"""
Storage of the votes in a SQLite database, in the database directory (see database.database).

Each voted document is a row of the "documents" table. The votes held on the document (amendments, paragraphs, ...)
are stored apart, in the "amendments" table: they make most of the volume of the database, and are not needed to
display the search results.

The database is in WAL mode, so that the website can read it while it's updated.
"""
import contextlib
import json
import sqlite3
import time
from typing import Iterator

from unidecode import unidecode

from database.database import get_path

DATABASE_FILE = "votes.sqlite"

# Seconds to wait when the database is locked by another writer (the database is filled by several threads)
BUSY_TIMEOUT = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS days (
    date TEXT PRIMARY KEY,
    -- Changes when the day is written again, to refresh what is computed from the day
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    date TEXT NOT NULL REFERENCES days(date) ON DELETE CASCADE,
    eu_document_code TEXT NOT NULL,
    -- Order of the documents in the day
    position INTEGER NOT NULL,
    -- Title, description and code, without accents. NULL if the details of the document are unknown.
    search_text TEXT,
    -- The document, without its amendments (JSON)
    content TEXT NOT NULL,
    PRIMARY KEY (date, eu_document_code)
);
CREATE TABLE IF NOT EXISTS amendments (
    date TEXT NOT NULL,
    eu_document_code TEXT NOT NULL,
    -- All the votes held on the document (JSON list)
    content TEXT NOT NULL,
    PRIMARY KEY (date, eu_document_code),
    FOREIGN KEY (date, eu_document_code) REFERENCES documents(date, eu_document_code) ON DELETE CASCADE
);
"""


@contextlib.contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """
    Connection to the database, created if needed. The changes are committed when the block exits without error.
    """
    connection = sqlite3.connect(get_path(DATABASE_FILE), timeout=BUSY_TIMEOUT)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
            connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA)
        with connection:
            yield connection
    finally:
        connection.close()


def search_text(eu_document_code: str, content: dict) -> str | None:
    """
    Text in which the keywords of a search are looked for
    """
    if "details" not in content:
        return None
    details = content["details"]
    return unidecode(" ".join([details.get("title", ""), details.get("description", ""), eu_document_code]))


def write_day(date: str, votes_per_document: dict):
    """
    Write the documents voted on a day, replacing what was stored for this day
    :param date: date as iso formatted string
    :param votes_per_document: {<eu_document_code>: <content>}, the content may have "amendments"
    """
    with connect() as connection:
        connection.execute("DELETE FROM days WHERE date = ?", (date,))
        connection.execute("INSERT INTO days (date, updated_at) VALUES (?, ?)", (date, time.time()))
        for position, (eu_document_code, content) in enumerate(votes_per_document.items()):
            content = dict(content)
            amendments = content.pop("amendments", None)
            connection.execute(
                "INSERT INTO documents (date, eu_document_code, position, search_text, content) VALUES (?, ?, ?, ?, ?)",
                (date, eu_document_code, position, search_text(eu_document_code, content),
                 json.dumps(content, ensure_ascii=False)))
            if amendments is not None:
                connection.execute("INSERT INTO amendments (date, eu_document_code, content) VALUES (?, ?, ?)",
                                   (date, eu_document_code, json.dumps(amendments, ensure_ascii=False)))


def day_exists(date: str) -> bool:
    with connect() as connection:
        return connection.execute("SELECT 1 FROM days WHERE date = ?", (date,)).fetchone() is not None


def days() -> list[tuple[str, float]]:
    """
    :return: [(<date>, <time of the last update>)] for all the days of the database, in chronological order
    """
    with connect() as connection:
        return connection.execute("SELECT date, updated_at FROM days ORDER BY date").fetchall()


def read_day(date: str, with_amendments: bool = True) -> dict:
    """
    :param date: date as iso formatted string
    :param with_amendments: False to skip the amendments, which are much bigger than the rest
    :return: {<eu_document_code>: <content>} in the order they were written, empty if the day is unknown
    """
    with connect() as connection:
        if with_amendments:
            rows = connection.execute(
                "SELECT d.eu_document_code, d.content, a.content FROM documents d "
                "LEFT JOIN amendments a USING (date, eu_document_code) WHERE d.date = ? ORDER BY d.position",
                (date,)).fetchall()
        else:
            rows = connection.execute(
                "SELECT eu_document_code, content, NULL FROM documents WHERE date = ? ORDER BY position",
                (date,)).fetchall()
    day = {}
    for eu_document_code, content, amendments in rows:
        day[eu_document_code] = json.loads(content)
        if amendments is not None:
            day[eu_document_code]["amendments"] = json.loads(amendments)
    return day


def read_amendments(date: str) -> dict:
    """
    :return: {<eu_document_code>: [<amendment>]} for the documents of the day which have amendments
    """
    with connect() as connection:
        rows = connection.execute(
            "SELECT a.eu_document_code, a.content FROM amendments a "
            "JOIN documents d USING (date, eu_document_code) WHERE a.date = ? ORDER BY d.position",
            (date,)).fetchall()
    return {eu_document_code: json.loads(content) for eu_document_code, content in rows}


def search_documents(matches, start_date: str, end_date: str) -> Iterator[tuple[str, dict]]:
    """
    Documents voted between two dates whose search text matches, without their amendments
    :param matches: function called with the search text of each document, returning True to keep the document
    :param start_date: first day, as iso formatted string
    :param end_date: last day, included
    :return: (<date>, {<eu_document_code>: <content>}) for each day with matching documents, in chronological order
    """
    with connect() as connection:
        # The documents are filtered by SQLite, so the content of the others is not even read
        connection.create_function("matches", 1, lambda text: text is not None and matches(text), deterministic=True)
        rows = connection.execute(
            "SELECT date, eu_document_code, content FROM documents "
            "WHERE date BETWEEN ? AND ? AND matches(search_text) ORDER BY date, position",
            (start_date, end_date)).fetchall()
    current_date, documents = None, {}
    for date, eu_document_code, content in rows:
        if date != current_date:
            if documents:
                yield current_date, documents
            current_date, documents = date, {}
        documents[eu_document_code] = json.loads(content)
    if documents:
        yield current_date, documents
