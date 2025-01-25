import database.database


def empty_days_txt_path() -> str:
    """
    Get the path to `empty_days.txt` file
    """
    return database.database.get_path("empty_days.txt")


def create_empty_days_txt_file():
    with open(empty_days_txt_path(), "w", encoding="utf-8"):
        pass


def create_empty_days_txt_file_if_does_not_exist():
    if not database.database.exists(empty_days_txt_path()):
        create_empty_days_txt_file()


def set_nothing_happened_for(date: str):
    """
    Write date in DATABASE/empty_days.txt
    :param date: date to write
    :return: None
    """
    with open(empty_days_txt_path(), "a", encoding="utf-8") as f:
        f.write(date + "\n")


def set_something_happened_for(date: str):
    """
    Remove date from DATABASE/empty_days.txt
    :param date: date to remove
    :return: None
    """
    with open(empty_days_txt_path(), "r", encoding="utf-8") as f:
        dates = f.read().split("\n")
    if date in dates:
        dates.remove(date)
    with open(empty_days_txt_path(), "w", encoding="utf-8") as f:
        f.write("\n".join(dates))


def nothing_happened_on(date: str) -> bool:
    """
    Check if nothing happened in the passed date, checking empty_days.txt in the database.
    :param date: date to check as iso formatted string
    :return: True if nothing happened in this date, False otherwise
    """
    with open(empty_days_txt_path(), "r", encoding="utf-8") as f:
        empty_days = f.read().split('\n')
    return date in empty_days
