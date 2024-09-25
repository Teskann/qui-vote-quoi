import json
from os.path import join, abspath, dirname

import jinja2

from server.filters import filter_political_group, is_last_iterator, to_pretty_date, political_group_url, \
    political_group_class, class_from_vote_result, political_group_tooltip

HERE = abspath(dirname(__file__))
TEMPLATES_PATH = join(HERE, "jinja_templates")
CSS_PATH = join(HERE, "css")


def get_css():
    with open(join(CSS_PATH, "results.css"), 'r') as f:
        return f.read()


def generate_table(data_for_eu_code):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    env.filters["political_group"] = filter_political_group
    env.filters["enumerate"] = enumerate
    env.filters["is_last_iterator"] = is_last_iterator
    env.filters["to_pretty_date"] = to_pretty_date
    env.filters["political_group_url"] = political_group_url
    env.filters["political_group_class"] = political_group_class
    env.filters["class_from_vote_result"] = class_from_vote_result
    env.filters["political_group_tooltip"] = political_group_tooltip
    with open(join(TEMPLATES_PATH, "results.html.jinja")) as f:
        template = env.from_string(f.read())
    return template.render(data_for_eu_code)


if __name__ == "__main__":
    with open("/home/clement/dbtest/2024-03-14.json", 'r') as f:
        data = json.load(f)
    html = generate_table({"data":data, "css": get_css()})
    with open("/home/clement/dbtest/2024-03-14.html", 'w') as f:
        f.write(html)