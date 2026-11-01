from concurrent.futures import ThreadPoolExecutor

from parser.Document import Document
from utils import date_management


MAX_PARALLEL_REQUESTS = 8


def merge_data(roll_call_votes_data, global_votes_data, date, amendments_data=None):
    amendments_data = amendments_data or {}
    with ThreadPoolExecutor(MAX_PARALLEL_REQUESTS) as executor:
        details = dict(zip(global_votes_data, executor.map(lambda document: Document(document).to_dict(), global_votes_data)))
    merged = {}
    for document, global_votes_information in global_votes_data.items():
        roll_call_votes = roll_call_votes_data.get(document, {})
        merged[document] = {
            "votes": roll_call_votes.get("votes", {}),
            "date": date,
            "votes_source_url": date_management.votes_roll_call_source_url(date) if global_votes_information["was_roll_call_voted"] else date_management.votes_source_url(date),
            "details": details[document],
            "global": global_votes_information,
            # All the votes held on the document. The votes results give the result of each vote, but are only
            # usable since 2024. Before, only the roll-call votes are known.
            "amendments": amendments_data.get(document, roll_call_votes.get("amendments", [])),
        }
    return merged
