import json
import os

from database.database import get_path, exists, get_database_path
from database.database_writer import dump_day_to_json
from parser.empty_days_management import set_nothing_happened_for, nothing_happened_on
from tests.setup_database import clear_database

EXPECTED_DESTINATION = os.path.join(get_database_path(), "..", "expected")


def expected_path(date):
    return os.path.join(EXPECTED_DESTINATION, date + ".json")


def actual_path(date):
    return get_path(date + ".json")


def open_expected(date):
    with open(expected_path(date), "r", encoding="utf-8") as f:
        return json.load(f)


def open_actual(date):
    with open(actual_path(date), "r", encoding="utf-8") as f:
        return json.load(f)


def test_dump_day_to_json():
    clear_database()

    assert not exists("2024-10-08.json")
    dump_day_to_json("2024-10-08", True, False)
    assert exists("2024-10-08.json")
    assert open_actual("2024-10-08") == open_expected("2024-10-08")

    assert not exists("2024-09-19.json")
    dump_day_to_json("2024-09-19", True, False)
    assert exists("2024-09-19.json")
    assert open_actual("2024-09-19") == open_expected("2024-09-19")

    assert not exists("2022-06-23.json")
    dump_day_to_json("2022-06-23", True, False)
    assert exists("2022-06-23.json")
    assert open_actual("2022-06-23") == open_expected("2022-06-23")

    # If nothing happened on this date, the function should do nothing
    dump_day_to_json("2022-08-07", True, False)
    assert not exists("2022-08-07.json")

    # If the database registered the date as an empty day ...
    set_nothing_happened_for("2025-01-23")

    # ... the date should be skipped if overwrite_empty_days is False
    dump_day_to_json("2025-01-23", True, False)
    assert not exists("2025-01-23.json")
    assert nothing_happened_on("2025-01-23")

    # The date should be dumped if overwrite_empty_days is True, and the date should be removed from
    # empty days
    assert nothing_happened_on("2025-01-23")
    dump_day_to_json("2025-01-23", True, True)
    assert exists("2025-01-23.json")
    assert not nothing_happened_on("2025-01-23")