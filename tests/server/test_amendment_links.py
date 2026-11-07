import server.generate_results as generate_results
from server.generate_results import amendment_links, generate_document_page

PDF = "https://data.europarl.europa.eu/A-10-2025-0018-AM-001-161_fr.pdf"
AMENDMENT = {"id": "1", "amendment": "12", "label": "Am 12", "was_roll_call_voted": False, "votes": {},
             "global_votes": None}
PARAGRAPH = {**AMENDMENT, "id": "2", "amendment": None, "label": "§ 1"}
CONTENT = {"votes": {}, "date": "2025-01-23", "details": {"title": "Rapport", "source_url": ""},
           "global": {"was_roll_call_voted": True, "was_adopted": True}, "amendments": [AMENDMENT, PARAGRAPH]}


def test_amendment_links(monkeypatch):
    monkeypatch.setattr(generate_results, "get_amendments_documents", lambda code: [(1, 161, PDF)])
    # The votes which are not on an amendment have no link
    assert amendment_links("A10-0018/2025", [AMENDMENT, PARAGRAPH]) == {"1": PDF}


def test_amendment_links_without_amendments(monkeypatch):
    def fail(code):
        raise AssertionError("europarl should not be asked")
    monkeypatch.setattr(generate_results, "get_amendments_documents", fail)
    assert amendment_links("A10-0018/2025", [PARAGRAPH]) == {}


def test_document_page_does_not_ask_europarl(monkeypatch):
    def fail(code):
        raise AssertionError("europarl should not be asked")
    monkeypatch.setattr(generate_results, "get_amendments_documents", fail)
    page = generate_document_page("2025-01-23", "A10-0018/2025", CONTENT)
    # The link is loaded by the page
    assert 'data-vote-id="1"' in page
    assert 'data-vote-id="2"' not in page
    assert '"/texte/amendements?"' in page
