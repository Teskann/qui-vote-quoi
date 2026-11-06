"""
Convert a database of JSON files (one file per day, used before the SQLite database) to the SQLite database.
The JSON files are not modified: remove them once the website works with the SQLite database.
"""
import argparse
import glob
import json
import os
import re

from database.database import set_root_database_path, get_database_path
from database import storage

DAY_FILE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def migrate(overwrite: bool = False) -> tuple[int, int]:
    """
    Convert the JSON files of the database directory
    :param overwrite: convert again the days which are already in the SQLite database
    :return: (<number of days converted>, <number of JSON files>)
    """
    files = sorted(file for file in glob.glob(os.path.join(get_database_path(), "*.json"))
                   if DAY_FILE_REGEX.match(os.path.basename(file)))
    converted = 0
    for file in files:
        date = os.path.basename(file)[:10]
        if not overwrite and storage.day_exists(date):
            continue
        with open(file, "r", encoding="utf-8") as f:
            storage.write_day(date, json.load(f))
        converted += 1
    return converted, len(files)


def main():
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument("--overwrite", action="store_true",
                            help="Convert again the days which are already in the SQLite database")
    args = arg_parser.parse_args()
    set_root_database_path()
    converted, files = migrate(args.overwrite)
    print(f"{converted} days converted out of {files} JSON files, "
          f"database: {os.path.join(get_database_path(), storage.DATABASE_FILE)}")


if __name__ == "__main__":
    main()
