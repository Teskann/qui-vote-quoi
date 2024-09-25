from os.path import join, abspath, dirname

HERE = abspath(dirname(__file__))
TEMPLATES_PATH = join(HERE, "jinja_templates")
CSS_PATH = join(HERE, "css")

def get_css():
    with open(join(CSS_PATH, "results.css"), 'r') as f:
        return f.read()

def get_index_css():
    with open(join(CSS_PATH, "index.css"), 'r') as f:
        return f.read()
