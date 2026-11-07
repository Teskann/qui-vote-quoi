import datetime

from database import storage
from database import database_writer
from parser import open_data
from server import filters, generate_results
from server.generate_member import generate_member_page
from tests.setup_database import clear_database


def set_genders(genders):
    clear_database()
    storage.write_genders(genders)
    # The genders read before are forgotten
    getattr(filters, "__genders")["read_at"] = None


def member(identifier):
    return {"name": identifier, "id": identifier, "full_name": f"Député {identifier}"}


def test_agree():
    set_genders({"f1": "F", "f2": "F", "m": "M"})
    assert filters.agree(member("f1"), "absent", "absente") == "absente"
    assert filters.agree("m", "absent", "absente") == "absent"
    # Unknown gender
    assert filters.agree(member("x"), "absent", "absente") == "absent"
    assert filters.agree(member("x"), "absent", "absente", "absent(e)") == "absent(e)"
    assert filters.agree("Dupont", "absent", "absente") == "absent"  # Member without identifier
    # Several members: feminine only if they are all women
    assert filters.agree([member("f1"), member("f2")], "absents", "absentes") == "absentes"
    assert filters.agree([member("f1"), member("m")], "absents", "absentes") == "absents"
    assert filters.agree([member("f1"), member("x")], "absents", "absentes") == "absents"
    assert filters.agree([], "absents", "absentes") == "absents"


def test_fill_genders(monkeypatch):
    clear_database()
    storage.write_genders({"known": "M"})
    asked = []
    monkeypatch.setattr(open_data, "get_meps", lambda term: [{"identifier": "known"}, {"identifier": f"{term}"}])
    monkeypatch.setattr(open_data, "get_mep_gender", lambda identifier: asked.append(identifier) or
                        {"8": "F", "9": "M"}.get(identifier))
    database_writer.fill_genders("2020-01-01")
    # Terms 8 and 9: the known member is not asked again, the member without gender is not stored
    assert sorted(asked) == ["8", "9"]
    assert storage.read_genders() == {"known": "M", "8": "F", "9": "M"}


def render(template, **context):
    with open(f"server/jinja_templates/{template}", encoding="utf-8") as f:
        source = f.read()
    environment = getattr(generate_results, "__environment")(datetime.date.today())
    return environment.from_string(source).module


def test_corrections_section():
    set_genders({"f1": "F", "f2": "F", "m": "M"})
    section = render("corrections.html.jinja").corrections_section
    one = str(section([{**member("f1"), "voted": "0", "intended": "+"}]))
    assert "S'est trompée de bouton" in one and "s'est abstenue" in one
    assert "S'est trompé de bouton" in str(section([{**member("m"), "voted": "+", "intended": "-"}]))
    women = [{**member(i), "voted": "+", "intended": "-"} for i in ("f1", "f2")]
    assert "Se sont trompées de bouton" in str(section(women))
    mixed = women + [{**member("m"), "voted": "0", "intended": "-"}]
    text = str(section(mixed))
    assert "Se sont trompés de bouton" in text and "s'est abstenu<" in text


def test_votes_table_legend_and_card():
    set_genders({"f1": "F", "f2": "F", "m": "M"})
    table = render("votes_table.html.jinja").create_votes_table
    votes = {"+": {"France / PPE :": [member("m")]}, "0": {"France / PPE :": [member("f1")], "France / S&D :": [member("f2")]}}
    text = str(table(votes, "2025-01-01", {"France / PPE :": [member("f1"), member("m")]}))
    assert "Se sont abstenues" in text and "Absents<" in text
    assert 'data-id="f1" data-full-name="Député f1" data-gender="F"' in text
    assert 'data-id="m" data-full-name="Député m" data-gender="M"' in text


def test_member_page():
    set_genders({"f1": "F", "m": "M"})
    stats = {"voted": 10, "absent": 2, "corrections": 1, "members_count": 2,
             "ranks": {"absent_rate": 1, "absent": 1, "corrections": 1, "voted": 1}, "group": "France / PPE :",
             "months": {}, "recent": [{"date": "2025-01-01", "eu_document_code": "A10-0001/2025", "title": "Rapport",
                                        "vote": "absent", "was_adopted": True}]}
    filters_context = {"start_date": None, "end_date": None, "votes": "tous", "terms": []}
    woman = generate_member_page({**member("f1"), **stats}, filters_context, [])
    assert "S'est trompée de bouton" in woman and ">Absente<" in woman
    man = generate_member_page({**member("m"), **stats}, filters_context, [])
    assert "S'est trompé de bouton" in man and ">Absent<" in man
    unknown = generate_member_page({**member("x"), **stats}, filters_context, [])
    assert ">Absent(e)<" in unknown
