import json
import os.path

from parser.votes_page_parser import get_vote_results_for_date


HERE = os.path.abspath(os.path.dirname(__file__))


def test_get_vote_results_for_date():
    print(json.dumps(get_vote_results_for_date("2023-11-22"), indent=2, ensure_ascii=False))
    with open(os.path.join(HERE, "..", "expected", "votes_page_parser.json"), "r") as f:
        expected = json.load(f)
    for date in expected:
        assert get_vote_results_for_date(date) == expected[date]

