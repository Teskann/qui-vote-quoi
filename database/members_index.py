"""
Statistics of each member over the whole database: participation to the roll-call votes, corrections, recent votes.
Also the cohesion of the political groups, and how often they vote like each other.
Reading the whole database takes a few seconds, so the statistics of each day are kept in memory, and a day is read
again only when it is updated in the database.
"""
import threading

from database import storage

RECENT_VOTES = 30

# Kinds of roll-call votes: the final vote on a text, or the other votes (amendments, paragraphs, ...)
FINAL = "final"
AMENDMENTS = "amendments"
VOTE_KINDS = (FINAL, AMENDMENTS)

__lock = threading.Lock()
# {<date>: (<time of the last update>, <statistics of the day, see __day_statistics>)}
__days = {}
__cache = {"key": None, "index": None, "groups": None}


def __members(groups: dict):
    """
    :param groups: {"France / <group> :": [<member>]}
    :return: (<group>, <member>) for the identified members
    """
    for group, members in groups.items():
        for member in members:
            if isinstance(member, dict) and member.get("id"):
                yield group, member


def __group_positions(vote: dict) -> dict:
    """
    The abstentions don't count in the result of a vote: the position of a group is that of the majority of its
    members who voted for or against.
    :return: {<group>: (<"+" or "-", None when there are as many votes for as against>, <number of members who voted
    so>, <number of members who voted for or against>)}
    """
    counts = {}
    for position in ("+", "-"):
        for group, members in vote["votes"].get(position, {}).items():
            counts.setdefault(group, {"+": 0, "-": 0})[position] = len(members)
    positions = {}
    for group, per_position in counts.items():
        votes_for, votes_against = per_position["+"], per_position["-"]
        majority = None if votes_for == votes_against else "+" if votes_for > votes_against else "-"
        positions[group] = (majority, max(votes_for, votes_against), votes_for + votes_against)
    return positions


def is_final_vote(vote: dict, document: dict) -> bool:
    """
    :param vote: one of the votes held on the document (see "amendments")
    :return: whether the vote is the roll-call vote on the whole document. Its identifier is stored since the final vote
    is chosen from the result of the document (see merge_data). In the days filled before, it's the vote whose votes
    are those of the document (the last roll-call vote on the document).
    """
    if not (document.get("global", {}).get("was_roll_call_voted") and vote.get("was_roll_call_voted")):
        return False
    if "final_vote_id" in document:
        return document["final_vote_id"] is not None and vote.get("id") == document["final_vote_id"]
    return bool(vote.get("votes") and vote["votes"] == document.get("votes") and vote.get("absent") == document.get("absent"))


