from server.podiums import search_podiums


def member(identifier):
    return {"name": identifier, "id": identifier, "full_name": f"Député {identifier}"}


def document(date, voted, absent, corrections=()):
    return {"date": date, "global": {"was_roll_call_voted": True}, "votes": {"+": {"France / PPE :": [member(i) for i in voted]}},
            "absent": {"France / PPE :": [member(i) for i in absent]},
            "corrections": [{**member(i), "voted": "+", "intended": "-"} for i in corrections]}


def test_search_podiums():
    data = {
        "A": document("2025-01-01", voted=["a", "b"], absent=["c", "d", "e", "f"], corrections=["a"]),
        "B": document("2025-01-02", voted=["a", "c", "d", "e", "f"], absent=["b"]),
    }
    podiums = search_podiums(data)

    # b, c, d, e and f missed 1 vote out of 2: they share the first place, 2 of them are not on the podium
    rate = podiums["absent_rate"]
    assert [entry["rank"] for entry in rate["entries"]] == [1, 1, 1]
    assert rate["ex_aequo"] == 2
    # a never missed a vote, so it's not on the podium
    assert all(entry["member"]["id"] != "a" for entry in rate["entries"])

    corrections = podiums["corrections"]
    assert [(entry["rank"], entry["member"]["id"]) for entry in corrections["entries"]] == [(1, "a")]
    assert corrections["ex_aequo"] == 0


def test_search_podiums_ignore_documents_not_voted_by_roll_call():
    # The final vote was not a roll-call vote: "votes" and "absent" come from a vote on an amendment
    not_roll_call = {**document("2025-01-01", voted=["a"], absent=["b"]), "global": {"was_roll_call_voted": False}}
    assert search_podiums({"A": not_roll_call}) is None


def test_search_podiums_without_absents():
    # Database filled before the absents were stored
    assert search_podiums({"A": {"date": "2025-01-01", "votes": {}}}) is None
