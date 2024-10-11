from os.path import join

import jinja2

from server.common import get_css, TEMPLATES_PATH


def generate_about():
    data = {"css": get_css()}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    with open(join(TEMPLATES_PATH, "about.html.jinja"), encoding="utf-8") as f:
        template = env.from_string(f.read())
    return template.render(data)