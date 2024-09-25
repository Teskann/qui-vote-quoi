import argparse

from database.database import set_database_path, set_root_database_path
from database.database_writer import fill_database
from parser.empty_days_management import create_empty_days_txt_file_if_does_not_exist


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--start-date", required=True, help="Start date in ISO format (YYYY-MM-DD)")
    arg_parser.add_argument("--end-date", required=True, help="End date in ISO format (YYYY-MM-DD)")
    arg_parser.add_argument("--overwrite", required=False, action="store_true",
                            help="Use this flag to overwrite the existing files in the database")

    args = arg_parser.parse_args()
    set_root_database_path()
    create_empty_days_txt_file_if_does_not_exist()
    fill_database(args.start_date, args.end_date, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
