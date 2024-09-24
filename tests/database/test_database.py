import os.path

from database.database import *

def test_get_database_path():
    assert get_database_path() is not None


def test_get_path():
    assert get_path("here", "and", "there.txt") == os.path.join(get_database_path(), "here", "and", "there.txt")

def test_exists():
    assert not exists("Unknown file")
    assert not exists("Unknown dir", "Unknown file")

    assert not exists("tmpFile")
    with open(get_path("tmpFile"), "w"):
        pass
    assert exists("tmpFile")
    os.remove(get_path("tmpFile"))
    assert not exists("tmpFile")