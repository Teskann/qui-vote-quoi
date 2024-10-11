from database.database import set_database_path, get_database_path, get_path
import os

from parser.empty_days_management import create_empty_days_txt_file


def clear_database():
    for file in os.listdir(get_database_path()):
        if file != ".gitignore":
            os.remove(get_path(file))
    create_empty_days_txt_file()


def setup():
    HERE = os.path.dirname(os.path.abspath(__file__))
    set_database_path(os.path.join(HERE, "actual"))
    if not os.path.exists(get_database_path()):
        os.makedirs(get_database_path())
    clear_database()