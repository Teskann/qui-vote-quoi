from parser.empty_days_management import nothing_happened_on
from parser.roll_call_votes_parser import get_roll_call_votes_xml_at_date, parse_all_votes


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



def test_parse_all_votes_before_2019():
    # Before 2019, the members are identified by their name, as the documents don't give their PersId
    votes = parse_all_votes(get_roll_call_votes_xml_at_date("2015-03-11"), "2015-03-11")
    votes = votes["A8-0014/2015"]["votes"]
    names = [name for groups in votes.values() for members in groups.values() for name in members]
    assert len(names) == 72
    assert "Le Pen Marine" in names
    assert "France / ALDE :" in votes["+"]
    # Homonyms of other countries are not selected
    assert all(name not in names for name in ["Martin David", "Martin Hans-Peter"])
