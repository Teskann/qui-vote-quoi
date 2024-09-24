import re

import bs4
import unidecode

from bs4 import BeautifulSoup

from utils import date_management
from parser.Document import scrap_documents_from_string


def __find_tables_from_eu_document_code(eu_document_code: str, html: BeautifulSoup):
    """
    Returns the first <tr> item coming right after the span that contains the EU document code
    :param eu_document_code: EU document code
    :param html: complete HTML content
    :return: <tr> item
    """
    # Return the last table matching the search
    spans = html.find_all('span', string=re.compile(
        r"(^|(.*\s+))" + re.escape(eu_document_code) + r"((\s+.*)|$)", flags=re.IGNORECASE | re.MULTILINE))
    span = spans[-1]
    return span.find_next('tr')


def __parse_votes_table(table: bs4.Tag) -> dict:
    """
    Parse a html table containing vote results (any of +, - or 0)
    """
    results = {}
    vote_type = table.find_next('span', string=re.compile(r"[+\-0]")).text
    results[vote_type] = {}
    for tr in table.find_all('tr')[1:]:  # Skip the first as it's used for vote type
        group = unidecode.unidecode(tr.find('span').text)
        votes = tr.find_all('td')[-1].text.split(', ')
        results[vote_type][group] = votes
    return results


def __parse_all_votes_tables(tables: bs4.Tag) -> dict:
    """
    Parse the html tables that contain vote results (+-0)
    """
    results = {}
    for table in tables.find_all('table'):

        # Select only the votes, the other table is vote corrections, in a deeper html tag
        if table.parent.parent != tables:
            continue

        results |= __parse_votes_table(table)
    return results


def __get_voters(eu_document_code: str, html: BeautifulSoup) -> dict:
    """
    Get the vote results contained in `html` for the passed EU document code
    :param eu_document_code: EU document code to check
    :param html: complete HTML content
    :return: votes results as a dict
    """
    results_table = __find_tables_from_eu_document_code(eu_document_code, html)
    return __parse_all_votes_tables(results_table)


def parse_all_votes(html: BeautifulSoup, date: str) -> dict:
    """
    Parses the passed html and return the vote result as a dict
    :param html: complete HTML content to parse
    :param date: date to check
    :return:
    """
    votes_per_document = {}
    all_documents = scrap_documents_from_string(html.prettify(formatter="html"))
    for document in all_documents:
        votes_per_document[str(document)] = {
            "votes": __get_voters(str(document), html),
            "date": date,
            "votes_source_url": date_management.votes_source_url(date),
            "details": document.to_dict()
        }
    return votes_per_document
