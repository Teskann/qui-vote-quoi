"""
Statistics computed from the votes of a day when it's written in the database (see storage.write_day), so that the
website reads them with SQL instead of decoding the votes of every member.
"""

# Kinds of roll-call votes: the final vote on a text, or the other votes (amendments, paragraphs, ...)
FINAL = "final"
AMENDMENTS = "amendments"
VOTE_KINDS = (FINAL, AMENDMENTS)

EUROPEAN_PARLIAMENT = "Parlement Européen :"
TOTAL_FRANCE = "Total France :"


def members(groups: dict):
    """
    :param groups: {"France / <group> :": [<member>]}
    :return: (<group>, <member>) for the identified members
    """
    for group, entries in groups.items():
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id"):
                yield group, entry


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


def __group_positions(vote: dict) -> dict:
    """
    The abstentions don't count in the result of a vote: the position of a group is that of the majority of its
    members who voted for or against.
    :return: {<group>: (<"+" or "-", None when there are as many votes for as against>, <number of members who voted
    so>, <number of members who voted for or against>)}
    """
    counts = {}
    for position in ("+", "-"):
        for group, entries in vote["votes"].get(position, {}).items():
            counts.setdefault(group, {"+": 0, "-": 0})[position] = len(entries)
    positions = {}
    for group, per_position in counts.items():
        votes_for, votes_against = per_position["+"], per_position["-"]
        majority = None if votes_for == votes_against else "+" if votes_for > votes_against else "-"
        positions[group] = (majority, max(votes_for, votes_against), votes_for + votes_against)
    return positions


def day_statistics(date: str, documents: dict) -> dict:
    """
    :param documents: {<eu_document_code>: <content, with its "amendments">}, the documents voted on the day
    :return: {"members": {<kind of vote, see VOTE_KINDS>: {<identifier>: {"full_name", "group", "voted", "absent",
    "corrections"}}},
    "cohesion": {<kind>: {<group>: [<number of votes>, <sum of the shares of the members who voted like the majority>]}},
    "proximity": {<kind>: {(<group>, <other group>): [<votes where they had the same position>, <votes where both had
    a position>]}}, "corrections": [{"member_id", "date", "kind", "vote_id", "eu_document_code", "title", "label",
    "voted", "intended"}]} for the roll-call votes of the day
    """
    statistics = {kind: {} for kind in VOTE_KINDS}
    cohesion = {kind: {} for kind in VOTE_KINDS}
    proximity = {kind: {} for kind in VOTE_KINDS}
    corrections = []

    def member(kind, group, entry):
        stats = statistics[kind].setdefault(entry["id"], {"voted": 0, "absent": 0, "corrections": 0})
        stats["full_name"] = entry.get("full_name") or entry["name"]
        stats["group"] = group
        return stats

    # A roll-call vote may concern several documents, it's counted once
    roll_call_votes = {}
    final_votes = set()
    # {<vote identifier>: (<eu_document_code>, <title>)}, the first document of the vote
    vote_documents = {}
    for eu_document_code, content in documents.items():
        for vote in content.get("amendments", []):
            if vote.get("was_roll_call_voted") and vote.get("id"):
                roll_call_votes[vote["id"]] = vote
                vote_documents.setdefault(vote["id"], (eu_document_code, content.get("details", {}).get("title")))
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
            for group, entry in members(groups):
                member(kind, group, entry)["voted"] += 1
        for group, entry in members(vote["absent"]):
            member(kind, group, entry)["absent"] += 1
        for correction in vote.get("corrections", []):
            if correction.get("id") in statistics[kind]:
                if correction.get("voted") is not None:
                    statistics[kind][correction["id"]]["corrections"] += 1
                corrections.append({
                    "member_id": correction["id"], "date": date, "kind": kind, "vote_id": vote["id"],
                    "eu_document_code": vote_documents[vote["id"]][0], "title": vote_documents[vote["id"]][1],
                    "label": vote.get("label"), "voted": correction.get("voted"), "intended": correction.get("intended")})
    return {"members": statistics, "cohesion": cohesion, "proximity": proximity, "corrections": corrections}


def document_members(content: dict) -> dict:
    """
    Statistics of the members on the final vote of a document, for the podiums of the searches
    :return: {<identifier>: {"full_name", "group", "voted", "absent", "corrections"}}, empty when the final vote was not
    a roll-call vote ("votes" and "absent" are then those of another vote on the document: amendment, ...) or when the
    absents are not known (database filled before they were stored, or unidentified voters)
    """
    statistics = {}
    if content.get("absent") is None or not content.get("global", {}).get("was_roll_call_voted"):
        return statistics

    def member(group, entry):
        stats = statistics.setdefault(entry["id"], {"voted": 0, "absent": 0, "corrections": 0})
        stats["full_name"] = entry.get("full_name") or entry["name"]
        stats["group"] = group
        return stats

    for groups in content["votes"].values():
        for group, entries in groups.items():
            for entry in entries:
                if entry.get("id"):
                    member(group, entry)["voted"] += 1
    for group, entries in content["absent"].items():
        for entry in entries:
            member(group, entry)["absent"] += 1
    for correction in content.get("corrections", []):
        if correction.get("id") in statistics and correction.get("voted") is not None:
            statistics[correction["id"]]["corrections"] += 1
    return statistics


def document_group_positions(content: dict) -> dict | None:
    """
    How the groups voted on a document, to compare them. The abstentions don't count: only the votes for and against
    are compared.
    :return: {<group, EUROPEAN_PARLIAMENT or TOTAL_FRANCE>: <True if the majority voted for, False if against, None when
    as many voted for as against>}. None when the final vote was not a roll-call vote.
    """
    votes = content.get("votes")
    if not votes or not content["global"]["was_roll_call_voted"]:
        return None

    def majority(votes_for, votes_against):
        return None if votes_for == votes_against else votes_for > votes_against

    positions = {}
    for group in {group for vote_type in votes for group in votes[vote_type]}:
        positions[group] = majority(len(votes.get("+", {}).get(group, [])), len(votes.get("-", {}).get(group, [])))
    # Not compared when the result is unknown
    positions[EUROPEAN_PARLIAMENT] = content["global"].get("was_adopted")
    positions[TOTAL_FRANCE] = majority(sum(len(entries) for entries in votes.get("+", {}).values()),
                                       sum(len(entries) for entries in votes.get("-", {}).values()))
    return positions
