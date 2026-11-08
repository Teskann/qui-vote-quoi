from unidecode import unidecode

from database import storage


def get_all_votes_for_day(date: str) -> dict:
    """
    Return the votes for a given day, with the amendments
    :param date: date as iso formatted string
    """
    return storage.read_day(date)


def __keywords_matcher(keywords: str):
    """
    :return: function telling if a text contains all the keywords, in this order, ignoring the case and the accents
    """
    keywords = [unidecode(keyword).lower() for keyword in keywords.split()]

    def matches(text: str) -> bool:
        text, position = text.lower(), 0
        for keyword in keywords:
            position = text.find(keyword, position)
            if position < 0:
                return False
            position += len(keyword)
        return True

    return matches


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


def search_keys_in_time_range(start_date: str, end_date: str, keywords: str) -> list[tuple[str, str]]:
    """
    Same as search_in_time_range, without reading the content of the documents
    :return: [(<date>, <eu_document_code>)] in chronological order
    """
    return storage.search_keys(__keywords_matcher(keywords), start_date, end_date)


def search_members_in_time_range(start_date: str, end_date: str, keywords: str) -> list[dict]:
    """
    Statistics of the members on the final votes of the documents found, see storage.search_members
    """
    return storage.search_members(__keywords_matcher(keywords), start_date, end_date)


def search_group_pairs_in_time_range(start_date: str, end_date: str, keywords: str) -> tuple[set[str], dict]:
    """
    How often the groups voted alike on the documents found, see storage.search_group_pairs
    """
    return storage.search_group_pairs(__keywords_matcher(keywords), start_date, end_date)
