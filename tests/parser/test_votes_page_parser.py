import json
import os.path
from time import sleep

from parser.votes_page_parser import get_vote_results_for_date


HERE = os.path.abspath(os.path.dirname(__file__))


def test_get_vote_results_for_date():
    with open(os.path.join(HERE, "..", "expected", "votes_page_parser.json"), "r", encoding="utf-8") as f:
        expected = json.load(f)
    for date in expected:
        assert get_vote_results_for_date(date) == expected[date]
        sleep(1)  # Should help preventing being blocked

