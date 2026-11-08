"""
Compute the statistics of the days of the database written before the statistics were stored with each day (see
database.statistics). Run once after the update: the votes are read from the database, nothing is downloaded.
fill_database does it too, at the end.
"""
from database.database import set_root_database_path
from database.database_writer import fill_statistics


if __name__ == "__main__":
    set_root_database_path()
    fill_statistics()
