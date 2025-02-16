import datetime
import json
from itertools import islice
from os.path import join, abspath, dirname

import jinja2

from server.filters import *
from urllib.parse import urlencode
from server.common import get_css, TEMPLATES_PATH


def generate_results_page(data):
    data["css"] = get_css()
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

    env.globals["today"] = datetime.date.today().isoformat()
    env.globals["yesterday"] = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    with open(join(TEMPLATES_PATH, "results.html.jinja"), encoding="utf-8") as f:
        template = env.from_string(f.read())
    return template.render(data)


if __name__ == "__main__":
    with open("/home/clement/dbtest/2024-03-14.json", 'r', encoding="utf-8") as f:
        data = json.load(f)
    html = generate_results_page({"data":data})
    with open("/home/clement/dbtest/2024-03-14.html", 'w', encoding="utf-8") as f:
        f.write(html)