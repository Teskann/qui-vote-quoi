import json
import os
import re

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
        with open(file_name, "r") as f:
            return json.load(f)


def search_eu_document(keywords, date):
    all_votes_for_day = get_all_votes_for_day(date)

    keywords_regex = re.compile(".*" + keywords.replace(" ", ".*") + ".*", flags=re.IGNORECASE | re.MULTILINE)
    matching_items = {}
    for eu_document_code, value in all_votes_for_day.items():
        if keywords_regex.match(value["details"]["title"]):
            matching_items[eu_document_code] = value
    return matching_items


def search_in_time_range(start_date, end_date, keywords):
    for date in date_management.date_range(start_date, end_date):
        yield from search_eu_document(keywords, date)
