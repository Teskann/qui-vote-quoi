"""
Parser of the roll-call votes results (documents PV-<term>-<date>-RCV), which give the vote of each member.
"""
import re

from lxml import etree
from unidecode import unidecode

from parser.Document import scrap_documents_from_string
from parser.empty_days_management import set_nothing_happened_for
from parser.open_data import get_plenary_document_xml, get_meps, plenary_document_reference
from utils.date_management import parliament_number_from_date

COUNTRY = "FR"
COUNTRY_NAME = "France"

VOTE_TYPES = {
    "Result.For": "+",
    "Result.Against": "-",
    "Result.Abstention": "0",
}


def get_roll_call_votes_xml_at_date(date: str) -> etree._Element | None:
    """
    Download the roll-call votes results of the given date.
    If nothing was voted by roll-call on this date, None is returned and the date is registered
    in the empty_days.txt file.
    :param date: date as iso formatted string
    :return: None if nothing was voted on this date, root of the XML document otherwise
    """
    xml = get_plenary_document_xml(plenary_document_reference(date, "RCV"))
    if xml is None or next(xml.iter("RollCallVote.Result"), None) is None:
        set_nothing_happened_for(date)
        return None
    return xml


def __text(element: etree._Element | None) -> str:
    return "".join(element.itertext()) if element is not None else ""


def __document_regex(eu_document_code: str) -> re.Pattern:
    return re.compile(r"(^|.*(\s+|\(|\)))" + re.escape(eu_document_code) + r"((\s+|\(|\)).*|$)",
                      flags=re.IGNORECASE | re.DOTALL)


class MembersSelector:
    """
    Select the members of a country in the roll-call votes results.
    Since 2019, the members are identified by their PersId, which is the identifier used by the open data API.
    Before, only an internal identifier is given, so the members are identified by their name. The names are
    unique among the members of the parliament: the first name is added when several members share the same family
    name (for example "Martin Dominique").
    """

    def __init__(self, parliamentary_term: int, country: str):
        meps = get_meps(parliamentary_term, country)
        self.ids = {mep["identifier"] for mep in meps}
        self.names = set()
        if parliamentary_term >= 9:
            return  # The members are identified by their PersId
        normalize = self.__normalize
        other_family_names = {normalize(mep.get("familyName", "")) for mep in get_meps(parliamentary_term, None)
                              if mep["identifier"] not in self.ids}
        for mep in meps:
            family_name, given_name = normalize(mep.get("familyName", "")), normalize(mep.get("givenName", ""))
            self.names |= {family_name, f"{family_name} {given_name}", f"{given_name} {family_name}"}
            # Compound family names are sometimes shortened ("Letard-Lechevalier" is "Lechevalier")
            parts = family_name.split()
            if len(parts) > 1:
                self.names |= {part for part in parts if len(part) > 3 and part not in other_family_names}

    @staticmethod
    def __normalize(name: str) -> str:
        return " ".join(unidecode(name).lower().replace("-", " ").split())

    def __contains__(self, member: etree._Element) -> bool:
        if member.get("PersId") is not None:
            return member.get("PersId") in self.ids
        return self.__normalize(member.text or "") in self.names


def __parse_vote(vote: etree._Element, members: MembersSelector) -> dict:
    """
    Get the votes of the selected members for one roll-call vote, grouped by vote type and political group.
    The corrections and voting intentions are not taken into account, as they do not change the result.
    :param vote: <RollCallVote.Result> element
    :param members: members to keep
    :return: {"+": {"France / <group> :": [<names>]}, "-": {...}, "0": {...}}
    """
    results = {}
    for tag, vote_type in VOTE_TYPES.items():
        element = vote.find(tag)
        if element is None:
            continue
        groups = {}
        for group in element.findall("Result.PoliticalGroup.List"):
            names = [member.text.strip() for member in group
                     # The tag is "Member.Name" in some documents of 2018 and 2019
                     if member.tag in ("PoliticalGroup.Member.Name", "Member.Name")
                     if member in members]
            if names:
                groups[unidecode(f"{COUNTRY_NAME} / {group.get('Identifier')} :")] = names
        if groups:
            results[vote_type] = groups
    return results


def __votes_count(vote: etree._Element) -> dict:
    counts = {}
    for tag, vote_type in VOTE_TYPES.items():
        element = vote.find(tag)
        number = element.get("Number") if element is not None else None
        counts[vote_type] = int(number) if number and number.isdigit() else 0
    return counts


def __amendment(vote: etree._Element, description: str, eu_document_code: str, members: MembersSelector) -> dict:
    """
    Description of one roll-call vote on a document (amendment, paragraph, final vote, ...)
    The result (adopted or not) is not part of the roll-call votes results, it comes from the votes results.
    """
    position = description.upper().find(eu_document_code.upper())
    return {
        "id": vote.get("Identifier"),
        "label": " ".join(description[position if position >= 0 else 0:].split()),
        "subject": None,
        "amendment": None,
        "part": None,
        "author": None,
        "was_roll_call_voted": True,
        "result": None,
        "global_votes": __votes_count(vote),
        "votes": __parse_vote(vote, members),
    }


def parse_all_votes(xml: etree._Element, date: str) -> dict:
    """
    Parse the roll-call votes results and return the votes of the French members for each document.
    When a document was voted several times (amendments, paragraphs, ...), the last vote is kept in "votes", as it's
    usually the vote on the whole text. All the votes on the document are listed in "amendments".
    :param xml: root of the roll-call votes results XML document
    :param date: date of the votes as iso formatted string
    :return: {<eu_document_code>: {"votes": {...}, "amendments": [...]}}
    """
    members = MembersSelector(parliament_number_from_date(date), COUNTRY)
    votes = [(vote, __text(vote.find("RollCallVote.Description.Text")))
             for vote in xml.iter("RollCallVote.Result")]

    all_documents = set()
    for _, description in votes:
        all_documents |= {str(document) for document in scrap_documents_from_string(description)}

    votes_per_document = {}
    for eu_document_code in all_documents:
        regex = __document_regex(eu_document_code)
        matching_votes = [(vote, description) for vote, description in votes if regex.match(description)]
        if not matching_votes:
            continue
        votes_per_document[eu_document_code] = {
            "votes": __parse_vote(matching_votes[-1][0], members),
            "amendments": [__amendment(vote, description, eu_document_code, members)
                           for vote, description in matching_votes],
        }
    return votes_per_document


def roll_call_votes_by_id(votes_per_document: dict) -> dict:
    """
    Index the roll-call votes returned by parse_all_votes by their identifier
    :return: {<vote identifier>: <amendment>}
    """
    return {amendment["id"]: amendment
            for content in votes_per_document.values()
            for amendment in content.get("amendments", [])}
