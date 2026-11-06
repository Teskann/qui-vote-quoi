from database.database import get_database_path, set_database_path
from database.members_index import get_member
from database.storage import write_day


def member(identifier, name):
    return {"name": name, "id": identifier, "full_name": f"Prénom {name}"}


def roll_call_vote(identifier, votes, absent, corrections=()):
    return {"id": identifier, "was_roll_call_voted": True, "votes": votes, "absent": absent,
            "corrections": list(corrections)}


def test_get_member(tmp_path):
    a, b = member("1", "A"), member("2", "B")
    vote_1 = roll_call_vote("v1", {"+": {"France / PPE :": [a]}}, {"France / S&D :": [b]})
    vote_2 = roll_call_vote("v2", {"-": {"France / PPE :": [a], "France / S&D :": [b]}}, {},
                            [{**b, "voted": "-", "intended": "+"}])
    day = {
        # The vote v2 concerns both documents: it's counted once
        "A10-0001/2025": {"votes": vote_2["votes"], "absent": vote_2["absent"], "corrections": [],
                          "details": {"title": "Titre 1"}, "global": {"was_adopted": False, "was_roll_call_voted": True},
                          "amendments": [vote_1, vote_2]},
        "A10-0002/2025": {"votes": vote_1["votes"], "absent": vote_1["absent"], "corrections": [],
                          "details": {"title": "Titre 2"}, "global": {"was_adopted": True, "was_roll_call_voted": True},
                          "amendments": [vote_2]},
        # Final vote not by roll-call: the document is not in the recent votes, but its roll-call votes are counted
        "A10-0003/2025": {"votes": vote_1["votes"], "absent": vote_1["absent"], "corrections": [],
                          "details": {"title": "Titre 3"}, "global": {"was_adopted": True, "was_roll_call_voted": False},
                          "amendments": [vote_1]},
    }
    previous_path = get_database_path()
    set_database_path(str(tmp_path))
    try:
        write_day("2025-03-12", day)
        b_stats = get_member("2")
        assert get_member("3") is None
    finally:
        set_database_path(previous_path)

    assert b_stats["full_name"] == "Prénom B"
    # A voted twice, B voted once and was absent once: B is the most absent, and the only one who corrected a vote
    assert b_stats["members_count"] == 2
    assert b_stats["ranks"] == {"absent_rate": 1, "absent": 1, "corrections": 1, "voted": 2}
    assert (b_stats["voted"], b_stats["absent"], b_stats["corrections"]) == (1, 1, 1)
    assert b_stats["months"] == {"2025-03": {"voted": 1, "absent": 1}}
    # Most recent first: the documents of a day are in the order of the file
    assert [(vote["eu_document_code"], vote["vote"]) for vote in b_stats["recent"]] == \
           [("A10-0002/2025", "absent"), ("A10-0001/2025", "-")]
