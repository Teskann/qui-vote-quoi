import datetime

def parliament_number_from_date(date: str) -> int:
    isodate = datetime.date.fromisoformat(date)
    # https://fr.wikipedia.org/wiki/Dixi%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("2024-07-16"):
        return 10
    # https://fr.wikipedia.org/wiki/Neuvi%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("2019-07-02"):
        return 9
    # https://fr.wikipedia.org/wiki/Huiti%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("2014-07-01"):
        return 8
    # https://fr.wikipedia.org/wiki/Septi%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("2009-07-14"):
        return 7
    # https://fr.wikipedia.org/wiki/Sixi%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("2004-07-20"):
        return 6
    # https://fr.wikipedia.org/wiki/Cinqui%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("1999-07-20"):
        return 5
    # https://fr.wikipedia.org/wiki/Quatri%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("1994-07-19"):
        return 4
    # https://fr.wikipedia.org/wiki/Troisi%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("1989-07-25"):
        return 3
    # https://fr.wikipedia.org/wiki/Deuxi%C3%A8me_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("1984-07-24"):
        return 2
    # https://fr.wikipedia.org/wiki/Premi%C3%A8re_l%C3%A9gislature_du_Parlement_europ%C3%A9en
    if isodate >= datetime.date.fromisoformat("1979-07-16"):
        return 1
    return 0

def year_from_parliament_number(number: int) -> int:
    matches = {
        1: 1979,
        2: 1984,
        3: 1989,
        4: 1994,
        5: 1999,
        6: 2004,
        7: 2009,
        8: 2014,
        9: 2019,
        10: 2024,
        11: 2029,
        12: 2034,
    }
    return matches[number] if number in matches else None


def votes_roll_call_source_url(date):
    return f"https://www.europarl.europa.eu/doceo/document/PV-{parliament_number_from_date(date)}-{date}-RCV_FR.html"

def votes_source_url(date):
    return f"https://www.europarl.europa.eu/doceo/document/PV-{parliament_number_from_date(date)}-{date}-VOT_FR.html"


def date_range(start_date, end_date):
    start_date = datetime.date.fromisoformat(start_date)
    end_date = datetime.date.fromisoformat(end_date)
    days = int((end_date - start_date).days)
    for n in range(days + 1):
        yield (start_date + datetime.timedelta(n)).isoformat()