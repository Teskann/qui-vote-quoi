from os.path import join

import jinja2

from server.common import TEMPLATES_PATH, get_index_css


def generate_index():
    data = {"css": get_index_css()}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    with open(join(TEMPLATES_PATH, "index.html.jinja")) as f:
        template = env.from_string(f.read())
    return template.render(data)