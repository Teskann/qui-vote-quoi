"""
Podiums of the members: the most absent (in proportion and in number of votes), and those who corrected their vote
the most.
"""

PODIUM_SIZE = 3


class SearchMembers:
    """
    Statistics of the members on the final votes of the documents found by a search. The documents are added one by
    one, so that they don't have to be kept in memory.
    """

    def __init__(self):
        # {<identifier>: {"id", "full_name", "group", "voted", "absent", "corrections"}}
        self.__members = {}

    def __member(self, group, entry):
        stats = self.__members.setdefault(entry["id"], {"id": entry["id"], "voted": 0, "absent": 0, "corrections": 0})
        stats["full_name"] = entry.get("full_name") or entry["name"]
        stats["group"] = group
        return stats

    def add(self, content: dict):
        """
        :param content: a document found, as displayed on the results page. The documents must be added by date, so
        that the latest group of each member is kept.
        """
        if content.get("absent") is None:
            return  # Database filled before the absents were stored, or unidentified voters
        if not content.get("global", {}).get("was_roll_call_voted"):
            return  # "votes" and "absent" are those of another vote on the document (amendment, ...)
        for groups in content["votes"].values():
            for group, entries in groups.items():
                for entry in entries:
                    if entry.get("id"):
                        self.__member(group, entry)["voted"] += 1
        for group, entries in content["absent"].items():
            for entry in entries:
                self.__member(group, entry)["absent"] += 1
        for correction in content.get("corrections", []):
            if correction.get("id") in self.__members and correction.get("voted") is not None:
                self.__members[correction["id"]]["corrections"] += 1

    def members(self) -> list[dict]:
        """
        :return: [{"id", "full_name", "group", "voted", "absent", "absent_rate", "corrections"}]
        """
        for stats in self.__members.values():
            stats["absent_rate"] = stats["absent"] / (stats["voted"] + stats["absent"])
        return list(self.__members.values())


def __podium(members: list[dict], key: str, tie_break: str | None = None) -> dict:
    """
    The first members by decreasing value of key (then tie_break). Members with the same values share the same rank.
    :return: {"entries": [{"rank": ..., "member": ...}], "ex_aequo": <number of other members with the same values as
    the last one of the podium>}. No entries if nobody has a value above 0.
    """
    def values(member):
        return member[key], member[tie_break] if tie_break else 0

    candidates = sorted((member for member in members if member[key] > 0),
                        key=lambda member: (*(-value for value in values(member)), member.get("full_name") or member["group"]))
    entries = []
    for position, member in enumerate(candidates[:PODIUM_SIZE]):
        rank = entries[-1]["rank"] if entries and values(entries[-1]["member"]) == values(member) else position + 1
        entries.append({"rank": rank, "member": member})
    ex_aequo = sum(1 for member in candidates[PODIUM_SIZE:] if entries and values(member) == values(entries[-1]["member"]))
    return {"entries": entries, "ex_aequo": ex_aequo}


def __podiums(members: list[dict]) -> dict:
    return {
        # Between two members with the same proportion, the one who missed more votes comes first
        "absent_rate": __podium(members, "absent_rate", "absent"),
        "absent": __podium(members, "absent", "absent_rate"),
        "corrections": __podium(members, "corrections"),
    }


def search_podiums(data: dict | SearchMembers) -> dict | None:
    """
    :param data: {<eu_document_code>: <content>}, as displayed on the results page, or the statistics of the members
    on these documents
    :return: {"absent_rate": <podium>, "absent": <podium>, "corrections": <podium>} for the final votes of the
    documents found, None if the absents are not known for these documents
    """
    if not isinstance(data, SearchMembers):
        search_members = SearchMembers()
        for content in sorted(data.values(), key=lambda content: content["date"]):
            search_members.add(content)
        data = search_members
    members = data.members()
    return __podiums(members) if members else None


def global_podiums(members: list[dict]) -> dict:
    """
    :param members: statistics of the members, see get_all_members
    :return: same as search_podiums, for all the roll-call votes of the members
    """
    return __podiums(members)


# Groups which changed their name: {<former name>: <current name>}. The open data of the parliament doesn't link them
# (they are distinct corporate bodies), the change of name is only announced in plenary.
RENAMED_GROUPS = {
    # Announced in plenary on 2021-01-18: "The Left in the European Parliament - GUE/NGL"
    "France / GUE/NGL :": "France / The Left :",
}


def group_statistics(members: list[dict]) -> list[dict]:
    """
    :param members: statistics of the members, see get_all_members. Each member counts in their latest group, under
    its current name (see RENAMED_GROUPS).
    :return: [{"group", "members", "members_count", "voted", "absent", "corrections", "absent_rate", "voted_average",
    "absent_average", "corrections_average"}]. The absent rate is over all the votes of the group, the averages are per
    member, so that the groups can be compared whatever their size.
    """
    groups = {}
    for member in members:
        name = RENAMED_GROUPS.get(member["group"], member["group"])
        group = groups.setdefault(name, {"group": name, "members": [], "members_count": 0,
                                         "voted": 0, "absent": 0, "corrections": 0})
        group["members"].append(member)
        group["members_count"] += 1
        for key in ("voted", "absent", "corrections"):
            group[key] += member[key]
    for group in groups.values():
        group["absent_rate"] = group["absent"] / (group["voted"] + group["absent"])
        for key in ("voted", "absent", "corrections"):
            group[key + "_average"] = group[key] / group["members_count"]
    return list(groups.values())


def group_podiums(groups: list[dict]) -> dict:
    """
    :param groups: see group_statistics
    :return: same as search_podiums, for the political groups
    """
    return {
        "absent_rate": __podium(groups, "absent_rate", "absent_average"),
        "absent": __podium(groups, "absent_average", "absent_rate"),
        "corrections": __podium(groups, "corrections_average"),
    }
