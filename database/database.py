import os.path

__DATABASE_PATH = None


class DataBasePathNotSet(Exception):
    pass


def set_root_database_path():
    HERE = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(HERE, "..", "database_path.txt"), "r") as f:
        set_database_path(f.read())


def set_database_path(path: str):
    """
    Set the database path in DATABASE_PATH
    :param path: Path to set. Must be a directory
    """
    global __DATABASE_PATH
    __DATABASE_PATH = path


def get_database_path() -> str:
    if __DATABASE_PATH is None:
        raise DataBasePathNotSet()
    return __DATABASE_PATH


def get_path(*args):
    return os.path.join(get_database_path(), *args)


def exists(*args):
    return os.path.exists(get_path(*args))
