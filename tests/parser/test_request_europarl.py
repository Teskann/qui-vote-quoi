import pytest

from parser.empty_days_management import nothing_happened_on
from parser.request_europarl import get_roll_call_votes_html_at_date


def test_get_votes_html_at_date():
    # On an empty date => Should return None
    assert not nothing_happened_on("2022-06-21")
    assert get_roll_call_votes_html_at_date("2022-06-21") == None
    assert nothing_happened_on("2022-06-21")

    # Non empty date => should return the soup
    assert get_roll_call_votes_html_at_date("2022-06-23") is not None
    assert get_roll_call_votes_html_at_date("2024-09-19") is not None
