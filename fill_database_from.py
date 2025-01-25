import sys
import os

import datetime

from database.database import  set_root_database_path
from database.database_writer import fill_database
from parser.empty_days_management import create_empty_days_txt_file_if_does_not_exist


def main():
    yesterday_arg = "yesterday"
    today_arg = "today"
    allowed_args = [yesterday_arg, today_arg]
    if len(sys.argv) < 2 or sys.argv[1] not in allowed_args:
        exit(f"Usage: python {os.path.relpath(__file__)} [{"|".join(allowed_args)}]")
    set_root_database_path()
    create_empty_days_txt_file_if_does_not_exist()
    date_to_process = datetime.date.today() - datetime.timedelta(days=1 if sys.argv[1] == yesterday_arg else 0)
    fill_database(date_to_process.isoformat(), date_to_process.isoformat(), overwrite=True, overwrite_empty_days=True)


if __name__ == "__main__":
    main()
