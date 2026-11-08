"""
Statistics of each member over the whole database: participation to the roll-call votes, corrections, recent votes.
Also the cohesion of the political groups, and how often they vote like each other.
The statistics of each day are computed when the day is written (see database.statistics): they are gathered here with
SQL, so that nothing is kept in memory between the requests.
"""
from database import storage
from database.statistics import FINAL, AMENDMENTS, VOTE_KINDS, members as __members

RECENT_VOTES = 30


def __period(start_date: str | None, end_date: str | None, kinds: tuple) -> tuple[str, list]:
    """
    :return: (<SQL condition on the "date" and "kind" columns>, <its parameters>)
    """
    numbers = [storage.KINDS[kind] for kind in kinds]
    return (f"date BETWEEN ? AND ? AND kind IN ({', '.join('?' * len(numbers))})",
            [start_date or "", end_date or "9999", *numbers])


def __first_appearance_order(table: str, key: str, period: str, alias: str | None = None) -> str:
    """
    :param key: SQL expression of the key, named alias in the query
    :param period: SQL condition on the rows, see __period
    :return: SQL query of (<key>, <rank of its first appearance>) in the rows of the period of the table, the days
    being processed in order, then the kinds, then the rows of a day
    """
    alias = alias or key
    return f"""SELECT {alias}, ROW_NUMBER() OVER (ORDER BY date, kind, position) AS appearance FROM (
        SELECT {key} AS {alias}, date, kind, position,
               ROW_NUMBER() OVER (PARTITION BY {key} ORDER BY date, kind, position) AS rank
        FROM {table} WHERE {period}) WHERE rank = 1"""


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


def __index(start_date: str | None = None, end_date: str | None = None, kinds: tuple = VOTE_KINDS) -> dict:
    """
    Gather the statistics of the members on the period and kinds of votes, and rank them
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :param kinds: kinds of votes counted, see VOTE_KINDS
    :return: {<identifier>: <statistics, see get_member>}
    """
    period, parameters = __period(start_date, end_date, tuple(kinds))
    index = {}
    with storage.connect() as connection:
        # The latest name and group of each member are kept: SQLite takes them from the row of MAX()
        for identifier, full_name, group, corrections, _ in connection.execute(
                f"SELECT member_id, full_name, group_name, SUM(corrections), MAX(date || kind) FROM member_days "
                f"WHERE {period} GROUP BY member_id", parameters):
            index[identifier] = {"id": identifier, "months": {}, "corrections": corrections, "full_name": full_name,
                                 "group": group}
        for identifier, month, voted, absent in connection.execute(
                f"SELECT member_id, substr(date, 1, 7) AS month, SUM(voted), SUM(absent) FROM member_days "
                f"WHERE {period} GROUP BY member_id, month ORDER BY month", parameters):
            index[identifier]["months"][month] = {"voted": voted, "absent": absent}

    for entry in index.values():
        entry["voted"] = sum(month["voted"] for month in entry["months"].values())
        entry["absent"] = sum(month["absent"] for month in entry["months"].values())
        entry["absent_rate"] = entry["absent"] / (entry["voted"] + entry["absent"])
    __rank(index, "absent_rate")
    __rank(index, "absent")
    __rank(index, "corrections")
    __rank(index, "voted")
    return index


def database_dates() -> tuple[str, str] | None:
    """
    :return: (first day, last day) of the database, None if it's empty
    """
    days = storage.days()
    return (days[0][0], days[-1][0]) if days else None


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
    with storage.connect() as connection:
        entry = connection.execute(
            "SELECT full_name, group_name, substr(date, 1, 7) FROM member_days WHERE member_id = ? "
            "ORDER BY date DESC, kind DESC LIMIT 1", (identifier,)).fetchone()
    if entry is None:
        return None
    full_name, group, last_month = entry
    recent = __recent_votes(identifier, last_month)
    on_period = __index(start_date, end_date, kinds).get(identifier)
    if on_period is None:
        return {"id": identifier, "full_name": full_name, "group": group, "recent": recent}
    return {**on_period, "recent": recent}


def get_member_group(identifier: str, start_date: str | None = None, end_date: str | None = None) -> str | None:
    """
    :param identifier: identifier of the member (PersId)
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :return: the latest group of the member on the period (as in get_all_members), None if they didn't vote on it
    """
    with storage.connect() as connection:
        row = connection.execute(
            "SELECT group_name FROM member_days WHERE member_id = ? AND date BETWEEN ? AND ? "
            "ORDER BY date DESC, kind DESC LIMIT 1", (identifier, start_date or "", end_date or "9999")).fetchone()
    return row[0] if row else None


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
    period, parameters = __period(start_date, end_date, tuple(kinds))
    with storage.connect() as connection:
        cohesion = {group: [votes, shares] for group, votes, shares in connection.execute(f"""
            WITH appearances AS ({__first_appearance_order("group_cohesion", "group_name", period)})
            SELECT group_name, SUM(votes), SUM(shares) FROM group_cohesion JOIN appearances USING (group_name)
            WHERE {period} GROUP BY group_name ORDER BY MIN(appearance)""", parameters * 2)}
        pair = "group_name || char(0) || other_group"
        proximity = {(group, other): [same, votes] for group, other, same, votes in connection.execute(f"""
            WITH appearances AS ({__first_appearance_order("group_proximity", pair, period, "pair")})
            SELECT group_name, other_group, SUM(same), SUM(votes) FROM group_proximity
            JOIN appearances ON appearances.pair = {pair}
            WHERE {period} GROUP BY group_name, other_group ORDER BY MIN(appearance)""", parameters * 2)}
    return {"cohesion": cohesion, "proximity": proximity}


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
    period, parameters = __period(start_date, end_date, tuple(kinds))
    kind_names = {number: kind for kind, number in storage.KINDS.items()}
    with storage.connect() as connection:
        rows = connection.execute(
            f"SELECT date, kind, vote_id, eu_document_code, title, label, voted, intended FROM corrections "
            f"WHERE member_id = ? AND {period} ORDER BY date DESC, position DESC", [identifier, *parameters]).fetchall()
    return [{"date": date, "kind": kind_names[kind], "vote_id": vote_id, "eu_document_code": eu_document_code,
             "title": title, "label": label, "voted": voted, "intended": intended}
            for date, kind, vote_id, eu_document_code, title, label, voted, intended in rows]
