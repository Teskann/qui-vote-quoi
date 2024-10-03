from utils.date_management import *

def test_parliament_number_from_date():
    assert parliament_number_from_date("2024-09-19") == 10
    assert parliament_number_from_date("2022-06-23") == 9
    assert parliament_number_from_date("2022-06-22") == 9
    assert parliament_number_from_date("2018-06-23") == 8
    assert parliament_number_from_date("2016-06-23") == 8
    assert parliament_number_from_date("2011-01-05") == 7

def test_year_from_parliament_number():
    assert year_from_parliament_number(12) == 2034
    assert year_from_parliament_number(11) == 2029
    assert year_from_parliament_number(10) == 2024
    assert year_from_parliament_number(9) == 2019
    assert year_from_parliament_number(8) == 2014
    assert year_from_parliament_number(7) == 2009
    assert year_from_parliament_number(6) == 2004
    assert year_from_parliament_number(5) == 1999
    assert year_from_parliament_number(4) == 1994
    assert year_from_parliament_number(3) == 1989
    assert year_from_parliament_number(2) == 1984
    assert year_from_parliament_number(1) == 1979
    assert year_from_parliament_number(0) is None


def test_date_range():
    expected = ["2022-05-29", "2022-05-30", "2022-05-31", "2022-06-01", "2022-06-02"]
    actual = []
    for date in date_range("2022-05-29", "2022-06-02"):
        actual.append(date)
    assert actual == expected
