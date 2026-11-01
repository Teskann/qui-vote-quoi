import json
import os

from database.database import get_path
from parser.merger import merge_data
from parser.votes_page_parser import get_vote_results_for_date
from utils.date_management import date_range
from parser.empty_days_management import nothing_happened_on, set_something_happened_for
from parser.roll_call_votes_parser import get_roll_call_votes_xml_at_date, parse_all_votes, find_votes_in_previous_days


def dump_day_to_json(date: str, overwrite: bool = False, overwrite_empty_days: bool = False):
    """
    Dump the content of what happened on the passed date and write this in the database.
    If it's known that nothing happened in the passed date, this function does nothing.
    If a file already exists for the passed date and `overwrite` is False, this function does nothing
    :param date: date to dump, as iso-formatted string
    :param overwrite: set to True to overwrite the file for this date in the DB if it exists
    :param overwrite_empty_days: set to True to overwrite the data for the given day, even if it
    has been recorded as a day on which no votes happened
    """
    file_name = get_path(date + ".json")
    if os.path.exists(file_name) and not overwrite or nothing_happened_on(date) and not overwrite_empty_days:
        return
    if overwrite_empty_days:
        set_something_happened_for(date)
    xml = get_roll_call_votes_xml_at_date(date)
    if xml is None:
        return
    votes_per_document = parse_all_votes(xml, date)
    global_votes = get_vote_results_for_date(date)
    if global_votes is not None:
        missing_roll_call_votes = {document for document, result in global_votes.items()
                                   if result["was_roll_call_voted"] and not votes_per_document.get(document, {}).get("votes")}
        votes_per_document |= find_votes_in_previous_days(missing_roll_call_votes, date)
        votes_per_document = merge_data(votes_per_document, global_votes, date)
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(votes_per_document, f, indent=2, ensure_ascii=False)


def fill_database(start_date, end_date, overwrite=False, overwrite_empty_days=False):
    for date in date_range(start_date, end_date):
        print("Processing " + date + " ...")
        dump_day_to_json(date, overwrite=overwrite, overwrite_empty_days=overwrite_empty_days)
