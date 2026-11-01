from parser.Document import Document
from utils import date_management


def merge_data(roll_call_votes_data, global_votes_data, date):
    merged = {}
    for document, global_votes_information in global_votes_data.items():
        roll_call_votes = roll_call_votes_data.get(document, {})
        # The roll-call vote may have been published on a previous day (see find_votes_in_previous_days)
        roll_call_date = roll_call_votes.get("date", date)
        merged[document] = {
            "votes": roll_call_votes.get("votes", {}),
            "date": date,
            "votes_source_url": date_management.votes_roll_call_source_url(roll_call_date) if global_votes_information["was_roll_call_voted"] else date_management.votes_source_url(date),
            "details": Document(document).to_dict(),
            "global": global_votes_information
        }
    return merged
