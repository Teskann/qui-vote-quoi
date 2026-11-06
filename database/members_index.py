"""
Statistics of each member over the whole database: participation to the roll-call votes, corrections, recent votes.
Reading the whole database takes a few seconds, so the statistics of each day are kept in memory, and a day is read
again only when its file changes (database update).
"""
import glob
import json
import os
import threading

from database.database import get_database_path

RECENT_VOTES = 30

__lock = threading.Lock()
# {<file>: (<modification time>, <statistics of the day, see __day_statistics>)}
__days = {}
__cache = {"key": None, "index": None}


def __files() -> list[str]:
    return sorted(glob.glob(os.path.join(get_database_path(), "*.json")))


def __read(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def __members(groups: dict):
    """
    :param groups: {"France / <group> :": [<member>]}
    :return: (<group>, <member>) for the identified members
    """
    for group, members in groups.items():
        for member in members:
            if isinstance(member, dict) and member.get("id"):
                yield group, member


def __day_statistics(file: str) -> dict:
    """
    :return: {<identifier>: {"full_name", "group", "voted", "absent", "corrections"}} for the roll-call votes of the day
    """
    statistics = {}

    def member(group, entry):
        stats = statistics.setdefault(entry["id"], {"voted": 0, "absent": 0, "corrections": 0})
        stats["full_name"] = entry.get("full_name") or entry["name"]
        stats["group"] = group
        return stats

    # A roll-call vote may concern several documents, it's counted once
    roll_call_votes = {}
    for content in __read(file).values():
        for vote in content.get("amendments", []):
            if vote.get("was_roll_call_voted") and vote.get("absent") is not None and vote.get("id"):
                roll_call_votes[vote["id"]] = vote
    for vote in roll_call_votes.values():
        for groups in vote["votes"].values():
            for group, entry in __members(groups):
                member(group, entry)["voted"] += 1
        for group, entry in __members(vote["absent"]):
            member(group, entry)["absent"] += 1
        for correction in vote.get("corrections", []):
            if correction.get("id") in statistics:
                statistics[correction["id"]]["corrections"] += 1
    return statistics


def __refresh(files: list[str]):
    """
    Update the statistics of the days. Only the days whose file changed are read again.
    """
    for file in set(__days) - set(files):
        del __days[file]
    for file in files:
        modification_time = os.path.getmtime(file)
        if file not in __days or __days[file][0] != modification_time:
            __days[file] = (modification_time, __day_statistics(file))


def __aggregate(files: list[str]) -> dict:
    """
    Gather the statistics of the given days (already refreshed), and rank the members
    """
    index = {}
    for file in files:
        month = os.path.basename(file)[:7]
        for identifier, day in __days[file][1].items():
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


def __index(start_date: str | None = None, end_date: str | None = None) -> dict:
    """
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    """
    with __lock:
        files = __files()
        key = tuple((file, os.path.getmtime(file)) for file in files)
        if __cache["key"] != key:
            __refresh(files)
            __cache["index"] = __aggregate(files)
            __cache["key"] = key
        if start_date is None and end_date is None:
            return __cache["index"]
        return __aggregate([file for file in files
                            if (start_date or "") <= os.path.basename(file)[:10] <= (end_date or "9999")])


def database_dates() -> tuple[str, str] | None:
    """
    :return: (first day, last day) of the database, None if it's empty
    """
    files = __files()
    return (os.path.basename(files[0])[:10], os.path.basename(files[-1])[:10]) if files else None


def warm_up():
    """
    Build the index in the background, so that the first visitor doesn't wait
    """
    threading.Thread(target=__index, daemon=True).start()


def __recent_votes(identifier: str, last_month: str) -> list[dict]:
    """
    Final votes of the member on the most recent documents. Only the last files are read, from the last month the
    member voted in.
    """
    recent = []
    for file in reversed([file for file in __files() if os.path.basename(file)[:7] <= last_month]):
        date = os.path.basename(file)[:10]
        for eu_document_code, content in reversed(list(__read(file).items())):
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


def get_all_members(start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :return: the statistics of all the members on the period, see get_member (without "recent"). The ranks are among
    the members who were in office during the period.
    """
    return list(__index(start_date, end_date).values())


def get_member(identifier: str) -> dict | None:
    """
    :param identifier: identifier of the member (PersId)
    :return: {"id", "full_name", "group", "voted", "absent", "absent_rate", "corrections", "months", "recent",
    "ranks": {"absent_rate": ..., "absent": ..., "corrections": ..., "voted": ...}, "members_count"}, None if the
    member never appears in the database. The ranks are among all the members of the database.
    """
    entry = __index().get(identifier)
    if entry is None:
        return None
    return {**entry, "recent": __recent_votes(identifier, max(entry["months"]))}
