from parser.Document import Document
from utils import date_management


def merge_data(roll_call_votes_data, global_votes_data, date):
    merged = {}
    for document, global_votes_information in global_votes_data.items():
        merged[document] = {
            "votes": roll_call_votes_data[document]["votes"] if document in roll_call_votes_data else {},
            "date": date,
            "votes_source_url": date_management.votes_roll_call_source_url(date) if global_votes_information["was_roll_call_voted"] else date_management.votes_source_url(date),
            "details": Document(document).to_dict(),
            "global": global_votes_information
        }
    return merged