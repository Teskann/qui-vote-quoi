import json
import os
from concurrent.futures import ThreadPoolExecutor

from database.database import get_path
from parser.merger import merge_data
from parser import open_data
from parser.open_data import get_sitting_dates, OpenDataError
from parser.votes_page_parser import get_votes_results_xml, parse_vote_results, parse_amendments
from utils.date_management import date_range
from parser.empty_days_management import nothing_happened_on, set_something_happened_for
from parser.roll_call_votes_parser import get_roll_call_votes_xml_at_date, parse_all_votes, roll_call_votes_by_id


def __join_amendments(amendments: dict, roll_call_votes: dict) -> dict:
    """
    Add the votes of the members to the amendments voted by roll-call
    :param amendments: {<eu_document_code>: [<amendment>]}, from the votes results
    :param roll_call_votes: {<vote identifier>: <amendment>}, from the roll-call votes results
    """
    for document_amendments in amendments.values():
        for amendment in document_amendments:
            roll_call_vote = roll_call_votes.get(amendment["id"])
            if roll_call_vote is not None:
                amendment["votes"] = roll_call_vote["votes"]
                amendment["absent"] = roll_call_vote["absent"]
                amendment["corrections"] = roll_call_vote["corrections"]
                amendment["was_roll_call_voted"] = True
                amendment["global_votes"] = amendment["global_votes"] or roll_call_vote["global_votes"]
    return amendments


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
    votes_results_xml = get_votes_results_xml(date)
    if votes_results_xml is not None:
        global_votes = parse_vote_results(votes_results_xml)
        amendments = __join_amendments(parse_amendments(votes_results_xml), roll_call_votes_by_id(votes_per_document))
        votes_per_document = merge_data(votes_per_document, global_votes, date, amendments)
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(votes_per_document, f, indent=2, ensure_ascii=False)


MAX_PARALLEL_DAYS = 8


def sitting_dates_in_range(start_date: str, end_date: str) -> list[str]:
    """
    Dates of the plenary sittings between start_date and end_date (included).
    If the calendar of the sittings cannot be retrieved, all the dates of the range are returned.
    """
    all_dates = list(date_range(start_date, end_date))
    try:
        sittings = set()
        for year in range(int(start_date[:4]), int(end_date[:4]) + 1):
            sittings |= get_sitting_dates(year)
    except (OpenDataError, OSError) as error:
        print(f"Could not get the calendar of the sittings ({error}), processing all the days")
        return all_dates
    return [date for date in all_dates if date in sittings]


def fill_database(start_date, end_date, overwrite=False, overwrite_empty_days=False, jobs=None):
    dates = sitting_dates_in_range(start_date, end_date)
    print(f"{len(dates)} plenary sittings to process between {start_date} and {end_date}")

    def process(date):
        dump_day_to_json(date, overwrite=overwrite, overwrite_empty_days=overwrite_empty_days)
        print("Processed " + date, flush=True)

    throttled_before = open_data.throttled_requests

    with ThreadPoolExecutor(jobs or MAX_PARALLEL_DAYS) as executor:
        # list() propagates the exceptions raised in the threads
        list(executor.map(process, dates))

    throttled = open_data.throttled_requests - throttled_before
    if throttled:
        print(f"{throttled} requests were throttled by the server (HTTP 429) and retried, "
              f"consider reducing the number of jobs")
