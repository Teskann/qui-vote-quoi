from database import database_writer
from parser import open_data
from server.generate_results import generate_document_page

PDF = "https://data.europarl.europa.eu/A-10-2025-0018-AM-001-161_fr.pdf"
AMENDMENT = {"id": "1", "amendment": "12", "label": "Am 12", "was_roll_call_voted": False, "votes": {},
             "global_votes": None}
PARAGRAPH = {**AMENDMENT, "id": "2", "amendment": None, "label": "§ 1"}
CONTENT = {"votes": {}, "date": "2025-01-23", "details": {"title": "Rapport", "source_url": ""},
           "global": {"was_roll_call_voted": True, "was_adopted": True}}


def fail(code):
    raise AssertionError("europarl should not be asked")


def test_amendment_links_stored_when_filling(monkeypatch):
    monkeypatch.setattr(open_data, "get_amendments_documents", lambda code: [(1, 161, PDF)])
    day = {"A10-0018/2025": {**CONTENT, "amendments": [dict(AMENDMENT), dict(PARAGRAPH)]}}
    getattr(database_writer, "__add_amendment_links")(day)
    # The votes which are not on an amendment have no link
    assert [vote["amendment_url"] for vote in day["A10-0018/2025"]["amendments"]] == [PDF, None]


def test_europarl_not_asked_without_amendments(monkeypatch):
    monkeypatch.setattr(open_data, "get_amendments_documents", fail)
    day = {"A10-0018/2025": {**CONTENT, "amendments": [dict(PARAGRAPH)]}}
    getattr(database_writer, "__add_amendment_links")(day)
    assert day["A10-0018/2025"]["amendments"][0]["amendment_url"] is None


def test_document_page_does_not_ask_europarl(monkeypatch):
    monkeypatch.setattr(open_data, "get_amendments_documents", fail)
    content = {**CONTENT, "amendments": [{**AMENDMENT, "amendment_url": PDF}, {**PARAGRAPH, "amendment_url": None}]}
    page = generate_document_page("2025-01-23", "A10-0018/2025", content)
    # The stored link is in the page, there's nothing left to load
    assert page.count("Lire l'amendement") == 1
    assert f'href="{PDF}"' in page and "Lire l'amendement 12 sur europarl" in page
    assert "/texte/amendements" not in page
    # A database filled before the links were stored: no link
    old = {**CONTENT, "amendments": [AMENDMENT]}
    assert "Lire l'amendement" not in generate_document_page("2025-01-23", "A10-0018/2025", old)
