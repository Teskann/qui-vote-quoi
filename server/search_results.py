"""
Results of a search: the documents of the displayed page, and the statistics of all the documents found (podiums,
similarity of the groups), computed by SQLite from the statistics stored with each day (see database.statistics).
The statistics of the last searches are kept until the database changes, so that the next pages of a search only read
their documents.
"""
import threading
from collections import OrderedDict

from database import storage
from database.database_reader import search_keys_in_time_range, search_members_in_time_range, \
    search_group_pairs_in_time_range
from database.statistics import EUROPEAN_PARLIAMENT, TOTAL_FRANCE
from server.filters import correlations
from server.podiums import search_podiums

RESULTS_PER_PAGE = 25
# Number of searches whose statistics are kept. The biggest one (all the votes since 2014) takes about 1.5 MB.
CACHED_SEARCHES = 8

__lock = threading.Lock()
__cache = {"database": None, "searches": OrderedDict()}


def __statistics(start_date: str, end_date: str, keywords: str) -> dict:
    """
    :return: {"keys": [(<date>, <eu_document_code>)] of the documents found, in chronological order, "podiums",
    "correlations", "days"}, see search_results
    """
    keys = search_keys_in_time_range(start_date, end_date, keywords)
    table = None
    if keys:
        groups, pairs = search_group_pairs_in_time_range(start_date, end_date, keywords)
        table = correlations(groups | {EUROPEAN_PARLIAMENT, TOTAL_FRANCE}, pairs)
    return {"keys": keys, "podiums": search_podiums(search_members_in_time_range(start_date, end_date, keywords)),
            "correlations": table, "days": {date for date, _ in keys}}


def __cached_statistics(start_date: str, end_date: str, keywords: str) -> dict:
    """
    Same as __statistics, kept for the last searches until the database changes
    """
    database = tuple(storage.days())
    search = (start_date, end_date, keywords)
    with __lock:
        if __cache["database"] != database:
            __cache["database"], __cache["searches"] = database, OrderedDict()
        if search in __cache["searches"]:
            __cache["searches"].move_to_end(search)
            return __cache["searches"][search]
    statistics = __statistics(start_date, end_date, keywords)
    with __lock:
        if __cache["database"] == database:
            __cache["searches"][search] = statistics
            while len(__cache["searches"]) > CACHED_SEARCHES:
                __cache["searches"].popitem(last=False)
    return statistics


def search_results(start_date: str, end_date: str, keywords: str, page: int) -> dict:
    """
    :return: {"data": {(<date>, <eu_document_code>): <content>} for the documents of the page, in chronological order
    (a document may be voted on several days: each vote is a result), "count": <number of documents found>,
    "podiums": <see search_podiums>, "correlations": <see correlations, None if nothing is found>, "days": {<date of a
    document found>}}
    """
    statistics = __cached_statistics(start_date, end_date, keywords)
    keys = statistics["keys"]
    # The most recent results come first
    displayed = keys[::-1][RESULTS_PER_PAGE * (page - 1):RESULTS_PER_PAGE * page][::-1]
    return {"data": storage.read_documents(displayed), "count": len(keys), "podiums": statistics["podiums"],
            "correlations": statistics["correlations"], "days": statistics["days"]}