def __day_statistics(date: str) -> dict:
    """
    :return: {"members": {<kind of vote, see VOTE_KINDS>: {<identifier>: {"full_name", "group", "voted", "absent",
    "corrections"}}},
    "cohesion": {<kind>: {<group>: [<number of votes>, <sum of the shares of the members who voted like the majority>]}},
    "proximity": {<kind>: {(<group>, <other group>): [<votes where they had the same position>, <votes where both had
    a position>]}}, "corrections": {<identifier>: [{"date", "kind", "vote_id", "eu_document_code", "title", "label",
    "voted", "intended"}]}} for the roll-call votes of the day
    """
    statistics = {kind: {} for kind in VOTE_KINDS}
    cohesion = {kind: {} for kind in VOTE_KINDS}
    proximity = {kind: {} for kind in VOTE_KINDS}
    # {<identifier>: [<correction>]}
    corrections = {}

    def member(kind, group, entry):
        stats = statistics[kind].setdefault(entry["id"], {"voted": 0, "absent": 0, "corrections": 0})
        stats["full_name"] = entry.get("full_name") or entry["name"]
        stats["group"] = group
        return stats

    # A roll-call vote may concern several documents, it's counted once
    roll_call_votes = {}
    final_votes = set()
    # {<vote identifier>: (<eu_document_code>, <title>)}, the first document of the vote
    documents = {}
    for eu_document_code, content in storage.read_day(date).items():
        for vote in content.get("amendments", []):
            if vote.get("was_roll_call_voted") and vote.get("id"):
                roll_call_votes[vote["id"]] = vote
                documents.setdefault(vote["id"], (eu_document_code, content.get("details", {}).get("title")))
        final = [vote for vote in content.get("amendments", []) if vote.get("id") and is_final_vote(vote, content)]
        if final:
            final_votes.add(final[-1]["id"])
    for vote in roll_call_votes.values():
        kind = FINAL if vote["id"] in final_votes else AMENDMENTS
        # The groups don't need the members to be identified: all the votes are used
        positions = __group_positions(vote)
        for group, (_, majority_count, voters) in positions.items():
            # The cohesion of a group of one member is meaningless
            if voters >= 2:
                group_cohesion = cohesion[kind].setdefault(group, [0, 0])
                group_cohesion[0] += 1
                group_cohesion[1] += majority_count / voters
        for group, (position, _, _) in positions.items():
            for other, (other_position, _, _) in positions.items():
                if group != other and position is not None and other_position is not None:
                    pair = proximity[kind].setdefault((group, other), [0, 0])
                    pair[0] += position == other_position
                    pair[1] += 1

        if vote.get("absent") is None:
            continue  # Database filled before the absents were stored, or unidentified voters
        for groups in vote["votes"].values():
            for group, entry in __members(groups):
                member(kind, group, entry)["voted"] += 1
        for group, entry in __members(vote["absent"]):
            member(kind, group, entry)["absent"] += 1
        for correction in vote.get("corrections", []):
            if correction.get("id") in statistics[kind]:
                if correction.get("voted") is not None:
                    statistics[kind][correction["id"]]["corrections"] += 1
                corrections.setdefault(correction["id"], []).append({
                    "date": date, "kind": kind, "vote_id": vote["id"], "eu_document_code": documents[vote["id"]][0],
                    "title": documents[vote["id"]][1], "label": vote.get("label"),
                    "voted": correction.get("voted"), "intended": correction.get("intended")})
    return {"members": statistics, "cohesion": cohesion, "proximity": proximity, "corrections": corrections}


def __refresh(days: list[tuple[str, float]]):
    """
    Update the statistics of the days. Only the days updated since they were read are read again.
    :param days: [(<date>, <time of the last update>)]
    """
    for date in set(__days) - {date for date, _ in days}:
        del __days[date]
    for date, updated_at in days:
        if date not in __days or __days[date][0] != updated_at:
            __days[date] = (updated_at, __day_statistics(date))


def __aggregate(dates: list[str], kinds: tuple = VOTE_KINDS) -> dict:
    """
    Gather the statistics of the given days (already refreshed) and kinds of votes, and rank the members
    """
    index = {}
    for date in dates:
        month = date[:7]
        for identifier, day in (item for kind in kinds for item in __days[date][1]["members"][kind].items()):
            entry = index.setdefault(identifier, {"id": identifier, "months": {}, "corrections": 0})
            # The days are processed in order, so the latest name and group are kept
            entry["full_name"], entry["group"] = day["full_name"], day["group"]
            months = entry["months"].setdefault(month, {"voted": 0, "absent": 0})
            months["voted"] += day["voted"]
            months["absent"] += day["absent"]
            entry["corrections"] += day["corrections"]

    for entry in index.values():
        entry["voted"] = sum(month["voted"] for month in entry["months"].values())
        entry["absent"] = sum(month["absent"] for month in entry["months"].values())
        entry["absent_rate"] = entry["absent"] / (entry["voted"] + entry["absent"])
    __rank(index, "absent_rate")
    __rank(index, "absent")
    __rank(index, "corrections")
    __rank(index, "voted")
    return index


def __aggregate_groups(dates: list[str], kinds: tuple = VOTE_KINDS) -> dict:
    """
    Gather the cohesion and the proximity of the groups over the given days (already refreshed) and kinds of votes
    """
    cohesion, proximity = {}, {}
    for date in dates:
        day = __days[date][1]
        for kind in kinds:
            for group, (votes, shares) in day["cohesion"][kind].items():
                total = cohesion.setdefault(group, [0, 0])
                total[0] += votes
                total[1] += shares
            for pair, (same, votes) in day["proximity"][kind].items():
                total = proximity.setdefault(pair, [0, 0])
                total[0] += same
                total[1] += votes
    return {"cohesion": cohesion, "proximity": proximity}


