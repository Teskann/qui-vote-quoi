import re

import bs4
import requests
from bs4 import BeautifulSoup

from parser.Document import Document, scrap_documents_from_string
from tests.utils.workarounds import find_all_next_fixed, find_all_fixed, find_all_previous_fixed
from utils.date_management import votes_source_url


class Error404(Exception):
    pass


def __get_votes_html(date: str) -> BeautifulSoup:
    """
    Return the votes html for a given date. Throws in case of error 404
    :param date: date as iso string
    :return: beautiful soup
    """
    headers = {
        'accept': '*/*',
        'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'origin': 'https://www.europarl.europa.eu',
        'priority': 'u=1, i',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    }
    response = requests.get(votes_source_url(date), headers=headers)

    if response.status_code != 200:
        raise Error404("Error", response.status_code, "for", date)
    return BeautifulSoup(response.text, 'lxml')


def __get_main_eu_document(documents: set[Document], item_html: bs4.Tag) -> tuple[Document, bool]:
    """
    Get the main document among a list of documents. The documents RC-B* have priority over B-*
    :param documents: list of documents
    :return: main document, True if it could find a main document, False otherwise
    """
    if len(documents) == 1:
        return list(documents)[0], True
    else :
        pass

    last_vote_cell = __find_last_vote_cell(item_html)
    if last_vote_cell is not None:
        all_code_items = find_all_previous_fixed(last_vote_cell, ["a", "p", "td"], string=re.compile(r".*(?<!-)(" + "|".join([re.escape(str(doc)) for doc in documents]) + ").*", flags=re.MULTILINE | re.DOTALL | re.IGNORECASE))
        if len(all_code_items) > 0:
            code_item = all_code_items[0]
            return list(scrap_documents_from_string(code_item.prettify() + " " + code_item.text))[0], True

    return list(documents)[0], False


def __find_eu_document_codes_in_html(html: BeautifulSoup) -> dict:
    """
    This returns all the voted document codes from the html, along with their tag
    :param html: input beautiful soup (whole page)
    :return: {"document code": <bs4.Tag>}
    """
    all_items = find_all_fixed(html, "a", string=re.compile(".*" + Document.rexeg_str + ".*", flags=re.MULTILINE | re.DOTALL | re.IGNORECASE))
    all_items += find_all_fixed(html,"p", string=re.compile(".*" + Document.rexeg_str + ".*", flags=re.MULTILINE | re.DOTALL | re.IGNORECASE))

    # Remove matches that are not the "header" of a table
    # In practice, headers are <p></p>, and sometimes in <p><a></a></p>
    valid_items = {}
    processed_documents = set()
    for item in all_items:
        if item.name == "p" or item.name == "a" and item.parent.name == "p":
            if item.name == "a":
                item = item.parent
            item_html = item.parent.prettify(formatter="html")
            all_documents = scrap_documents_from_string(item_html + " " + item.text)
            if not all_documents:
                continue
            eu_document_code, succeeded = __get_main_eu_document(all_documents, item)
            if not succeeded:
                next_td = find_all_next_fixed(item,"td", string=re.compile(".*" + Document.rexeg_str + ".*", flags=re.MULTILINE | re.DOTALL | re.IGNORECASE))
                if next_td is None or len(next_td) == 0:
                    continue
                eu_document_code = list(scrap_documents_from_string(next_td[0].prettify()))[0]
            if str(eu_document_code) not in processed_documents:
                valid_items[str(eu_document_code)] = item
                processed_documents.update([str(doc) for doc in all_documents])
    return valid_items


def __find_last_vote_cell(tag: bs4.Tag) -> bs4.Tag | None:
    table_results = tag.find_next("table")
    tds = find_all_fixed(table_results, "td", string=re.compile(r"^\s*[+\-—]\s*$"))
    return tds[-1] if len(tds) > 0 else None


def __find_vote_result_element(tag: bs4.Tag):
    """
    Find the vote result element of the page. Assume it's the last voted line (the last line of the table to contain
    either a "+" or a "-" in a cell)
    :param tag: tag containing the document code, typically a <p>
    :return: table row containing the vote results
    """
    table_results = tag.find_next("table")
    td = __find_last_vote_cell(tag)
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
    if td is None:
        return {"+": "Données indisponibles", "-": "Données indisponibles", "0": "Données indisponibles"}
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
    roll_name_voted_td = tr.find("td", recursive=False, string=re.compile("\s*AN\s*"))
    was_adopted_td = tr.find("td", recursive=False, string=re.compile(r"\s*[+\-—]\s*"))
    votes_result_td = tr.find(["td", "a"], recursive=True, string=re.compile(r"\s*\d+,\s*\d+,\s*\d+\s*"))
    if roll_name_voted_td is None and was_adopted_td is None:
        return {"was_roll_call_voted": False, "was_adopted": True}
    if roll_name_voted_td is not None and was_adopted_td is not None:
        was_adopted = was_adopted_td.text.strip() == "+"
        return {"was_roll_call_voted": True, "was_adopted": was_adopted, "global_votes": __get_votes_count(votes_result_td)}

    else:
        was_adopted = was_adopted_td.text.strip() == "+" if was_adopted_td is not None else True
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

def get_vote_results_for_date(date: str) -> dict | None:
    """
    Get the vote results for a given date
    :param date: date as iso string
    :return: dict of all the voted textx {<eu_document_code>: <vote_results>}
    """
    try:
        return __get_vote_results_for_all_documents(
            __find_eu_document_codes_in_html(__get_votes_html(date))
        )
    except Error404:
        return None
