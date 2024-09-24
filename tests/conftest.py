from tests import setup_database


def pytest_sessionstart(session):
    setup_database.setup()