def __rank(index: dict, metric: str):
    """
    Rank the members by decreasing value of the metric, in entry["ranks"][metric]. Equal values share the same rank
    (1, 1, 3, ...).
    """
    values = sorted((entry[metric] for entry in index.values()), reverse=True)
    first_rank = {}
    for position, value in enumerate(values):
        first_rank.setdefault(value, position + 1)
    for entry in index.values():
        entry.setdefault("ranks", {})[metric] = first_rank[entry[metric]]
        entry["members_count"] = len(values)


def __dates(start_date: str | None, end_date: str | None) -> list[str]:
    """
    Days of the period, after refreshing the statistics of the days updated since they were read. Called with the lock.
    """
    days = storage.days()
    key = tuple(days)
    dates = [date for date, _ in days]
    if __cache["key"] != key:
        __refresh(days)
        __cache["index"] = __aggregate(dates)
        __cache["groups"] = __aggregate_groups(dates)
        __cache["key"] = key
    return [date for date in dates if (start_date or "") <= date <= (end_date or "9999")]


def __index(start_date: str | None = None, end_date: str | None = None, kinds: tuple = VOTE_KINDS) -> dict:
    """
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :param kinds: kinds of votes counted, see VOTE_KINDS
    """
    with __lock:
        dates = __dates(start_date, end_date)
        if start_date is None and end_date is None and tuple(kinds) == VOTE_KINDS:
            return __cache["index"]
        return __aggregate(dates, tuple(kinds))


def database_dates() -> tuple[str, str] | None:
    """
    :return: (first day, last day) of the database, None if it's empty
    """
    days = storage.days()
    return (days[0][0], days[-1][0]) if days else None


def warm_up():
    """
    Build the index in the background, so that the first visitor doesn't wait
    """
    threading.Thread(target=__index, daemon=True).start()


def __recent_votes(identifier: str, last_month: str) -> list[dict]:
    """
    Final votes of the member on the most recent documents. Only the last days are read, from the last month the
    member voted in.
    """
    recent = []
    for date in reversed([date for date, _ in storage.days() if date[:7] <= last_month]):
        for eu_document_code, content in reversed(list(storage.read_day(date, with_amendments=False).items())):
            # When the final vote was not a roll-call vote, "votes" and "absent" are those of another roll-call vote
            # on the document (an amendment, ...): they don't say what the member voted on the text
            if content.get("absent") is None or "details" not in content or not content["global"]["was_roll_call_voted"]:
                continue
            cast = list(content["votes"].items()) + [("absent", content["absent"])]
            vote_type = next((vote_type for vote_type, groups in cast
                              for _, member in __members(groups) if member["id"] == identifier), None)
            if vote_type is not None:
                recent.append({
                    "date": date,
                    "eu_document_code": eu_document_code,
                    "title": content["details"]["title"],
                    "vote": vote_type,
                    "was_adopted": content["global"]["was_adopted"],
                })
                if len(recent) == RECENT_VOTES:
                    return recent
    return recent


