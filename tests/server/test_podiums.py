from server.podiums import search_podiums, group_statistics, group_podiums


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


def test_group_statistics_and_podiums():
    def stats(group, voted, absent, corrections=0):
        return {"group": group, "voted": voted, "absent": absent, "corrections": corrections}

    members = [stats("France / PPE :", 90, 10, 2), stats("France / PPE :", 70, 30),
               stats("France / NI :", 75, 25, 1)]
    groups = {group["group"]: group for group in group_statistics(members)}

    ppe = groups["France / PPE :"]
    assert ppe["members_count"] == 2
    # Over all the votes of the group, not the average of the rates
    assert ppe["absent_rate"] == 40 / 200
    assert ppe["absent_average"] == 20
    assert ppe["corrections_average"] == 1

    podiums = group_podiums(list(groups.values()))
    assert [entry["member"]["group"] for entry in podiums["absent_rate"]["entries"]] == ["France / NI :", "France / PPE :"]
    # Same average of corrections: they share the first place
    assert [entry["rank"] for entry in podiums["corrections"]["entries"]] == [1, 1]


def test_group_statistics_renamed_group():
    members = [{"group": "France / GUE/NGL :", "voted": 9, "absent": 1, "corrections": 0},
               {"group": "France / The Left :", "voted": 8, "absent": 2, "corrections": 0}]
    groups = group_statistics(members)
    assert [(group["group"], group["members_count"]) for group in groups] == [("France / The Left :", 2)]
