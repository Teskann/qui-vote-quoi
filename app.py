import datetime
from urllib.parse import urlencode

from flask import Flask, request, redirect, abort, jsonify

from database.database import set_root_database_path
from database.storage import read_day
from database.members_index import get_member, get_all_members, get_member_corrections
from server.generate_about import generate_about
from server.generate_member import generate_member_page, generate_ranking_page, generate_group_page, filters_context
from server.generate_results import generate_results_page, generate_document_page
from server.filters import filter_political_group
from server.search_results import search_results
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
    start_date = args.get('start_date') or "2014-07-01"
    end_date = args.get('end_date') or datetime.date.today().isoformat()
    page = int(args.get('page') or 1)
    data = {"keywords": search, **search_results(start_date, end_date, search, page)}
    data["request"] = {"search": search, "start_date": start_date, "end_date": end_date, "page": page}
    return generate_results_page(data)

@app.route('/texte')
def document():
    """
    A document voted on a day, with all the votes held on it
    """
    date, eu_document_code = request.args.get('date') or "", request.args.get('code') or ""
    content = read_day(date).get(eu_document_code) if date else None
    if content is None:
        abort(404)
    return generate_document_page(date, eu_document_code, content)

def __filters() -> dict:
    """
    Filters of the statistics given in the URL: start_date, end_date and votes (see filters_context)
    """
    return filters_context(request.args.get('start_date') or None, request.args.get('end_date') or None,
                           request.args.get('votes'))

@app.route('/membre/<identifier>')
def member(identifier):
    filters = __filters()
    member_data = get_member(identifier, filters["start_date"], filters["end_date"], filters["kinds"])
    if member_data is None:
        abort(404)
    corrections = get_member_corrections(identifier, filters["start_date"], filters["end_date"], filters["kinds"])
    return generate_member_page(member_data, filters, corrections)

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
    return generate_ranking_page(__filters(), request.args.get('vue') == "groupes")

@app.route('/groupe/<slug>')
def group(slug):
    page = generate_group_page(slug, __filters())
    if page is None:
        abort(404)
    return page


@app.route('/about')
def about():
    return generate_about()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