def get_group_recent_votes(groups: set[str], last_month: str) -> list[dict]:
    """
    Final votes of a political group on the most recent documents. Only the last days are read, from the last month
    the group voted in.
    :param groups: names of the group in the votes ("France / The Left :"), several when it was renamed
    :param last_month: last month the group voted in, as "YYYY-MM"
    :return: [{"date", "eu_document_code", "title", "counts": {"+": ..., "-": ..., "0": ..., "absent": ...},
    "position": <"+", "-" or "0" voted by most of the members who voted, None if as many voted two ways, "absent" if
    nobody voted>, "was_adopted"}], most recent first
    """
    recent = []
    for date in reversed([date for date, _ in storage.days() if date[:7] <= last_month]):
        for eu_document_code, content in reversed(list(storage.read_day(date, with_amendments=False).items())):
            # Same documents as the recent votes of the members, see __recent_votes
            if content.get("absent") is None or "details" not in content or not content["global"]["was_roll_call_voted"]:
                continue
            cast = list(content["votes"].items()) + [("absent", content["absent"])]
            counts = {vote_type: sum(1 for group, _ in __members(members) if group in groups)
                      for vote_type, members in cast}
            counts = {vote_type: counts.get(vote_type, 0) for vote_type in ("+", "-", "0", "absent")}
            if not any(counts.values()):
                continue  # The group was not in office
            votes = sorted((counts[vote_type], vote_type) for vote_type in ("+", "-", "0"))
            position = "absent" if votes[-1][0] == 0 else None if votes[-1][0] == votes[-2][0] else votes[-1][1]
            recent.append({
                "date": date,
                "eu_document_code": eu_document_code,
                "title": content["details"]["title"],
                "counts": counts,
                "position": position,
                "was_adopted": content["global"]["was_adopted"],
            })
            if len(recent) == RECENT_VOTES:
                return recent
    return recent


def get_all_members(start_date: str | None = None, end_date: str | None = None,
                    kinds: tuple = VOTE_KINDS) -> list[dict]:
    """
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :param kinds: kinds of votes counted, see VOTE_KINDS. All by default.
    :return: the statistics of all the members on the period, see get_member (without "recent"). The ranks are among
    the members who were in office during the period.
    """
    return list(__index(start_date, end_date, kinds).values())


def get_member(identifier: str, start_date: str | None = None, end_date: str | None = None,
               kinds: tuple = VOTE_KINDS) -> dict | None:
    """
    :param identifier: identifier of the member (PersId)
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :param kinds: kinds of votes counted, see VOTE_KINDS. All by default.
    :return: {"id", "full_name", "group", "voted", "absent", "absent_rate", "corrections", "months", "recent",
    "ranks": {"absent_rate": ..., "absent": ..., "corrections": ..., "voted": ...}, "members_count"}, None if the
    member never appears in the database. The ranks are among the members in office during the period. When the member
    has no vote on the period, only "id", "full_name", "group" and "recent" are given.
    """
    entry = __index().get(identifier)
    if entry is None:
        return None
    recent = __recent_votes(identifier, max(entry["months"]))
    on_period = __index(start_date, end_date, kinds).get(identifier)
    if on_period is None:
        return {"id": identifier, "full_name": entry["full_name"], "group": entry["group"], "recent": recent}
    return {**on_period, "recent": recent}


def get_groups_votes(start_date: str | None = None, end_date: str | None = None, kinds: tuple = VOTE_KINDS) -> dict:
    """
    How the political groups voted on the roll-call votes of the period (amendments included by default). Only the
    French members are in the database: a group is its French delegation.
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :param kinds: kinds of votes counted, see VOTE_KINDS. All by default.
    :return: {"cohesion": {<group>: [<number of votes with at least 2 members voting>, <sum of the shares of the members
    who voted like the majority of the group>]}, "proximity": {(<group>, <other group>): [<votes where both had the
    same majority position>, <votes where both had a majority position>]}}
    """
    with __lock:
        dates = __dates(start_date, end_date)
        if start_date is None and end_date is None and tuple(kinds) == VOTE_KINDS:
            return __cache["groups"]
        return __aggregate_groups(dates, tuple(kinds))


def get_member_corrections(identifier: str, start_date: str | None = None, end_date: str | None = None,
                           kinds: tuple = VOTE_KINDS) -> list[dict]:
    """
    Votes of the period on which the member declared afterwards what they meant to vote: they voted by mistake, or
    didn't vote
    :param identifier: identifier of the member (PersId)
    :param kinds: kinds of votes counted, see VOTE_KINDS. All by default.
    :return: [{"date", "kind", "vote_id", "eu_document_code", "title", "label", "voted", "intended"}], most recent
    first.
    "voted" is what the member voted (None if they didn't vote), "intended" what they meant to vote ("+", "-" or "0").
    """
    with __lock:
        dates = __dates(start_date, end_date)
        return [correction for date in reversed(dates)
                for correction in reversed(__days[date][1]["corrections"].get(identifier, []))
                if correction["kind"] in kinds]
