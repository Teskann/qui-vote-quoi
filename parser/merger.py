from concurrent.futures import ThreadPoolExecutor

from parser.Document import Document
from utils import date_management


MAX_PARALLEL_REQUESTS = 8

# Largest gap between the totals of the votes results and those of the roll-call votes results for the same vote. They
# are equal since 2024, and differ by up to 6 votes on a few votes before.
TOTALS_TOLERANCE = 6


def __totals_gap(vote: dict, totals: dict) -> int | None:
    """
    :return: sum of the differences between the totals ("+", "-", "0") of a roll-call vote and the given ones, None if
    they are unknown
    """
    counts = vote.get("global_votes") or {}
    if not all(isinstance(counts.get(key), int) for key in totals):
        return None
    return sum(abs(counts[key] - totals[key]) for key in totals)


def __final_vote(roll_call_votes: dict, global_votes_information: dict) -> dict | None:
    """
    Roll-call vote on the whole document. The roll-call votes results don't say which one it is: it's the one whose
    totals are those of the result of the document. The last vote on the document is often an amendment or a procedural
    vote (referral to committee, ...), or the final vote took place another day.
    :param roll_call_votes: the roll-call votes on the document, see parse_all_votes
    :param global_votes_information: result of the document, see the votes results parser
    :return: the roll-call vote (see "amendments" in parse_all_votes), None if no roll-call vote of the day has the totals
    of the result. When these totals are unknown, the last roll-call vote on the document.
    """
    votes = roll_call_votes.get("amendments", [])
    totals = global_votes_information.get("global_votes") or {}
    if not all(isinstance(totals.get(key), int) for key in ("+", "-", "0")):
        return votes[-1] if votes else None
    gaps = [(gap, position) for position, vote in enumerate(votes)
            if (gap := __totals_gap(vote, totals)) is not None and gap <= TOTALS_TOLERANCE]
    # The closest vote, the last one when several have the same totals
    return votes[min(gaps, key=lambda gap: (gap[0], -gap[1]))[1]] if gaps else None


def merge_data(roll_call_votes_data, global_votes_data, date, amendments_data=None):
    amendments_data = amendments_data or {}
    with ThreadPoolExecutor(MAX_PARALLEL_REQUESTS) as executor:
        details = dict(zip(global_votes_data, executor.map(lambda document: Document(document).to_dict(), global_votes_data)))
    merged = {}
    for document, global_votes_information in global_votes_data.items():
        roll_call_votes = roll_call_votes_data.get(document, {})
        final = __final_vote(roll_call_votes, global_votes_information) \
            if global_votes_information["was_roll_call_voted"] else None
        merged[document] = {
            # Votes of the members on the whole document, unknown when its final vote is not among the roll-call votes
            # of the day
            "votes": final["votes"] if final else {},
            "absent": final["absent"] if final else None,
            "corrections": final["corrections"] if final else [],
            # Identifier of the final vote among "amendments"
            "final_vote_id": final["id"] if final else None,
            "date": date,
            "votes_source_url": date_management.votes_roll_call_source_url(date, final["id"] if final else None,
                                                                           final.get("dlv_id") if final else None)
            if global_votes_information["was_roll_call_voted"] else date_management.votes_source_url(date),
            "details": details[document],
            "global": global_votes_information,
            # All the votes held on the document. The votes results give the result of each vote, but are only
            # usable since 2024. Before, only the roll-call votes are known.
            "amendments": amendments_data.get(document, roll_call_votes.get("amendments", [])),
        }
    return merged
