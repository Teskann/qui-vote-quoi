from database.database_reader import search_eu_document
from database.database_writer import dump_day_to_json
from tests.setup_database import clear_database


def test_find_eu_documents_from_keyword():
    dump_day_to_json("2024-09-19")
    dump_day_to_json("2022-06-23")

    # 1 example in 2024
    # Keyword "Ukraine"
    eu_documents = search_eu_document("ukraine", "2024-09-19")
    assert len(eu_documents) == 1
    assert "RC-B10-0028/2024" in eu_documents

    # keyword venezuela
    eu_documents = search_eu_document("venezuela", "2024-09-19")
    assert len(eu_documents) == 2
    assert "RC-B10-0023/2024" in eu_documents
    assert "B10-0023/2024" in eu_documents

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