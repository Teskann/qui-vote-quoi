from concurrent.futures import ThreadPoolExecutor

from database import storage
from parser.merger import merge_data
from parser import open_data
from parser.open_data import get_sitting_dates, OpenDataError
from parser.votes_page_parser import get_votes_results_xml, parse_vote_results, parse_amendments
from utils.date_management import date_range, parliament_number_from_date
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
                amendment["dlv_id"] = roll_call_vote["dlv_id"]
                amendment["was_roll_call_voted"] = True
                amendment["global_votes"] = amendment["global_votes"] or roll_call_vote["global_votes"]
    return amendments


def __add_amendment_links(votes_per_document: dict):
    """
    Store in each vote on an amendment the URL of the document of the amendment on europarl ("amendment_url", None if
    unknown), so that the website never has to ask europarl. Raises OpenDataError if europarl can't be reached: the day
    is then not written, and is processed again by the next filling.
    """
    for eu_document_code, content in votes_per_document.items():
        amendments = content.get("amendments", [])
        numbers = [open_data.amendment_number(vote) for vote in amendments]
        # Only asked when the document has amendments
        documents = open_data.get_amendments_documents(eu_document_code) if any(numbers) else []
        for vote, number in zip(amendments, numbers):
            vote["amendment_url"] = open_data.amendment_document(number, documents)


def dump_day(date: str, overwrite: bool = False, overwrite_empty_days: bool = False):
    """
    Get what was voted on the passed date and write it in the database.
    If it's known that nothing happened in the passed date, this function does nothing.
    If the date is already in the database and `overwrite` is False, this function does nothing
    :param date: date to dump, as iso-formatted string
    :param overwrite: set to True to overwrite the date in the DB if it exists
    :param overwrite_empty_days: set to True to overwrite the data for the given day, even if it
    has been recorded as a day on which no votes happened
    """
    if storage.day_exists(date) and not overwrite or nothing_happened_on(date) and not overwrite_empty_days:
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
    __add_amendment_links(votes_per_document)
    storage.write_day(date, votes_per_document)


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


FIRST_PARLIAMENTARY_TERM = 8  # The votes per country are only known since the 2014 term


def fill_genders(end_date: str, jobs: int | None = None):
    """
    Store the gender of the French members whose gender is not stored yet, from the 2014 term to the one of end_date.
    The members of all the terms are looked at, so that a database filled before the genders were stored gets them.
    """
    known = storage.read_genders()
    last_term = parliament_number_from_date(end_date)
    print(f"Looking for the members whose gender is unknown (terms {FIRST_PARLIAMENTARY_TERM} to {last_term}, "
          f"{len(known)} genders already stored)", flush=True)
    try:
        identifiers = {mep["identifier"] for term in range(FIRST_PARLIAMENTARY_TERM, last_term + 1)
                       for mep in open_data.get_meps(term)} - set(known)
        if not identifiers:
            print("The genders of all the members are already stored")
            return
        print(f"Getting the gender of {len(identifiers)} members", flush=True)
        with ThreadPoolExecutor(jobs or MAX_PARALLEL_DAYS) as executor:
            genders = dict(zip(identifiers, executor.map(open_data.get_mep_gender, identifiers)))
    except (OpenDataError, OSError) as error:
        print(f"Could not get the genders of the members ({error})")
        return
    found = {identifier: gender for identifier, gender in genders.items() if gender}
    storage.write_genders(found)
    print(f"Stored the gender of {len(found)} members "
          f"({sum(gender == 'F' for gender in found.values())} women, {sum(gender == 'M' for gender in found.values())} men)")
    missing = sorted(set(genders) - set(found))
    if missing:
        print(f"No gender given by the open data portal for {len(missing)} members: {', '.join(missing)}")


def fill_database(start_date, end_date, overwrite=False, overwrite_empty_days=False, jobs=None):
    dates = sitting_dates_in_range(start_date, end_date)
    print(f"{len(dates)} plenary sittings to process between {start_date} and {end_date}")

    def process(date):
        dump_day(date, overwrite=overwrite, overwrite_empty_days=overwrite_empty_days)
        print("Processed " + date, flush=True)

    throttled_before = open_data.throttled_requests

    with ThreadPoolExecutor(jobs or MAX_PARALLEL_DAYS) as executor:
        # list() propagates the exceptions raised in the threads
        list(executor.map(process, dates))
    fill_genders(end_date, jobs)

    throttled = open_data.throttled_requests - throttled_before
    if throttled:
        print(f"{throttled} requests were throttled by the server (HTTP 429) and retried, "
              f"consider reducing the number of jobs")
