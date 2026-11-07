from server.filters import vote_results_per_group


def member(name):
    return {"name": name}


def test_vote_results_per_group_without_abstentions():
    data = {"A": {"global": {"was_roll_call_voted": True, "was_adopted": True},
                  "votes": {"+": {"France / PPE :": [member("a")], "France / Renew :": [member("b"), member("c")]},
                            "-": {"France / Renew :": [member("d")], "France / S&D :": [member("e")]},
                            "0": {"France / PPE :": [member("f"), member("g")], "France / ECR :": [member("h")]}}}}
    results = vote_results_per_group(data)["A"]
    # The abstentions don't count
    assert results["France / PPE :"] is True
    assert results["France / S&D :"] is False
    assert results["France / ECR :"] is None
    # France: 3 for, 2 against (the members are counted, not the groups)
    assert results["Total France :"] is True


def test_is_final_vote():
    from server.filters import is_final_vote
    final = {"id": "2", "was_roll_call_voted": True, "votes": {"+": {"France / PPE :": [member("a")]}}, "absent": {}}
    amendment = {"id": "1", "was_roll_call_voted": True, "votes": {"-": {"France / PPE :": [member("a")]}}, "absent": {}}
    document = {"global": {"was_roll_call_voted": True}, "votes": final["votes"], "absent": {},
                "amendments": [amendment, final]}
    assert is_final_vote(final, document)
    assert not is_final_vote(amendment, document)
    # The final vote was not a roll-call vote: none of the roll-call votes is the final vote
    assert not is_final_vote(final, {**document, "global": {"was_roll_call_voted": False}})


def test_group_slug_of_renamed_group():
    from server.filters import group_slug
    assert group_slug("France / GUE/NGL :") == group_slug("France / The Left :") == "the-left"
    assert group_slug("France / Verts/ALE :") == "verts-ale"
