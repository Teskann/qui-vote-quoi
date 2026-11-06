import datetime
from urllib.parse import urlencode

from flask import Flask, request, redirect, abort, jsonify

from database.database import set_root_database_path
from database.database_reader import search_in_time_range
from database.members_index import get_member, get_all_members, warm_up
from server.generate_about import generate_about
from server.generate_member import generate_member_page, generate_ranking_page
from server.generate_results import generate_results_page
from server.filters import filter_political_group
from utils.date_management import parliament_number_from_date, date_from_parliament_number

set_root_database_path()
warm_up()
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
    start_date = args.get('start_date') or "2014-07-01"
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

@app.route('/membre/<identifier>')
def member(identifier):
    member_data = get_member(identifier)
    if member_data is None:
        abort(404)
    return generate_member_page(member_data)

@app.route('/membres.json')
def members_list():
    """
    Members of the database, for the search suggestions
    """
    return jsonify([{"id": member["id"], "name": member["full_name"],
                     "group": filter_political_group(member["group"]).replace("&nbsp;", " ")}
                    for member in sorted(get_all_members(), key=lambda member: member["full_name"])])

@app.route('/classement')
def ranking():
    return generate_ranking_page(request.args.get('start_date') or None, request.args.get('end_date') or None)

@app.route('/about')
def about():
    return generate_about()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

