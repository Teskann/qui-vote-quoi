import json

from database import storage
from database.database import get_path
from migrate_json_to_sqlite import migrate
from tests.setup_database import clear_database


def document(title, amendments=None):
    content = {"votes": {}, "details": {"title": title, "description": "Description"},
               "global": {"was_roll_call_voted": False, "was_adopted": True}}
    if amendments is not None:
        content["amendments"] = amendments
    return content


def test_write_and_read_day():
    clear_database()
    day = {"B10-0002/2025": document("Résolution sur l'Ukraine", [{"id": "1"}]),
           "A10-0001/2025": document("Rapport", [])}
    storage.write_day("2025-03-12", day)

    assert storage.day_exists("2025-03-12")
    assert not storage.day_exists("2025-03-13")
    # The documents keep their order
    assert storage.read_day("2025-03-12") == day
    assert list(storage.read_day("2025-03-12")) == ["B10-0002/2025", "A10-0001/2025"]
    assert storage.read_day("2025-03-12", with_amendments=False)["B10-0002/2025"] == document("Résolution sur l'Ukraine")
    assert storage.read_amendments("2025-03-12") == {"B10-0002/2025": [{"id": "1"}], "A10-0001/2025": []}

    # The search text has no accent
    found = list(storage.search_documents(lambda text: "resolution" in text.lower(), "2025-01-01", "2025-12-31"))
    assert found == [("2025-03-12", {"B10-0002/2025": document("Résolution sur l'Ukraine")})]

    # Writing a day again replaces it, and changes its update time
    updated_at = storage.days()[0][1]
    storage.write_day("2025-03-12", {"A10-0003/2025": document("Autre rapport")})
    assert storage.read_day("2025-03-12") == {"A10-0003/2025": document("Autre rapport")}
    assert storage.read_amendments("2025-03-12") == {}
    assert storage.days()[0][1] > updated_at

    # A day without any document still exists
    storage.write_day("2025-03-13", {})
    assert [date for date, _ in storage.days()] == ["2025-03-12", "2025-03-13"]
    assert storage.read_day("2025-03-13") == {}


def test_migrate_json_files():
    clear_database()
    day = {"A10-0001/2025": document("Rapport", [{"id": "1"}]), "B10-0002/2025": document("Résolution")}
    with open(get_path("2025-03-12.json"), "w", encoding="utf-8") as f:
        json.dump(day, f)

    assert migrate() == (1, 1)
    assert storage.read_day("2025-03-12") == day
    # Already converted
    assert migrate() == (0, 1)
    assert migrate(overwrite=True) == (1, 1)
