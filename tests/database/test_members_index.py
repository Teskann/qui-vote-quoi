from database.database import get_database_path, set_database_path
from database.members_index import get_member, get_groups_votes, get_all_members, get_member_corrections, FINAL, AMENDMENTS
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


def test_get_groups_votes(tmp_path):
    a, b, c, d, e = (member(str(i), name) for i, name in enumerate("ABCDE"))
    # PPE: 2 members for, 1 against. S&D: 1 for. Verts: 1 for, 1 against (no majority)
    vote = roll_call_vote("v1", {"+": {"France / PPE :": [a, b], "France / S&D :": [c], "France / Verts/ALE :": [d]},
                                 "-": {"France / PPE :": [e], "France / Verts/ALE :": [member("6", "F")]}}, {})
    previous_path = get_database_path()
    set_database_path(str(tmp_path))
    try:
        write_day("2025-03-12", {"A10-0001/2025": {"votes": {}, "absent": {}, "global": {}, "amendments": [vote]}})
        votes = get_groups_votes()
    finally:
        set_database_path(previous_path)

    # The S&D has a single member: no cohesion
    assert votes["cohesion"]["France / PPE :"] == [1, 2 / 3]
    assert votes["cohesion"]["France / Verts/ALE :"] == [1, 1 / 2]
    assert "France / S&D :" not in votes["cohesion"]
    # Same majority for PPE and S&D, Verts have no majority
    assert votes["proximity"][("France / PPE :", "France / S&D :")] == [1, 1]
    assert ("France / PPE :", "France / Verts/ALE :") not in votes["proximity"]


def test_get_all_members_final_votes_or_amendments(tmp_path):
    a, b = member("1", "A"), member("2", "B")
    amendment = roll_call_vote("v1", {"+": {"France / PPE :": [a]}}, {"France / S&D :": [b]})
    final = roll_call_vote("v2", {"-": {"France / PPE :": [a], "France / S&D :": [b]}}, {})
    day = {
        # The final vote is the one whose votes are those of the document
        "A10-0001/2025": {"votes": final["votes"], "absent": final["absent"], "corrections": [],
                          "global": {"was_roll_call_voted": True}, "amendments": [amendment, final]},
    }
    previous_path = get_database_path()
    set_database_path(str(tmp_path))
    try:
        write_day("2025-03-12", day)
        final_only = {m["id"]: m for m in get_all_members(kinds=(FINAL,))}
        amendments_only = {m["id"]: m for m in get_all_members(kinds=(AMENDMENTS,))}
    finally:
        set_database_path(previous_path)

    assert (final_only["2"]["voted"], final_only["2"]["absent"]) == (1, 0)
    assert (amendments_only["2"]["voted"], amendments_only["2"]["absent"]) == (0, 1)


def test_get_groups_votes_without_abstentions(tmp_path):
    a, b, c, d = (member(str(i), name) for i, name in enumerate("ABCD"))
    # The abstentions don't count: the PPE voted for (1 for, 2 abstentions), the S&D only abstained
    vote = roll_call_vote("v1", {"+": {"France / PPE :": [a], "France / Renew :": [d]},
                                 "0": {"France / PPE :": [b, member("5", "E")], "France / S&D :": [c]}}, {})
    previous_path = get_database_path()
    set_database_path(str(tmp_path))
    try:
        write_day("2025-03-12", {"A10-0001/2025": {"votes": {}, "absent": {}, "global": {}, "amendments": [vote]}})
        votes = get_groups_votes()
    finally:
        set_database_path(previous_path)

    assert votes["proximity"][("France / PPE :", "France / Renew :")] == [1, 1]
    assert ("France / PPE :", "France / S&D :") not in votes["proximity"]
    # A single member of the PPE voted for or against: no cohesion
    assert "France / PPE :" not in votes["cohesion"]


def test_get_member_corrections(tmp_path):
    a, b = member("1", "A"), member("2", "B")
    amendment = roll_call_vote("v1", {"+": {"France / PPE :": [a, b]}}, {}, [{**b, "voted": "+", "intended": "-"}])
    amendment["label"] = "Am 3"
    final = roll_call_vote("v2", {"-": {"France / PPE :": [a, b]}}, {})
    day = {"A10-0001/2025": {"votes": final["votes"], "absent": final["absent"], "corrections": [],
                             "details": {"title": "Titre"}, "global": {"was_roll_call_voted": True},
                             "amendments": [amendment, final]}}
    previous_path = get_database_path()
    set_database_path(str(tmp_path))
    try:
        write_day("2025-03-12", day)
        corrections = get_member_corrections("2")
        on_final_votes = get_member_corrections("2", kinds=(FINAL,))
    finally:
        set_database_path(previous_path)

    assert corrections == [{"date": "2025-03-12", "kind": AMENDMENTS, "vote_id": "v1", "eu_document_code": "A10-0001/2025",
                            "title": "Titre", "label": "Am 3", "voted": "+", "intended": "-"}]
    assert on_final_votes == []
