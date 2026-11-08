"""
Storage of the votes in a SQLite database, in the database directory (see database.database).

Each voted document is a row of the "documents" table. The votes held on the document (amendments, paragraphs, ...)
are stored apart, in the "amendments" table: they make most of the volume of the database, and are not needed to
display the search results.

The statistics of the members and of the groups are computed from the votes of each day when the day is written (see
database.statistics), in the tables below "amendments": the website reads them with SQL, without decoding the votes.

The database is in WAL mode, so that the website can read it while it's updated.
"""
import contextlib
import json
import sqlite3
import time
from typing import Iterator

from unidecode import unidecode

from database.database import get_path
from database import statistics

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
-- Days whose statistics are in the tables below (the days written before these tables existed don't have them)
CREATE TABLE IF NOT EXISTS statistics_days (
    date TEXT PRIMARY KEY REFERENCES days(date) ON DELETE CASCADE
);
-- Statistics of each member on the roll-call votes of a day, per kind of vote (see statistics.day_statistics)
CREATE TABLE IF NOT EXISTS member_days (
    date TEXT NOT NULL REFERENCES days(date) ON DELETE CASCADE,
    -- 0 for the final votes, 1 for the other votes (see KINDS)
    kind INTEGER NOT NULL,
    -- Order of the members in the votes of the day
    position INTEGER NOT NULL,
    member_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    group_name TEXT NOT NULL,
    voted INTEGER NOT NULL,
    absent INTEGER NOT NULL,
    corrections INTEGER NOT NULL,
    PRIMARY KEY (date, kind, member_id)
);
CREATE INDEX IF NOT EXISTS member_days_member ON member_days (member_id, date);
CREATE TABLE IF NOT EXISTS group_cohesion (
    date TEXT NOT NULL REFERENCES days(date) ON DELETE CASCADE,
    kind INTEGER NOT NULL,
    position INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    -- Number of votes with at least 2 members of the group voting for or against
    votes INTEGER NOT NULL,
    -- Sum of the shares of the members who voted like the majority of the group
    shares REAL NOT NULL,
    PRIMARY KEY (date, kind, group_name)
);
CREATE TABLE IF NOT EXISTS group_proximity (
    date TEXT NOT NULL REFERENCES days(date) ON DELETE CASCADE,
    kind INTEGER NOT NULL,
    position INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    other_group TEXT NOT NULL,
    -- Votes where both groups had the same majority position
    same INTEGER NOT NULL,
    -- Votes where both groups had a majority position
    votes INTEGER NOT NULL,
    PRIMARY KEY (date, kind, group_name, other_group)
);
-- Votes on which a member declared afterwards what they meant to vote
CREATE TABLE IF NOT EXISTS corrections (
    date TEXT NOT NULL REFERENCES days(date) ON DELETE CASCADE,
    -- Order of the corrections in the day
    position INTEGER NOT NULL,
    kind INTEGER NOT NULL,
    member_id TEXT NOT NULL,
    vote_id TEXT NOT NULL,
    eu_document_code TEXT NOT NULL,
    title TEXT,
    label TEXT,
    -- What the member voted, NULL if they didn't vote
    voted TEXT,
    intended TEXT,
    PRIMARY KEY (date, position)
);
CREATE INDEX IF NOT EXISTS corrections_member ON corrections (member_id, date);
-- Statistics of each member on the final vote of a document, for the podiums of the searches
CREATE TABLE IF NOT EXISTS document_members (
    date TEXT NOT NULL,
    eu_document_code TEXT NOT NULL,
    member_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    group_name TEXT NOT NULL,
    voted INTEGER NOT NULL,
    absent INTEGER NOT NULL,
    corrections INTEGER NOT NULL,
    PRIMARY KEY (date, eu_document_code, member_id),
    FOREIGN KEY (date, eu_document_code) REFERENCES documents(date, eu_document_code) ON DELETE CASCADE
);
-- Groups which voted on a document, for the similarity of the groups in the searches
CREATE TABLE IF NOT EXISTS document_groups (
    date TEXT NOT NULL,
    eu_document_code TEXT NOT NULL,
    group_name TEXT NOT NULL,
    -- 1 if the majority of the group voted for, 0 if against, NULL if as many voted for as against or if the final
    -- vote was not a roll-call vote (see statistics.document_group_positions)
    majority INTEGER,
    -- 0 when the final vote was not a roll-call vote: the group is only listed
    compared INTEGER NOT NULL,
    PRIMARY KEY (date, eu_document_code, group_name),
    FOREIGN KEY (date, eu_document_code) REFERENCES documents(date, eu_document_code) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS genders (
    -- Identifier of the member (PersId)
    id TEXT PRIMARY KEY,
    -- "F" or "M", to make the words agree with the member
    gender TEXT NOT NULL
);
"""


# Value of the "kind" columns for each kind of vote. The final votes come first.
KINDS = {statistics.FINAL: 0, statistics.AMENDMENTS: 1}


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
        __write_statistics(connection, date, votes_per_document)


def __write_statistics(connection: sqlite3.Connection, date: str, votes_per_document: dict):
    """
    Write the statistics of a day (see the tables below "amendments"), replacing those stored for this day
    :param votes_per_document: {<eu_document_code>: <content>}, with the "amendments"
    """
    for table in ("statistics_days", "member_days", "group_cohesion", "group_proximity", "corrections"):
        connection.execute(f"DELETE FROM {table} WHERE date = ?", (date,))
    connection.execute("DELETE FROM document_members WHERE date = ?", (date,))
    connection.execute("DELETE FROM document_groups WHERE date = ?", (date,))
    day = statistics.day_statistics(date, votes_per_document)
    for kind, number in KINDS.items():
        connection.executemany(
            "INSERT INTO member_days (date, kind, position, member_id, full_name, group_name, voted, absent, corrections) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(date, number, position, identifier, stats["full_name"], stats["group"], stats["voted"], stats["absent"],
              stats["corrections"]) for position, (identifier, stats) in enumerate(day["members"][kind].items())])
        connection.executemany(
            "INSERT INTO group_cohesion (date, kind, position, group_name, votes, shares) VALUES (?, ?, ?, ?, ?, ?)",
            [(date, number, position, group, votes, shares)
             for position, (group, (votes, shares)) in enumerate(day["cohesion"][kind].items())])
        connection.executemany(
            "INSERT INTO group_proximity (date, kind, position, group_name, other_group, same, votes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(date, number, position, group, other, same, votes)
             for position, ((group, other), (same, votes)) in enumerate(day["proximity"][kind].items())])
    connection.executemany(
        "INSERT INTO corrections (date, position, kind, member_id, vote_id, eu_document_code, title, label, voted, "
        "intended) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(date, position, KINDS[correction["kind"]], correction["member_id"], correction["vote_id"],
          correction["eu_document_code"], correction["title"], correction["label"], correction["voted"],
          correction["intended"]) for position, correction in enumerate(day["corrections"])])
    for eu_document_code, content in votes_per_document.items():
        connection.executemany(
            "INSERT INTO document_members (date, eu_document_code, member_id, full_name, group_name, voted, absent, "
            "corrections) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(date, eu_document_code, identifier, stats["full_name"], stats["group"], stats["voted"], stats["absent"],
              stats["corrections"]) for identifier, stats in statistics.document_members(content).items()])
        positions = statistics.document_group_positions(content)
        # The groups of a document whose final vote was not a roll-call vote are still listed in the comparison
        groups = positions if positions is not None else \
            dict.fromkeys(group for groups in content.get("votes", {}).values() for group in groups)
        connection.executemany(
            "INSERT INTO document_groups (date, eu_document_code, group_name, majority, compared) VALUES (?, ?, ?, ?, ?)",
            [(date, eu_document_code, group, majority, positions is not None) for group, majority in groups.items()])
    connection.execute("INSERT INTO statistics_days (date) VALUES (?)", (date,))


def days_without_statistics() -> list[str]:
    """
    :return: the days written before the statistics were stored, in chronological order
    """
    with connect() as connection:
        return [date for date, in connection.execute(
            "SELECT date FROM days WHERE date NOT IN (SELECT date FROM statistics_days) ORDER BY date")]


def write_statistics(date: str):
    """
    Compute and write the statistics of a day already in the database
    """
    documents = read_day(date)
    with connect() as connection:
        __write_statistics(connection, date, documents)


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


def write_genders(genders: dict):
    """
    :param genders: {<identifier>: <"F" or "M">}, added to those already stored
    """
    with connect() as connection:
        connection.executemany("INSERT OR REPLACE INTO genders (id, gender) VALUES (?, ?)", genders.items())


def read_genders() -> dict:
    """
    :return: {<identifier>: <"F" or "M">} for the members whose gender is known
    """
    with connect() as connection:
        return dict(connection.execute("SELECT id, gender FROM genders").fetchall())


def read_documents(keys: list[tuple[str, str]]) -> dict:
    """
    :param keys: [(<date>, <eu_document_code>)]
    :return: {(<date>, <eu_document_code>): <content>} for the documents found, without their amendments, in the order
    of keys
    """
    with connect() as connection:
        found = {}
        for date, eu_document_code in keys:
            row = connection.execute("SELECT content FROM documents WHERE date = ? AND eu_document_code = ?",
                                     (date, eu_document_code)).fetchone()
            if row is not None:
                found[(date, eu_document_code)] = json.loads(row[0])
    return found


@contextlib.contextmanager
def __search_connection(matches) -> Iterator[sqlite3.Connection]:
    """
    Connection on which the documents found are given by FOUND (with the parameters start_date and end_date)
    :param matches: function called with the search text of each document, returning True to keep the document
    """
    with connect() as connection:
        # The documents are filtered by SQLite, so the content of the others is not even read
        connection.create_function("matches", 1, lambda text: text is not None and matches(text), deterministic=True)
        yield connection


# Documents found by a search, see __search_connection
FOUND = "SELECT date, eu_document_code, position FROM documents WHERE date BETWEEN ? AND ? AND matches(search_text)"
# The same, computed once before being joined with the statistics of the documents (otherwise SQLite may call matches()
# for each row of the statistics). "ordinal" is the chronological order of the documents.
FOUND_TABLE = ("WITH found AS MATERIALIZED (SELECT date, eu_document_code, "
               "ROW_NUMBER() OVER (ORDER BY date, position) AS ordinal FROM documents "
               "WHERE date BETWEEN ? AND ? AND matches(search_text)) ")


def search_keys(matches, start_date: str, end_date: str) -> list[tuple[str, str]]:
    """
    Same as search_documents, without reading the content of the documents
    :return: [(<date>, <eu_document_code>)] in chronological order
    """
    with __search_connection(matches) as connection:
        return connection.execute(f"SELECT date, eu_document_code FROM ({FOUND}) ORDER BY date, position",
                                  (start_date, end_date)).fetchall()


def search_members(matches, start_date: str, end_date: str) -> list[dict]:
    """
    Statistics of the members on the final votes of the documents found by a search (see search_documents)
    :return: [{"id", "full_name", "group", "voted", "absent", "absent_rate", "corrections"}]. The latest name and group
    of each member are given.
    """
    with __search_connection(matches) as connection:
        # SQLite takes the name and the group from the row of MAX(): the latest document
        rows = connection.execute(
            FOUND_TABLE + "SELECT member_id, full_name, group_name, SUM(voted), SUM(absent), SUM(corrections), "
            "MAX(ordinal) FROM found JOIN document_members USING (date, eu_document_code) GROUP BY member_id",
            (start_date, end_date)).fetchall()
    return [{"id": identifier, "voted": voted, "absent": absent, "corrections": corrections, "full_name": full_name,
             "group": group, "absent_rate": absent / (voted + absent)}
            for identifier, full_name, group, voted, absent, corrections, _ in rows]


def search_group_pairs(matches, start_date: str, end_date: str) -> tuple[set[str], dict]:
    """
    How often the groups had the same majority on the final votes of the documents found by a search (see
    search_documents)
    :return: (<groups which voted on the documents>, {(<group>, <other group>): (<documents where both had the same
    majority>, <documents where both had a majority>)}, in both orders)
    """
    with __search_connection(matches) as connection:
        groups = {group for group, in connection.execute(
            FOUND_TABLE + "SELECT DISTINCT group_name FROM found JOIN document_groups USING (date, eu_document_code)",
            (start_date, end_date))}
        pairs = {}
        for group, other, same, total in connection.execute(
                FOUND_TABLE + "SELECT a.group_name, b.group_name, SUM(a.majority = b.majority), COUNT(*) "
                "FROM found JOIN document_groups a USING (date, eu_document_code) "
                "JOIN document_groups b ON b.date = a.date AND b.eu_document_code = a.eu_document_code "
                "AND b.group_name > a.group_name "
                "WHERE a.compared AND a.majority IS NOT NULL AND b.majority IS NOT NULL "
                "GROUP BY a.group_name, b.group_name", (start_date, end_date)):
            pairs[(group, other)] = pairs[(other, group)] = (same, total)
    return groups, pairs


def search_documents(matches, start_date: str, end_date: str) -> Iterator[tuple[str, dict]]:
    """
    Documents voted between two dates whose search text matches, without their amendments. The rows are read one day
    at a time, so that a search over many years doesn't hold all the documents in memory.
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
            (start_date, end_date))
        current_date, documents = None, {}
        for date, eu_document_code, content in rows:
            if date != current_date:
                if documents:
                    yield current_date, documents
                current_date, documents = date, {}
            documents[eu_document_code] = json.loads(content)
        if documents:
            yield current_date, documents
