import json
import os

from database.database import get_path
from parser.merger import merge_data
from parser.votes_page_parser import get_vote_results_for_date
from utils.date_management import date_range
from parser.empty_days_management import nothing_happened_on
from parser.europarl_html_parser import parse_all_votes
from parser.request_europarl import get_roll_call_votes_html_at_date


def dump_day_to_json(date: str, overwrite: bool = False):
    """
    Dump the content of what happened on the passed date and write this in the database.
    If it's known that nothing happened in the passed date, this function does nothing.
    If a file already exists for the passed date and `overwrite` is False, this function does nothing
    :param date: date to dump, as iso-formatted string
    :param overwrite: set to True to overwrite the file for this date in the DB if it exists
    :param custom_destination: pass the path to the database (folder)
    """
    file_name = get_path(date + ".json")
    if os.path.exists(file_name) and not overwrite or nothing_happened_on(date):
        return
    html = get_roll_call_votes_html_at_date(date)
    if html is None:
        return
    votes_per_document = parse_all_votes(html)
    global_votes = get_vote_results_for_date(date)
    if global_votes is not None:
        votes_per_document = merge_data(votes_per_document, global_votes, date)
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(votes_per_document, f, indent=2, ensure_ascii=False)


def fill_database(start_date, end_date, overwrite=False):
    for date in date_range(start_date, end_date):
        print("Processing " + date + " ...")
        dump_day_to_json(date, overwrite=overwrite)
