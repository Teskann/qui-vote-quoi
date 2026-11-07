from server.generate_results import generate_document_page
from utils.date_management import votes_roll_call_source_url

RCV_URL = "https://www.europarl.europa.eu/doceo/document/PV-10-2026-10-22-RCV_FR.html"


def test_votes_roll_call_source_url():
    assert votes_roll_call_source_url("2026-10-22", "199497", "993352") == RCV_URL + "#199497#993352"
    # Before 2024, the XML doesn't give the item of the agenda: the page is opened at the top
    assert votes_roll_call_source_url("2026-10-22", "199497", None) == RCV_URL
    assert votes_roll_call_source_url("2026-10-22") == RCV_URL


def test_document_page_links_to_each_vote():
    vote = {"id": "199497", "dlv_id": "993352", "label": "§ 1", "was_roll_call_voted": True, "votes": {},
            "global_votes": None}
    old_vote = {**vote, "id": "199498", "dlv_id": None}
    show_of_hands = {**vote, "id": "199499", "was_roll_call_voted": False}
    content = {"votes": {}, "date": "2026-10-22", "votes_source_url": RCV_URL + "#199500#993352",
               "details": {"title": "Résolution", "source_url": ""},
               "global": {"was_roll_call_voted": True, "was_adopted": True},
               "amendments": [vote, old_vote, show_of_hands]}
    page = generate_document_page("2026-10-22", "RC-B10-0476/2026", content)
    assert page.count("Source du vote ↗") == 1
    assert f'href="{RCV_URL}#199497#993352"' in page
    # The source of the document opens its final vote
    assert f'href="{RCV_URL}#199500#993352"' in page
