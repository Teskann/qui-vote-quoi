from parser.open_data import get_sitting_dates


def test_get_sitting_dates():
    # The format of the dates in the API changed over time
    for year, date in [(2015, "2015-12-16"), (2019, "2019-12-18"), (2024, "2024-10-08")]:
        dates = get_sitting_dates(year)
        assert 40 < len(dates) < 70
        assert date in dates
    assert "2024-10-12" not in get_sitting_dates(2024)  # Saturday
