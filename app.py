import datetime
from urllib.parse import urlencode

from flask import Flask, request, redirect

from database.database import set_root_database_path
from database.database_reader import search_in_time_range
from server.generate_about import generate_about
from server.generate_results import generate_results_page
from utils.date_management import parliament_number_from_date, date_from_parliament_number

set_root_database_path()
app = Flask(__name__)


@app.route('/')
def index():
    today = datetime.date.today().isoformat()
    current_parliament_date = date_from_parliament_number(parliament_number_from_date(today))
    args = {"start_date": current_parliament_date} if current_parliament_date else {}
    return redirect(f"/results?{urlencode(args)}")

@app.route('/results')
def results():
    args = request.args
    search = args.get('search') or ""
    start_date = args.get('start_date') or "2019-07-15"
    end_date = args.get('end_date') or datetime.date.today().isoformat()
    page = int(args.get('page') or 1)
    data = {"keywords": search, "data": {}}

    for result in search_in_time_range(start_date, end_date, search):
        for eu_document, content in result.items():
            if eu_document in data["data"] and content["votes"] == {}:
                continue
            data["data"][eu_document] = content

    data["request"] = {"search": search, "start_date": start_date, "end_date": end_date, "page": page}
    return generate_results_page(data)

@app.route('/about')
def about():
    return generate_about()

if __name__ == "__main__":
    app.run(debug=True)

