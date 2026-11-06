import re

from unidecode import unidecode

from database import storage


def get_all_votes_for_day(date: str) -> dict:
    """
    Return the votes for a given day, with the amendments
    :param date: date as iso formatted string
    """
    return storage.read_day(date)


def __keywords_matcher(keywords: str):
    keywords_re = ".*".join(map(lambda kw: re.escape(unidecode(kw)), keywords.split(" ")))
    keywords_regex = re.compile(f".*{keywords_re}.*", flags=re.IGNORECASE | re.MULTILINE)
    return lambda text: keywords_regex.match(text) is not None


def search_eu_document(keywords: str, date: str) -> dict:
    """
    Documents voted on the given day whose title, description or code contain the keywords, in this order.
    The amendments are not returned.
    """
    for _, documents in storage.search_documents(__keywords_matcher(keywords), date, date):
        return documents
    return {}


def search_in_time_range(start_date: str, end_date: str, keywords: str):
    """
    Same as search_eu_document, for all the days between start_date and end_date (included)
    :return: {<eu_document_code>: <content>} for each day with matching documents, in chronological order
    """
    for _, documents in storage.search_documents(__keywords_matcher(keywords), start_date, end_date):
        yield documents
