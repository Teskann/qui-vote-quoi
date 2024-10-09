import json
import os

from database.database import get_path, exists, get_database_path
from database.database_writer import dump_day_to_json
from tests.setup_database import clear_database

EXPECTED_DESTINATION = os.path.join(get_database_path(), "..", "expected")


def expected_path(date):
    return os.path.join(EXPECTED_DESTINATION, date + ".json")


def actual_path(date):
    return get_path(date + ".json")


def open_expected(date):
    with open(expected_path(date), "r") as f:
        return json.load(f)


def open_actual(date):
    with open(actual_path(date), "r") as f:
        return json.load(f)


def test_dump_day_to_json():
    clear_database()

    assert not exists("2024-10-08.json")
    dump_day_to_json("2024-10-08", True)
    assert exists("2024-10-08.json")
    assert open_actual("2024-10-08") == open_expected("2024-10-08")

    assert not exists("2024-09-19.json")
    dump_day_to_json("2024-09-19", True)
    assert exists("2024-09-19.json")
    assert open_actual("2024-09-19") == open_expected("2024-09-19")

    assert not exists("2022-06-23.json")
    dump_day_to_json("2022-06-23", True)
    assert exists("2022-06-23.json")
    assert open_actual("2022-06-23") == open_expected("2022-06-23")

    # If nothing happened on this date, the function should do nothing
    dump_day_to_json("2022-08-07", True)
    assert not exists("2022-08-07.json")