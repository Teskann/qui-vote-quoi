"""
Results of a search: the documents of the displayed page, and the statistics of all the documents found (podiums,
similarity of the groups), computed by SQLite from the statistics stored with each day (see database.statistics).
"""
from database import storage
from database.database_reader import search_keys_in_time_range, search_members_in_time_range, \
    search_group_pairs_in_time_range
from database.statistics import EUROPEAN_PARLIAMENT, TOTAL_FRANCE
from server.filters import correlations
from server.podiums import search_podiums

RESULTS_PER_PAGE = 25


def search_results(start_date: str, end_date: str, keywords: str, page: int) -> dict:
    """
    :return: {"data": {(<date>, <eu_document_code>): <content>} for the documents of the page, in chronological order
    (a document may be voted on several days: each vote is a result), "count": <number of documents found>,
    "podiums": <see search_podiums>, "correlations": <see correlations, None if nothing is found>, "days": {<date of a
    document found>}}
    """
    keys = search_keys_in_time_range(start_date, end_date, keywords)
    # The most recent results come first
    displayed = keys[::-1][RESULTS_PER_PAGE * (page - 1):RESULTS_PER_PAGE * page][::-1]
    table = None
    if keys:
        groups, pairs = search_group_pairs_in_time_range(start_date, end_date, keywords)
        table = correlations(groups | {EUROPEAN_PARLIAMENT, TOTAL_FRANCE}, pairs)
    return {"data": storage.read_documents(displayed), "count": len(keys),
            "podiums": search_podiums(search_members_in_time_range(start_date, end_date, keywords)),
            "correlations": table, "days": {date for date, _ in keys}}
