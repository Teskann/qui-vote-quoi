import re

import bs4
import requests
from bs4 import BeautifulSoup

from parser.Document import Document, scrap_documents_from_string
from utils.date_management import votes_source_url


def __get_votes_html(date: str) -> BeautifulSoup:
    """
    Return the votes html for a given date. Throws in case of error 404
    :param date: date as iso string
    :return: beautiful soup
    """
    response = requests.get(votes_source_url(date))

    if response.status_code != 200:
        raise Exception("Error", response.status_code, "for", date)
    return BeautifulSoup(response.text, 'html.parser')


def __get_main_eu_document(documents: set[Document]) -> tuple[Document, bool]:
    """
    Get the main document among a list of documents. The documents RC-B* have priority over B-*
    :param documents: list of documents
    :return: main document, True if it could find a main document, False otherwise
    """
    for document in documents:
        if document.prefix == "RC":
            return document, True
    return list(documents)[0], len(documents) == 1


def __find_eu_document_codes_in_html(html: BeautifulSoup) -> dict:
    """
    This returns all the voted document codes from the html, along with their tag
    :param html: input beautiful soup (whole page)
    :return: {"document code": <bs4.Tag>}
    """
    all_items = html.find_all("a", string=re.compile(".*" + Document.rexeg_str + ".*"))
    all_items += html.find_all("p", string=re.compile(".*" + Document.rexeg_str + ".*"))

    # Remove matches that are not the "header" of a table
    # In practice, headers are <p></p>, and sometimes in <p><a></a></p>
    valid_items = {}
    processed_documents = set()
    for item in all_items:
        if item.name == "p" or item.name == "a" and item.parent.name == "p":
            if item.name == "a":
                item = item.parent
            all_documents = scrap_documents_from_string(item.parent.prettify(formatter="html"))
            eu_document_code, succeeded = __get_main_eu_document(all_documents)
            if not succeeded:
                eu_document_code = list(scrap_documents_from_string(item.find_next(string=re.compile(".*" + Document.rexeg_str + ".*"))))[0]
            if str(eu_document_code) not in processed_documents:
                valid_items[str(eu_document_code)] = item
                processed_documents.update([str(doc) for doc in all_documents])
    return valid_items


def __find_vote_result_element(tag: bs4.Tag):
    """
    Find the vote result element of the page. Assume it's the last voted line (the last line of the table to contain
    either a "+" or a "-" in a cell)
    :param tag: tag containing the document code, typically a <p>
    :return: table row containing the vote results
    """
    table_results = tag.find_next("table")
    tds = table_results.find_all("td", string=re.compile(r"^[+\-—]$"))
    td = tds[-1] if len(tds) > 0 else None
    if td is None:
        return table_results.find_all("tr")[-1]
    return td.parent


def __get_votes_count(td: bs4.Tag) -> dict:
    """
    Parse the votes cell and return them in a dict.
    This function applies a locig to process <p>1, 2, 3</p> as well as <p><a>1, 2, 3</a></p>
    :param td: table cell containing the votes
    :return: dict of votes count
    """
    text = td.text
    while td.text == "" and td.next_element is not None:
        td = td.next_element
        text = td.text
    parts = text.split(",")
    return {"+": int(parts[0].strip()), "-": int(parts[1].strip()), "0": int(parts[2].strip())}


def __parse_vote_results(tr: bs4.Tag) -> dict:
    """
    Parse the vote results and return them in a dict
    :param tr: table row containing the vote results
    :return: dict
    """
    roll_name_voted_td = tr.find("td", recursive=False, string="AN")
    was_adopted_td = tr.find("td", recursive=False, string=re.compile(r"[+\-—]"))
    votes_result_td = was_adopted_td.find_next_sibling("td") if was_adopted_td is not None else None
    if roll_name_voted_td is None and was_adopted_td is None:
        return {"was_roll_call_voted": False, "was_adopted": True}
    if roll_name_voted_td is not None and was_adopted_td is not None:
        was_adopted = was_adopted_td.text == "+"
        return {"was_roll_call_voted": True, "was_adopted": was_adopted, "global_votes": __get_votes_count(votes_result_td)}

    else:
        was_adopted = was_adopted_td.text == "+" if was_adopted_td is not None else True
        return {"was_roll_call_voted": False, "was_adopted": was_adopted}


def __get_vote_results_for_all_documents(documents: dict):
    """
    Returns the vote results for all the provided documents
    :param documents: {<eu_document_code>: <bs4.Tag>}
    :return: dict with the vote results for each document
    """
    results = {}
    for eu_document_code, tag in documents.items():
        results[eu_document_code] = __parse_vote_results(__find_vote_result_element(tag))
    return results

def get_vote_results_for_date(date: str):
    """
    Get the vote results for a given date
    :param date: date as iso string
    :return: dict of all the voted textx {<eu_document_code>: <vote_results>}
    """
    return __get_vote_results_for_all_documents(
        __find_eu_document_codes_in_html(__get_votes_html(date))
    )
