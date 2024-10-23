import datetime

from database.database import  set_root_database_path
from database.database_writer import fill_database
from parser.empty_days_management import create_empty_days_txt_file_if_does_not_exist


def main():
    set_root_database_path()
    create_empty_days_txt_file_if_does_not_exist()
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    fill_database(yesterday.isoformat(), yesterday.isoformat(), overwrite=True)


if __name__ == "__main__":
    main()
