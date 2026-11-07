import json
import os

from database.database import get_database_path
from database.database_reader import get_all_votes_for_day
from database.database_writer import dump_day
from database.storage import day_exists
from parser.empty_days_management import set_nothing_happened_for, nothing_happened_on
from tests.setup_database import clear_database

EXPECTED_DESTINATION = os.path.join(get_database_path(), "..", "expected")


def expected_path(date):
    return os.path.join(EXPECTED_DESTINATION, date + ".json")


def open_expected(date):
    with open(expected_path(date), "r", encoding="utf-8") as f:
        return json.load(f)


def open_actual(date):
    """
    Open the actual result, without the amendments which are tested separately
    """
    data = get_all_votes_for_day(date)
    for content in data.values():
        content.pop("amendments", None)
    return data


def open_actual_amendments(date, eu_document_code):
    return get_all_votes_for_day(date)[eu_document_code]["amendments"]


def test_dump_day():
    clear_database()

    assert not day_exists("2024-10-08")
    dump_day("2024-10-08", True, False)
    assert day_exists("2024-10-08")
    assert open_actual("2024-10-08") == open_expected("2024-10-08")

    assert not day_exists("2024-09-19")
    dump_day("2024-09-19", True, False)
    assert day_exists("2024-09-19")
    assert open_actual("2024-09-19") == open_expected("2024-09-19")

    assert not day_exists("2022-06-23")
    dump_day("2022-06-23", True, False)
    assert day_exists("2022-06-23")
    assert open_actual("2022-06-23") == open_expected("2022-06-23")

    # If nothing happened on this date, the function should do nothing
    dump_day("2022-08-07", True, False)
    assert not day_exists("2022-08-07")

    # If the database registered the date as an empty day ...
    set_nothing_happened_for("2025-01-23")

    # ... the date should be skipped if overwrite_empty_days is False
    dump_day("2025-01-23", True, False)
    assert not day_exists("2025-01-23")
    assert nothing_happened_on("2025-01-23")

    # The date should be dumped if overwrite_empty_days is True, and the date should be removed from
    # empty days
    assert nothing_happened_on("2025-01-23")
    dump_day("2025-01-23", True, True)
    assert day_exists("2025-01-23")
    assert not nothing_happened_on("2025-01-23")


def test_amendments():
    clear_database()

    # Since 2024, the result of every vote is known, and the members votes for the roll-call votes
    dump_day("2024-10-10", True, False)
    amendments = open_actual_amendments("2024-10-10", "RC-B10-0101/2024/REV1")
    final_vote = [amendment for amendment in amendments if amendment["id"] == "169857"][0]
    assert final_vote["result"] == "ADOPTED"
    assert final_vote["global_votes"] == {"+": 540, "-": 23, "0": 47}
    assert final_vote["votes"] != {}
    amendment = [amendment for amendment in amendments if amendment["id"] == "169856"][0]
    assert amendment["amendment"] == "1"
    assert amendment["author"] == "The Left"
    assert amendment["result"] == "REJECTED"
    assert amendment["was_roll_call_voted"]
    # The document of the amendment on europarl is stored, the website doesn't have to ask it
    other = [vote for vote in open_actual_amendments("2024-10-10", "RC-B10-0095/2024") if vote["id"] == "169828"][0]
    assert other["amendment_url"].endswith("/RC-10-2024-0095-AM-003-004_fr.pdf")
    assert final_vote["amendment_url"] is None
    assert any(not amendment["was_roll_call_voted"] and amendment["votes"] == {} for amendment in amendments)

    # Before, only the roll-call votes are known
    dump_day("2022-06-23", True, False)
    amendments = open_actual_amendments("2022-06-23", "C9-0185/2022")
    assert [amendment["label"] for amendment in amendments] == [
        "C9-0185/2022 - Article 1, § 1, point 1 - Am 1",
        "C9-0185/2022 - Article 1, § 1, point 1 - Am 2",
        "C9-0185/2022 - Proposition de la Commission",
    ]
    assert all(amendment["votes"] != {} and amendment["result"] is None for amendment in amendments)
