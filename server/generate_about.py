import functools
from os.path import join

import jinja2

from server.common import get_css, TEMPLATES_PATH


@functools.cache
def __template() -> jinja2.Template:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    with open(join(TEMPLATES_PATH, "about.html.jinja"), encoding="utf-8") as f:
        return env.from_string(f.read())


def generate_about():
    return __template().render({"css": get_css()})