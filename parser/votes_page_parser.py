"""
Parser of the votes results (documents PV-<term>-<date>-VOT), which give the global result of each vote.

Two XML formats exist:
- the structured format (root <file>), used since 2024, which describes each vote with attributes
- the tabular format (root <documents>), used before, which is a conversion of the tables of the HTML page
"""
import re

from lxml import etree

from parser.Document import scrap_documents_from_string
from parser.open_data import get_plenary_document_xml, plenary_document_reference

UNAVAILABLE = "Données indisponibles"

# Results that end the voting procedure. The other ones are lapsed (LAPSED), withdrawn, etc.
FINAL_RESULTS = {"ADOPTED", "REJECTED"}

# Cell of the tabular format containing the result of a vote
VOTE_CELL_REGEX = re.compile(r"^\s*[+\-—]\s*$")
ROLL_CALL_REGEX = re.compile(r"\bAN\b")
VOTES_COUNT_REGEX = re.compile(r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
REVISION_REGEX = re.compile(r"/rev\d+$", flags=re.IGNORECASE)


def __text(element: etree._Element | None) -> str:
    return "".join(element.itertext()) if element is not None else ""


def __documents_in(text: str) -> set[str]:
    return {str(document) for document in scrap_documents_from_string(text)}


def __unavailable_votes_count() -> dict:
    return {"+": UNAVAILABLE, "-": UNAVAILABLE, "0": UNAVAILABLE}


def __vote_results(was_roll_call_voted: bool, was_adopted: bool, global_votes: dict | None = None) -> dict:
    results = {"was_roll_call_voted": was_roll_call_voted, "was_adopted": was_adopted}
    if was_roll_call_voted:
        results["global_votes"] = global_votes if global_votes is not None else __unavailable_votes_count()
    return results


# Structured format ####################################################################################################

def __document_code(document: etree._Element) -> str:
    number = document.get("documentNumber")
    return f"RC-{number}" if document.get("documentType") == "RC" else number


def __main_document(documents: list[etree._Element]) -> str:
    """
    Main document of a vote. Joint motions for resolution (RC) are the ones which are voted, the other motions
    for resolution are usually lapsed.
    """
    joint_motions = [document for document in documents if document.get("documentType") == "RC"]
    if joint_motions:
        return __document_code(joint_motions[0])
    return __document_code(min(documents, key=lambda document: int(document.get("documentOrder") or 0)))


def __parse_structured_voting(voting: etree._Element) -> dict:
    was_adopted = voting.get("result") == "ADOPTED"
    if voting.get("resultType") != "ROLL_CALL":
        return __vote_results(False, was_adopted)
    try:
        global_votes = {
            "+": int(voting.get("numberFavor")),
            "-": int(voting.get("numberAgainst")),
            "0": int(voting.get("numberAbstention")),
        }
    except (TypeError, ValueError):
        match = VOTES_COUNT_REGEX.search(voting.findtext("observations") or "")
        global_votes = {"+": int(match[1]), "-": int(match[2]), "0": int(match[3])} if match else None
    return __vote_results(True, was_adopted, global_votes)


def __parse_structured_format(xml: etree._Element) -> dict:
    results = {}
    for vote in xml.iter("vote"):
        documents = vote.findall("documents/document")
        if not documents:
            continue
        votings = [voting for voting in vote.findall("votings/voting") if voting.get("result") in FINAL_RESULTS]
        if not votings:
            continue
        eu_document_code = __main_document(documents)
        if eu_document_code not in results:
            # The last vote is the vote on the whole text
            results[eu_document_code] = __parse_structured_voting(votings[-1])
    return results


def __structured_amendment(voting: etree._Element) -> dict:
    def text(tag):
        value = " ".join((voting.findtext(tag) or "").split())
        return value or None
    result = __parse_structured_voting(voting)
    # "§" means that the original text is voted, not an amendment
    amendment = text("amendmentNumber") if text("amendmentNumber") != "§" else None
    # Part of a split vote ("1", "2", "2/AN", ...)
    part = re.match(r"^(\d+)", text("rcv/value") or "")
    label = text("label") or " - ".join(filter(None, [text("amendmentSubject"),
                                                      f"Am {amendment}" if amendment else None]))
    if part and not text("label"):
        label = f"{label}/{part[1]}"
    return {
        "id": voting.get("votingId"),
        "label": label or None,
        "subject": text("amendmentSubject"),
        "amendment": amendment,
        "part": part[1] if part else None,
        "author": text("amendmentAuthor"),
        "was_roll_call_voted": result["was_roll_call_voted"],
        "result": voting.get("result"),
        "global_votes": result.get("global_votes"),
        "votes": {},
    }


def __parse_structured_amendments(xml: etree._Element) -> dict:
    results = {}
    for vote in xml.iter("vote"):
        documents = vote.findall("documents/document")
        if not documents:
            continue
        eu_document_code = __main_document(documents)
        if eu_document_code in results:
            continue
        results[eu_document_code] = [__structured_amendment(voting) for voting in vote.findall("votings/voting")
                                     if voting.get("type") != "TITLE_BLOCK" and voting.get("result")]
    return results


# Tabular format #######################################################################################################

def __parse_votes_count(row: etree._Element) -> dict | None:
    for cell in row.findall("TD"):
        total_for = cell.find(".//Vote.Result.Table.TotalVote.For")
        if total_for is not None:
            def count(name):
                return int(__text(cell.find(f".//Vote.Result.Table.TotalVote.{name}")).strip())
            try:
                return {"+": count("For"), "-": count("Against"), "0": count("Abstention")}
            except ValueError:
                return None
        match = VOTES_COUNT_REGEX.search(__text(cell))
        if match:
            return {"+": int(match[1]), "-": int(match[2]), "0": int(match[3])}
    return None


def __main_tabular_document(documents: set[str], cells_before_vote: list[etree._Element]) -> str:
    """
    Find the document on which the final vote was held: it's the last document mentioned before the final vote.
    """
    for cell in reversed(cells_before_vote):
        found = __documents_in(__text(cell))
        if found:
            main = max(found, key=lambda code: (code.upper().startswith("RC-"), len(code)))
            break
    else:
        joint_motions = sorted(code for code in documents if code.upper().startswith("RC-"))
        main = joint_motions[0] if joint_motions else min(documents)

    # Use the code as written in the description, which sometimes omits the revision number
    for code in documents:
        if code != main and REVISION_REGEX.sub("", code).upper() == REVISION_REGEX.sub("", main).upper():
            return code
    return main


def __parse_tabular_format(xml: etree._Element) -> dict:
    results = {}
    for vote in xml.iter("Vote.Result"):
        documents = __documents_in(__text(vote.find("Vote.Result.Description.Text")))
        table = vote.find(".//TABLE")
        if not documents or table is None:
            continue
        cells = list(table.iter("TD"))
        vote_cells = [cell for cell in cells if VOTE_CELL_REGEX.match(__text(cell))]
        last_vote_cell = vote_cells[-1] if vote_cells else None
        cells_before_vote = cells[:cells.index(last_vote_cell)] if last_vote_cell is not None else cells
        eu_document_code = __main_tabular_document(documents, cells_before_vote)
        if eu_document_code in results:
            continue
        if last_vote_cell is None:
            results[eu_document_code] = __vote_results(False, True)
            continue
        row = last_vote_cell.getparent()
        was_adopted = __text(last_vote_cell).strip() == "+"
        was_roll_call_voted = any(ROLL_CALL_REGEX.search(__text(cell)) for cell in row.findall("TD"))
        results[eu_document_code] = __vote_results(
            was_roll_call_voted, was_adopted, __parse_votes_count(row) if was_roll_call_voted else None)
    return results


########################################################################################################################

def parse_vote_results(xml: etree._Element) -> dict:
    """
    Parse the votes results XML document
    :param xml: root of the XML document
    :return: dict of all the voted texts {<eu_document_code>: <vote_results>}
    """
    if xml.tag == "file":
        return __parse_structured_format(xml)
    return __parse_tabular_format(xml)


def parse_amendments(xml: etree._Element) -> dict:
    """
    Parse all the votes held on each document (amendments, paragraphs, final vote, ...).
    Only the structured format (since 2024) is supported: the tabular format cannot be parsed reliably.
    The votes of the members are not part of this document, they come from the roll-call votes results.
    :param xml: root of the XML document
    :return: {<eu_document_code>: [<amendment>]}
    """
    if xml.tag == "file":
        return __parse_structured_amendments(xml)
    return {}


def get_votes_results_xml(date: str) -> etree._Element | None:
    """
    Download the votes results XML document of the given date, None if it does not exist
    """
    return get_plenary_document_xml(plenary_document_reference(date, "VOT"))


def get_vote_results_for_date(date: str) -> dict | None:
    """
    Get the vote results for a given date
    :param date: date as iso string
    :return: dict of all the voted texts {<eu_document_code>: <vote_results>}, None if the document does not exist
    """
    xml = get_votes_results_xml(date)
    if xml is None:
        return None
    return parse_vote_results(xml)
