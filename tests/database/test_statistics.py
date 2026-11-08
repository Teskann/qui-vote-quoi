from database import storage
from database.database import get_database_path, set_database_path
from database.database_reader import search_group_pairs_in_time_range
from database.database_writer import fill_statistics
from database.members_index import get_member, get_member_corrections
from database.statistics import EUROPEAN_PARLIAMENT, TOTAL_FRANCE
from server.filters import correlations


def member(identifier, name):
    return {"name": name, "id": identifier, "full_name": f"Prénom {name}"}


def document(votes, was_roll_call_voted=True, was_adopted=True):
    return {"votes": votes, "absent": {}, "corrections": [], "details": {"title": "Titre"},
            "global": {"was_roll_call_voted": was_roll_call_voted, "was_adopted": was_adopted}}


def in_database(tmp_path, function):
    previous_path = get_database_path()
    set_database_path(str(tmp_path))
    try:
        return function()
    finally:
        set_database_path(previous_path)


def test_search_group_pairs(tmp_path):
    a, b, c, d = (member(str(i), name) for i, name in enumerate("ABCD"))
    day = {
        # PPE and S&D for, Renew against: France for (2 against 1)
        "A10-0001/2025": document({"+": {"France / PPE :": [a], "France / S&D :": [b]}, "-": {"France / Renew :": [c]}}),
        # PPE for, S&D as many for as against: S&D is not compared
        "A10-0002/2025": document({"+": {"France / PPE :": [a], "France / S&D :": [b]}, "-": {"France / S&D :": [d]}},
                                  was_adopted=False),
        # Not a roll-call vote: the group is listed, but not compared
        "A10-0003/2025": document({"+": {"France / NI :": [d]}}, was_roll_call_voted=False),
    }

    def search():
        storage.write_day("2025-03-12", day)
        return search_group_pairs_in_time_range("2025-01-01", "2025-12-31", "")
    groups, pairs = in_database(tmp_path, search)

    assert groups == {"France / PPE :", "France / S&D :", "France / Renew :", "France / NI :",
                      EUROPEAN_PARLIAMENT, TOTAL_FRANCE}
    assert pairs[("France / PPE :", "France / S&D :")] == pairs[("France / S&D :", "France / PPE :")] == (1, 1)
    assert pairs[("France / PPE :", "France / Renew :")] == (0, 1)
    # The parliament adopted the first text, rejected the second one
    assert pairs[("France / PPE :", EUROPEAN_PARLIAMENT)] == (1, 2)
    assert not any("France / NI :" in pair for pair in pairs)

    table = correlations(groups, pairs)
    values = {frozenset((group, other)): value for group, row in table.items() for other, value in row.items()
              if value is not None}
    assert values[frozenset(("France / PPE :", EUROPEAN_PARLIAMENT))] == 1 / 2
    assert frozenset(("France / PPE :", "France / NI :")) not in values


def test_fill_statistics_of_days_written_before(tmp_path):
    a, b = member("1", "A"), member("2", "B")
    vote = {"id": "v1", "was_roll_call_voted": True, "votes": {"+": {"France / PPE :": [a, b]}}, "absent": {},
            "corrections": [{**b, "voted": "+", "intended": "-"}]}
    day = {"A10-0001/2025": {**document(vote["votes"]), "amendments": [vote]}}

    def statistics():
        return get_member("2"), get_member_corrections("2")

    def fill():
        storage.write_day("2025-03-12", day)
        expected = statistics()
        # A database written before the statistics were stored with each day
        with storage.connect() as connection:
            for table in ("statistics_days", "member_days", "group_cohesion", "group_proximity", "corrections",
                          "document_members", "document_groups"):
                connection.execute(f"DELETE FROM {table}")
        missing = storage.days_without_statistics()
        fill_statistics()
        return expected, missing, statistics(), storage.days_without_statistics()
    expected, missing, filled, missing_after = in_database(tmp_path, fill)

    assert missing == ["2025-03-12"] and missing_after == []
    assert filled == expected
    assert expected[0]["corrections"] == 1
