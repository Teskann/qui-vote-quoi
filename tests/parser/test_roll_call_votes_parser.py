from parser.empty_days_management import nothing_happened_on
from parser.roll_call_votes_parser import get_roll_call_votes_xml_at_date, parse_all_votes, find_votes_in_previous_days


def test_get_roll_call_votes_xml_at_date():
    # On an empty date => Should return None
    assert not nothing_happened_on("2022-06-21")
    assert get_roll_call_votes_xml_at_date("2022-06-21") is None
    assert nothing_happened_on("2022-06-21")

    # Non empty date => should return the XML document
    assert get_roll_call_votes_xml_at_date("2022-06-23") is not None
    assert get_roll_call_votes_xml_at_date("2024-09-19") is not None


def test_parse_all_votes():
    votes = parse_all_votes(get_roll_call_votes_xml_at_date("2024-10-08"), "2024-10-08")
    assert list(votes.keys()) == ["A10-0002/2024"]
    votes = votes["A10-0002/2024"]["votes"]
    assert set(votes.keys()) == {"+"}
    assert "France / PfE :" in votes["+"]
    assert "Bardella" in votes["+"]["France / PfE :"]
    # Only French members are kept
    assert sum(len(names) for names in votes["+"].values()) == 75


def test_find_votes_in_previous_days():
    # During the remote voting period, the votes results of 2021-07-07 refer to roll-call votes of 2021-07-06
    found = find_votes_in_previous_days({"A9-0210/2021", "UNKNOWN"}, "2021-07-07")
    assert list(found.keys()) == ["A9-0210/2021"]
    assert found["A9-0210/2021"]["date"] == "2021-07-06"
    assert found["A9-0210/2021"]["votes"] != {}
