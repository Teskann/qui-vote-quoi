import time

from database.database_reader import search_eu_document, search_in_time_range
from database.database_writer import dump_day
from tests.setup_database import clear_database


def test_find_eu_documents_from_keyword():
    dump_day("2024-09-19")
    dump_day("2022-06-23")

    # 1 example in 2024
    # Keyword "Ukraine"
    eu_documents = search_eu_document("ukraine", "2024-09-19")
    assert len(eu_documents) == 1
    assert "RC-B10-0028/2024" in eu_documents

    # keyword venezuela
    eu_documents = search_eu_document("venezuela", "2024-09-19")
    assert len(eu_documents) == 1
    assert "RC-B10-0023/2024" in eu_documents

    # Keyword "unknown"
    eu_documents = search_eu_document("unknown", "2024-09-19")
    assert len(eu_documents) == 0

    # 1 example in 2022 https://www.europarl.europa.eu/doceo/document/PV-9-2022-06-23-RCV_FR.html
    # Keyword "Ukraine"

    eu_documents = search_eu_document("UkRaInE", "2022-06-23")

    assert len(eu_documents) == 2
    assert "RC-B9-0331/2022" in eu_documents
    assert "A9-0181/2022" in eu_documents

    # Keyword "covid"
    eu_documents = search_eu_document("covid", "2022-06-23")
    assert len(eu_documents) == 2

    assert "A9-0138/2022" in eu_documents
    assert "A9-0137/2022" in eu_documents

def test_search_in_time_range():
    clear_database()
    dump_day("2024-09-19")
    dump_day("2022-06-23")

    days = list(search_in_time_range("2022-01-01", "2024-12-31", "ukraine"))
    assert [set(day) for day in days] == [{"RC-B9-0331/2022", "A9-0181/2022"}, {"RC-B10-0028/2024"}]
    # The amendments are not needed to display the results
    assert all("amendments" not in content for day in days for content in day.values())

    # The range is inclusive
    assert len(list(search_in_time_range("2022-06-23", "2022-06-23", ""))) == 1
    assert list(search_in_time_range("2023-01-01", "2023-12-31", "")) == []


def test_search_with_many_keywords():
    clear_database()
    dump_day("2024-09-19")
    # The keywords must appear in this order, the case and the accents are ignored
    assert set(search_eu_document("situation VÉNÉZUELA", "2024-09-19")) == {"RC-B10-0023/2024"}
    # Many keywords don't block the server (a regular expression took several seconds per document)
    start = time.perf_counter()
    assert search_eu_document("a " * 50 + "zzz", "2024-09-19") == {}
    assert time.perf_counter() - start < 1
