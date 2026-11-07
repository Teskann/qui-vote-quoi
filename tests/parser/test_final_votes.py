from lxml import etree

import parser.votes_page_parser as votes_page_parser
from parser import merger


def roll_call_vote(identifier, counts, label=""):
    return {"id": identifier, "label": label, "global_votes": dict(zip("+-0", counts)),
            "votes": {"+": {"France / PPE :": [{"id": identifier}]}}, "absent": {}, "corrections": []}


def result(counts):
    return {"was_roll_call_voted": True, "was_adopted": True,
            "global_votes": dict(zip("+-0", counts)) if counts else {"+": "Données indisponibles", "-": "x", "0": "x"}}


def final_vote(votes, counts):
    return getattr(merger, "__final_vote")({"amendments": votes}, result(counts))


def test_final_vote_is_the_one_with_the_totals_of_the_result():
    resolution = roll_call_vote("2", (478, 107, 80), "Résolution")
    amendment = roll_call_vote("3", (184, 483, 20), "Am 20")
    # The last vote on the document is an amendment: the final vote is the one with the totals of the result
    assert final_vote([resolution, amendment], (478, 107, 80)) is resolution
    # The two reports differ by a few votes before 2024
    assert final_vote([amendment, roll_call_vote("4", (629, 58, 4))], (629, 58, 6))["id"] == "4"
    # The final vote took place another day: no vote of the day is the final vote
    assert final_vote([amendment], (478, 107, 80)) is None
    # Totals unknown: the last vote, as before
    assert final_vote([resolution, amendment], None) is amendment


def test_merged_document_keeps_the_final_vote(monkeypatch):
    class Document:  # The details of the document are not asked to europarl
        def __init__(self, code):
            pass

        def to_dict(self):
            return {"title": "Rapport"}
    monkeypatch.setattr(merger, "Document", Document)
    resolution = roll_call_vote("2", (478, 107, 80))
    amendment = roll_call_vote("3", (184, 483, 20))
    merged = merger.merge_data({"A9-0026/2020": {"amendments": [resolution, amendment]}},
                               {"A9-0026/2020": result((478, 107, 80))}, "2020-06-19")
    document = merged["A9-0026/2020"]
    assert document["final_vote_id"] == "2" and document["votes"] == resolution["votes"]
    assert document["votes_source_url"].endswith("PV-9-2020-06-19-RCV_FR.html")


VOTE = """<vote>
  <documents>
    <document documentNumber="B10-0060/2026" documentType="PR" documentOrder="0"/>
    <document documentNumber="B10-0061/2026" documentType="PR" documentOrder="1"/>
  </documents>
  <votings>
    <voting type="TITLE_BLOCK" votingId="1"><title>Proposition de résolution B10-0060/2026 (députés)</title></voting>
    <voting type="AMENDMENT" votingId="2" result="ADOPTED" resultType="ROLL_CALL" numberFavor="334" numberAgainst="324"
            numberAbstention="11"><label>B10-0060/2026 - Proposition de résolution</label></voting>
    <voting type="TITLE_BLOCK" votingId="3"><title>Proposition de résolution B10-0061/2026 (députés)</title></voting>
    <voting type="AMENDMENT" votingId="4" result="REJECTED" resultType="ROLL_CALL" numberFavor="225" numberAgainst="402"
            numberAbstention="13"><label>B10-0061/2026 - Proposition de résolution</label></voting>
    <voting type="TITLE_BLOCK" votingId="5"><title>Autres propositions de résolution</title></voting>
    <voting type="AMENDMENT" votingId="6" result="REJECTED" resultType="RAISE_HAND"/>
  </votings>
</vote>"""


def test_competing_motions_have_their_own_result():
    xml = etree.fromstring(f"<file>{VOTE}</file>")
    results = getattr(votes_page_parser, "__parse_structured_format")(xml)
    assert results["B10-0060/2026"]["was_adopted"] and results["B10-0060/2026"]["global_votes"] == {"+": 334, "-": 324, "0": 11}
    assert not results["B10-0061/2026"]["was_adopted"]
    amendments = getattr(votes_page_parser, "__parse_structured_amendments")(xml)
    assert [vote["id"] for vote in amendments["B10-0060/2026"]] == ["2"]
    # The block which gives no document is left out
    assert [vote["id"] for vote in amendments["B10-0061/2026"]] == ["4"]
