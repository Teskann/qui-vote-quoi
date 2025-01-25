import json
import os
import re

from unidecode import unidecode

from utils import date_management
from database.database import get_path
from database.database_writer import dump_day_to_json


def get_all_votes_for_day(date: str) -> dict:
    """
    Return the votes for a given day
    :param date: date as iso formatted string
    """
    file_name = get_path(date + ".json")
    if not os.path.exists(file_name):
        return {}
    else:
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)


def search_eu_document(keywords: str, date: str):
    all_votes_for_day = get_all_votes_for_day(date)
    keywords_re = ".*".join(map(lambda kw: re.escape(unidecode(kw)), keywords.split(" ")))
    keywords_regex = re.compile(f".*{keywords_re}.*", flags=re.IGNORECASE | re.MULTILINE)
    matching_items = {}
    for eu_document_code, value in all_votes_for_day.items():
        # This might happen if data is not completely available in europarl.europa.eu
        if "details" not in value:
            continue
        if keywords_regex.match(unidecode(" ".join([value["details"]["title"], value["details"]["description"], eu_document_code]))):
            matching_items[eu_document_code] = value
    return matching_items


def search_in_time_range(start_date: str, end_date: str, keywords: str):
    for date in date_management.date_range(start_date, end_date):
        yield search_eu_document(keywords, date)
