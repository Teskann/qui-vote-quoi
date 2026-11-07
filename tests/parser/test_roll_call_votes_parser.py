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
    names = [member["name"] for member in votes["+"]["France / PfE :"]]
    assert "Bardella" in names
    # The members are described with their identifier, used for the photo and the link to their page
    bardella = votes["+"]["France / PfE :"][names.index("Bardella")]
    assert bardella == {"name": "Bardella", "id": "131580", "full_name": "Jordan Bardella"}
    # Only French members are kept
    assert sum(len(members) for members in votes["+"].values()) == 75



def test_parse_all_votes_before_2019():
    # Before 2019, the members are identified by their name, as the documents don't give their PersId
    votes = parse_all_votes(get_roll_call_votes_xml_at_date("2015-03-11"), "2015-03-11")
    votes = votes["A8-0014/2015"]["votes"]
    members = [member for groups in votes.values() for group in groups.values() for member in group]
    names = [member["name"] for member in members]
    assert len(names) == 72
    assert "Le Pen Marine" in names
    # The identifier is found from the name
    assert members[names.index("Le Pen Marine")]["id"] == "28210"
    assert all(member["id"] is not None for member in members)
    assert "France / ALDE :" in votes["+"]
    # Homonyms of other countries are not selected
    assert all(name not in names for name in ["Martin David", "Martin Hans-Peter"])


def test_absent_and_corrections():
    # Michèle Rivasi died on 2023-11-29 and was replaced by François Thiollet on 2023-11-30
    documents = parse_all_votes(get_roll_call_votes_xml_at_date("2023-12-12"), "2023-12-12")
    for document in documents.values():
        voters = [member for groups in document["votes"].values() for group in groups.values() for member in group]
        absent = [member for group in document["absent"].values() for member in group]
        # Every French member in office either voted or is absent: 79 seats between 2020 and 2024
        assert len(voters) + len(absent) == 79
        names = {member["full_name"] for member in voters + absent}
        assert "Michèle Rivasi" not in names
        assert "François Thiollet" in names
        for correction in document["corrections"]:
            assert correction["intended"] in ("+", "-", "0")
            assert correction["voted"] in ("+", "-", "0", None)
    assert any(document["corrections"] for document in documents.values())


def test_votes_without_identifier():
    # From mid-2017 to 2019, the XML doesn't identify the votes: they are identified by their number in the day, so
    # that they are counted in the statistics of the members
    votes = parse_all_votes(get_roll_call_votes_xml_at_date("2017-06-01"), "2017-06-01")
    identifiers = [vote["id"] for content in votes.values() for vote in content["amendments"]]
    assert identifiers and all(identifier and identifier.startswith("2017-06-01-") for identifier in identifiers)
    assert "2017-06-01-1" in identifiers


def test_members_sharing_a_name():
    # Marine Le Pen left in June 2017: "Le Pen" is then Jean-Marie Le Pen
    votes = parse_all_votes(get_roll_call_votes_xml_at_date("2018-03-14"), "2018-03-14")
    members = [member for content in votes.values() for vote in content["amendments"]
               for groups in list(vote["votes"].values()) + [vote["absent"]] for group in groups.values() for member in group]
    assert {member["id"] for member in members if member["name"] == "Le Pen"} == {"1023"}
    assert all(member["id"] for member in members)
    # When both were in office, the document writes "Le Pen Marine" for one and "Le Pen" for the other
    votes = parse_all_votes(get_roll_call_votes_xml_at_date("2017-05-16"), "2017-05-16")
    members = [member for content in votes.values() for vote in content["amendments"]
               for groups in vote["votes"].values() for group in groups.values() for member in group]
    assert {member["id"] for member in members if member["name"] == "Le Pen"} == {"1023"}
    assert all(vote["absent"] is not None for content in votes.values() for vote in content["amendments"])
