import requests
from bs4 import BeautifulSoup

from utils import date_management
from parser.empty_days_management import set_nothing_happened_for


def __create_request_for_roll_call(date: str):
    """
    Create the web request to contact europarl website
    :param date: date as iso-formatted string
    :return: url, headers, data
    """
    url = "https://www.europarl.europa.eu/doceo/document/filter"
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
    }
    data = {
        "groupPol": "ALL",
        "country": "FR",
        "reference": f"PV-{date_management.parliament_number_from_date(date)}-{date}-RCV",
        "langNav": "FR",
        "langDoc": "FR",
        "mep": "",
        "xm": "N"
    }
    return url, headers, data


def __get_roll_call_votes_html(url: str, headers: dict, data: dict) -> BeautifulSoup | None:
    """
    Contacts europarl website and returns the HTML of the response in a BeautifulSoup object
    If the result is empty because nothing happened in parliament on this date, None is returned
    :param url: url to query
    :param headers: request's headers
    :param data: request's data
    :return: Content of html response if it's not empty
    """
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception("Invalid response")
    html = BeautifulSoup(response.text, 'html.parser')

    # Checking if the response is empty.
    # If it's empty, the response contains a div#allEmpty with the text Y
    all_empty = html.find("div", id="allEmpty")
    if all_empty is not None and all_empty.text == "Y":
        return None

    return html


def get_roll_call_votes_html_at_date(date: str) -> BeautifulSoup | None:
    """
    Contacts europarl website and returns the HTML of the response in a BeautifulSoup object
    If the result is empty because nothing happened in parliament on this date, None is returned
    and the date is registered in the empty_days.txt file.
    :param date: date as iso formatted string
    :return: None if nothing was voted on this date, HTML content otherwise
    """
    req = __create_request_for_roll_call(date=date)
    html = __get_roll_call_votes_html(*req)
    if html is None:
        set_nothing_happened_for(date)
    return html

