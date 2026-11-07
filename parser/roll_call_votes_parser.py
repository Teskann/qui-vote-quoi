"""
Parser of the roll-call votes results (documents PV-<term>-<date>-RCV), which give the vote of each member.
"""
import re
from concurrent.futures import ThreadPoolExecutor

from lxml import etree
from unidecode import unidecode

from parser.Document import scrap_documents_from_string
from parser.empty_days_management import set_nothing_happened_for
from parser.open_data import (get_plenary_document_xml, get_meps, plenary_document_reference, get_mep,
                              get_corporate_body_label)
from utils.date_management import parliament_number_from_date, votes_roll_call_source_url

COUNTRY = "FR"
COUNTRY_NAME = "France"

VOTE_TYPES = {
    "Result.For": "+",
    "Result.Against": "-",
    "Result.Abstention": "0",
}

# Votes the members declared they intended to cast, after the vote
INTENTION_TYPES = {
    "Intentions.Result.For": "+",
    "Intentions.Result.Against": "-",
    "Intentions.Result.Abstention": "0",
}

COUNTRY_URI = "http://publications.europa.eu/resource/authority/country/FRA"


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
    Select the members of a country in the roll-call votes results, and find who they are.
    Since 2019, the members are identified by their PersId, which is the identifier used by the open data API.
    Before, only an internal identifier is given, so the members are identified by their name. The names are
    unique among the members of the parliament: the first name is added when several members share the same family
    name (for example "Martin Dominique").
    """

    def __init__(self, parliamentary_term: int, country: str):
        meps = get_meps(parliamentary_term, country)
        self.by_id = {mep["identifier"]: mep for mep in meps}
        self.by_name = {}
        self.__details = None
        if parliamentary_term >= 9:
            return  # The members are identified by their PersId
        normalize = self.__normalize
        other_family_names = {normalize(mep.get("familyName", "")) for mep in get_meps(parliamentary_term, None)
                              if mep["identifier"] not in self.by_id}
        ambiguous = set()
        for mep in meps:
            family_name, given_name = normalize(mep.get("familyName", "")), normalize(mep.get("givenName", ""))
            names = {family_name, f"{family_name} {given_name}", f"{given_name} {family_name}"}
            # Compound family names are sometimes shortened ("Letard-Lechevalier" is "Lechevalier")
            parts = family_name.split()
            if len(parts) > 1:
                names |= {part for part in parts if len(part) > 3 and part not in other_family_names}
            for name in names:
                if name in self.by_name and self.by_name[name] is not mep:
                    ambiguous.add(name)
                self.by_name[name] = mep
        # A name shared by several members still selects a member of the country, but we can't tell which one
        for name in ambiguous:
            self.by_name[name] = None

    @staticmethod
    def __normalize(name: str) -> str:
        return " ".join(unidecode(name).lower().replace("-", " ").split())

    def __contains__(self, member: etree._Element) -> bool:
        if member.get("PersId") is not None:
            return member.get("PersId") in self.by_id
        return self.__normalize(member.text or "") in self.by_name

    def describe(self, member: etree._Element) -> dict:
        """
        :param member: member element of the roll-call votes results, which must be selected (see __contains__)
        :return: {"name": <name in the document>, "id": <PersId or None>, "full_name": <given and family name or None>}
        """
        if member.get("PersId") is not None:
            mep = self.by_id[member.get("PersId")]
        else:
            mep = self.by_name[self.__normalize(member.text or "")]
        return {"name": member.text.strip(), "id": mep["identifier"] if mep else None,
                "full_name": self.__full_name(mep) if mep else None}

    @staticmethod
    def __full_name(mep: dict) -> str:
        return f"{mep.get('givenName', '')} {mep.get('familyName', '')}".strip()

    def __short_name(self, mep: dict) -> str:
        """
        Name of a member written as in the roll-call votes results: the family name, followed by the given name if
        another member shares the same family name
        """
        family_name = mep.get("familyName", "")
        homonyms = [other for other in self.by_id.values() if other.get("familyName", "") == family_name]
        return f"{family_name} {mep.get('givenName', '')}" if len(homonyms) > 1 else family_name

    def __periods(self) -> dict:
        """
        Mandates and political groups of each member, downloaded once
        :return: {<identifier>: {"mandates": [(start, end)], "groups": [(start, end, <group name>)]}}
        end is None when the period is not over
        """
        if self.__details is None:
            with ThreadPoolExecutor(8) as executor:
                details = dict(zip(self.by_id, executor.map(get_mep, self.by_id)))
            self.__details = {}
            for identifier, mep in details.items():
                mandates, groups = [], []
                for membership in mep.get("hasMembership", []):
                    period = membership.get("memberDuring", {})
                    start, end = period.get("startDate"), period.get("endDate")
                    if start is None:
                        continue
                    # The mandates are the memberships representing a country. They end at the resignation or the
                    # death of the member.
                    if COUNTRY_URI in membership.get("represents", []):
                        mandates.append((start, end))
                    elif membership.get("membershipClassification", "").endswith("/EU_POLITICAL_GROUP"):
                        # Any role in the group (member, chair, treasurer, ...)
                        organization = membership["organization"].split("/")[-1]
                        groups.append((start, end, get_corporate_body_label(organization)))
                self.__details[identifier] = {"mandates": mandates, "groups": groups}
        return self.__details

    @staticmethod
    def __during(date: str, start: str, end: str | None) -> bool:
        return start <= date and (end is None or date <= end)

    def absent(self, date: str, votes: dict) -> dict | None:
        """
        Members of the country who were in office at the given date but did not vote. The members who resigned
        or died before the vote, or who were not elected yet, are not in office.
        :param date: date of the vote, as iso formatted string
        :param votes: votes of the members, as returned by __parse_vote
        :return: {"France / <group> :": [{"name": ..., "id": ..., "full_name": ...}]}, grouped by the political group
        of the members at the given date. None if it can't be known, because some voters were not identified.
        """
        voters = [member for groups in votes.values() for group in groups.values() for member in group]
        if any(member["id"] is None for member in voters):
            return None
        voters_ids = {member["id"] for member in voters}
        absent = {}
        for identifier, periods in self.__periods().items():
            if identifier in voters_ids:
                continue
            if not any(self.__during(date, start, end) for start, end in periods["mandates"]):
                continue
            groups = [(start, group) for start, end, group in periods["groups"] if self.__during(date, start, end)]
            # When a member changes of group, the latest one is kept
            group = max(groups)[1] if groups else "NI"
            mep = self.by_id[identifier]
            absent.setdefault(unidecode(f"{COUNTRY_NAME} / {group} :"), []).append(
                {"name": self.__short_name(mep), "id": identifier, "full_name": self.__full_name(mep)})
        return {group: sorted(members, key=lambda member: unidecode(member["name"]).lower())
                for group, members in sorted(absent.items())}


def __parse_vote(vote: etree._Element, members: MembersSelector) -> dict:
    """
    Get the votes of the selected members for one roll-call vote, grouped by vote type and political group.
    The corrections and voting intentions are not taken into account, as they do not change the result
    (see __parse_corrections).
    :param vote: <RollCallVote.Result> element
    :param members: members to keep
    :return: {"+": {"France / <group> :": [{"name": ..., "id": ..., "full_name": ...}]}, "-": {...}, "0": {...}}
    """
    results = {}
    for tag, vote_type in VOTE_TYPES.items():
        element = vote.find(tag)
        if element is None:
            continue
        groups = {}
        for group in element.findall("Result.PoliticalGroup.List"):
            selected = [members.describe(member) for member in group
                        # The tag is "Member.Name" in some documents of 2018 and 2019
                        if member.tag in ("PoliticalGroup.Member.Name", "Member.Name")
                        if member in members]
            if selected:
                groups[unidecode(f"{COUNTRY_NAME} / {group.get('Identifier')} :")] = selected
        if groups:
            results[vote_type] = groups
    return results


def __parse_corrections(vote: etree._Element, members: MembersSelector, votes: dict) -> list:
    """
    Get the corrections declared by the selected members after a roll-call vote: the vote they intended to cast.
    They don't change the result of the vote.
    :param vote: <RollCallVote.Result> element
    :param members: members to keep
    :param votes: votes of the members, as returned by __parse_vote
    :return: [{"name": ..., "id": ..., "full_name": ..., "voted": <"+", "-", "0" or None if they didn't vote>,
               "intended": <"+", "-" or "0">}]
    """
    intentions = vote.find("Intentions")
    if intentions is None:
        return []
    def cast_vote(described: dict) -> str | None:
        key = "id" if described["id"] is not None else "name"
        return next((vote_type for vote_type, groups in votes.items() for group in groups.values()
                     for member in group if member[key] == described[key]), None)

    corrections = []
    for tag, vote_type in INTENTION_TYPES.items():
        for element in intentions.findall(tag):
            for member in element:
                if member.tag in ("PoliticalGroup.Member.Name", "Member.Name") and member in members:
                    described = members.describe(member)
                    corrections.append({**described, "voted": cast_vote(described), "intended": vote_type})
    return corrections


def __parse_roll_call_vote(vote: etree._Element, members: MembersSelector, date: str) -> dict:
    """
    :return: {"votes": <see __parse_vote>, "absent": <see MembersSelector.absent>,
              "corrections": <see __parse_corrections>}
    """
    votes = __parse_vote(vote, members)
    return {
        "votes": votes,
        "absent": members.absent(date, votes),
        "corrections": __parse_corrections(vote, members, votes),
    }


def __votes_count(vote: etree._Element) -> dict:
    counts = {}
    for tag, vote_type in VOTE_TYPES.items():
        element = vote.find(tag)
        number = element.get("Number") if element is not None else None
        counts[vote_type] = int(number) if number and number.isdigit() else 0
    return counts


def __amendment(vote: etree._Element, description: str, eu_document_code: str, members: MembersSelector,
                date: str) -> dict:
    """
    Description of one roll-call vote on a document (amendment, paragraph, final vote, ...)
    The result (adopted or not) is not part of the roll-call votes results, it comes from the votes results.
    """
    position = description.upper().find(eu_document_code.upper())
    return {
        "id": vote.get("Identifier"),
        # Item of the agenda the vote belongs to, to open the vote in the source (see votes_roll_call_source_url)
        "dlv_id": vote.get("DlvId"),
        "label": " ".join(description[position if position >= 0 else 0:].split()),
        "subject": None,
        "amendment": None,
        "part": None,
        "author": None,
        "was_roll_call_voted": True,
        "result": None,
        "global_votes": __votes_count(vote),
        **__parse_roll_call_vote(vote, members, date),
    }


def parse_all_votes(xml: etree._Element, date: str) -> dict:
    """
    Parse the roll-call votes results and return the votes of the French members for each document.
    When a document was voted several times (amendments, paragraphs, ...), the last vote is kept in "votes", as it's
    usually the vote on the whole text. All the votes on the document are listed in "amendments".
    :param xml: root of the roll-call votes results XML document
    :param date: date of the votes as iso formatted string
    :return: {<eu_document_code>: {"votes": {...}, "absent": {...}, "corrections": [...], "amendments": [...],
    "source_url": <URL of the last vote in the roll-call votes results>}}
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
        last_vote = matching_votes[-1][0]
        votes_per_document[eu_document_code] = {
            **__parse_roll_call_vote(last_vote, members, date),
            "source_url": votes_roll_call_source_url(date, last_vote.get("Identifier"), last_vote.get("DlvId")),
            "amendments": [__amendment(vote, description, eu_document_code, members, date)
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
