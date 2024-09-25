from flask import Flask, request

from database.database import set_root_database_path
from database.database_reader import search_in_time_range
from server.generate_about import generate_about
from server.generate_index import generate_index
from server.generate_results import generate_results_page

set_root_database_path()
app = Flask(__name__)


@app.route('/')
def hello_world():
    return generate_index()

@app.route('/results')
def results():
    args = request.args
    search = args.get('search')
    start_date = args.get('start_date')
    end_date = args.get('end_date')
    data = {"keywords": search, "data": {}}

    for result in search_in_time_range(start_date, end_date, search):
        data["data"] |= result
    return generate_results_page(data)

@app.route('/about')
def about():
    return generate_about()

