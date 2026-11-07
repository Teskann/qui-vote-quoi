import datetime
import re
import functools
from itertools import islice
from os.path import join

import jinja2

from server.filters import *
from urllib.parse import urlencode
from server.common import get_css, TEMPLATES_PATH
from server.podiums import search_podiums
from parser.open_data import get_amendments_documents, amendment_document
from utils.date_management import votes_roll_call_source_url


@functools.lru_cache(maxsize=1)
def __environment(today: datetime.date) -> jinja2.Environment:
    """
    Created once a day: the templates depend on the current date
    """
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    env.filters["political_group"] = filter_political_group
    env.filters["enumerate"] = enumerate
    env.filters["reversed"] = reversed
    env.filters["is_last_iterator"] = is_last_iterator
    env.filters["is_first_iterator"] = is_first_iterator
    env.filters["to_pretty_date"] = to_pretty_date
    env.filters["political_group_url"] = political_group_url
    env.filters["political_group_class"] = political_group_class
    env.filters["class_from_vote_result"] = class_from_vote_result
    env.filters["political_group_tooltip"] = political_group_tooltip
    env.filters["count_all_votes"] = count_all_votes
    env.filters["urlencode"] = urlencode
    env.filters["set_page"] = set_page
    env.filters["set_search"] = set_search
    env.filters["islice"] = islice
    env.filters["min"] = min
    env.filters["page_range"] = page_range
    env.filters["add_flags"] = add_flags
    env.filters["add_emojis"] = add_emojis
    env.filters["correlations"] = correlations
    env.filters["parliament_number_from_date"] = parliament_number_from_date
    env.filters["votes_on_day"] = votes_on_day
    env.filters["to_html_id"] = to_html_id
    env.filters["search_podiums"] = search_podiums
    env.filters["fr_number"] = fr_number

    env.filters["group_slug"] = group_slug
    env.filters["is_final_vote"] = is_final_vote
    env.filters["votes_roll_call_source_url"] = votes_roll_call_source_url

    env.globals["today"] = today.isoformat()
    env.globals["agree"] = agree
    env.globals["yesterday"] = (today - datetime.timedelta(days=1)).isoformat()
    return env


@functools.lru_cache(maxsize=2)
def __template(today: datetime.date, name: str = "results.html.jinja") -> jinja2.Template:
    """
    Compiled once a day, as the compilation takes longer than the rendering
    """
    with open(join(TEMPLATES_PATH, name), encoding="utf-8") as f:
        return __environment(today).from_string(f.read())


def generate_results_page(data):
    data["css"] = get_css()
    return __template(datetime.date.today()).render(data)


def __amendment_number(vote: dict) -> str | None:
    """
    :return: number of the amendment voted, None if the vote is not on an amendment. Before 2024, the number is only in
    the label ("A8-0193/2018 - Cláudia Monteiro de Aguiar - Am 32=33rev=").
    """
    if vote.get("amendment"):
        return vote["amendment"]
    number = re.search(r"\bAm (\d+)", vote.get("label") or "")
    return number[1] if number else None


def generate_document_page(date: str, eu_document_code: str, content: dict) -> str:
    """
    Page of a document voted on a day: its final vote, and all the votes held on it (amendments, paragraphs, ...)
    :param content: the document, with its amendments (see storage.read_day)
    """
    amendments = content.get("amendments", [])
    # Documents of the amendments on europarl, only asked when the document has amendments
    numbers = {vote.get("id"): __amendment_number(vote) for vote in amendments}
    documents = get_amendments_documents(eu_document_code) if any(numbers.values()) else []
    return __template(datetime.date.today(), "document_page.html.jinja").render(
        css=get_css(), date=date, eu_document_code=eu_document_code, data=content, amendments=amendments,
        amendment_numbers=numbers,
        amendment_links={identifier: amendment_document(number, documents) for identifier, number in numbers.items()})
