import os.path

from parser.empty_days_management import empty_days_txt_path, set_nothing_happened_for, nothing_happened_on, \
    create_empty_days_txt_file, set_something_happened_for


def test_empty_days_txt_path():
    assert os.path.exists(empty_days_txt_path())
    assert empty_days_txt_path().endswith("empty_days.txt")

def test_set_nothing_happened_for():
    # Clear the file
    create_empty_days_txt_file()

    assert not nothing_happened_on("2023-10-10")
    set_nothing_happened_for("2023-10-10")
    assert nothing_happened_on("2023-10-10")

    assert not nothing_happened_on("2018-01-24")
    set_nothing_happened_for("2018-01-24")
    assert nothing_happened_on("2018-01-24")

    # Clear the file
    create_empty_days_txt_file()


def test_something_happened_for():
    # Clear the file
    create_empty_days_txt_file()

    for date in ["2018-01-24", "2023-12-10","2017-01-15", "2023-10-11", "2023-10-10"]:
        assert not nothing_happened_on(date)
        set_nothing_happened_for(date)
        assert nothing_happened_on(date)

    # If date is not in file, should not crash
    set_something_happened_for("2018-01-25")
    assert not nothing_happened_on("2018-01-25")

    # If date is in the file, it should be removed
    assert nothing_happened_on("2018-01-24")
    set_something_happened_for("2018-01-24")
    assert not nothing_happened_on("2018-01-24")

    assert nothing_happened_on("2023-10-10")
    set_something_happened_for("2023-10-10")
    assert not nothing_happened_on("2023-10-10")

    for date in ["2023-12-10","2017-01-15", "2023-10-11"]:
        assert nothing_happened_on(date)

    # Clear the file
    create_empty_days_txt_file()