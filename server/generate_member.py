import datetime
from os.path import join

import jinja2
from babel.dates import format_date

from database.members_index import get_all_members, database_dates
from server.common import get_css, TEMPLATES_PATH
from utils.date_management import parliament_number_from_date, date_from_parliament_number, year_from_parliament_number
from server.podiums import global_podiums, search_podiums
from server.filters import fr_number, add_flags, add_emojis, filter_political_group, political_group_tooltip, to_pretty_date, class_from_vote_result


def __months_between(first: str, last: str) -> list[str]:
    """
    :return: all the months from first to last included, as "YYYY-MM"
    """
    year, month = map(int, first.split("-"))
    months = []
    while f"{year:04d}-{month:02d}" <= last:
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def absenteeism_per_month(member: dict) -> list[dict]:
    """
    Absenteeism of the member for each month since their first vote. The months without any vote (no plenary
    sitting, or not in office) have a None rate.
    :return: [{"month": "2024-07", "label": "juillet 2024", "rate": <0 to 1 or None>, "absent": ..., "total": ...}]
    """
    if not member["months"]:
        return []
    result = []
    for month in __months_between(min(member["months"]), max(member["months"])):
        counts = member["months"].get(month, {"voted": 0, "absent": 0})
        total = counts["voted"] + counts["absent"]
        result.append({
            "month": month,
            "label": format_date(datetime.date.fromisoformat(month + "-01"), format="MMMM y", locale="fr"),
            "rate": counts["absent"] / total if total else None,
            "absent": counts["absent"],
            "total": total,
        })
    return result


def __template(name: str) -> jinja2.Template:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    env.filters["political_group"] = filter_political_group
    env.filters["political_group_tooltip"] = political_group_tooltip
    env.filters["to_pretty_date"] = to_pretty_date
    env.filters["class_from_vote_result"] = class_from_vote_result
    env.filters["search_podiums"] = search_podiums
    env.filters["fr_number"] = fr_number
    env.filters["add_flags"] = add_flags
    env.filters["add_emojis"] = add_emojis
    with open(join(TEMPLATES_PATH, name), encoding="utf-8") as f:
        return env.from_string(f.read())


def generate_member_page(member: dict) -> str:
    return __template("member_page.html.jinja").render(css=get_css(), member=member,
                                                       months=absenteeism_per_month(member),
                                                       today=datetime.date.today().isoformat())


def parliamentary_terms(first_date: str, last_date: str) -> list[dict]:
    """
    Parliamentary terms covered by the database
    :return: [{"label": "2019-2024", "start_date": "2019-07-02", "end_date": "2024-07-15"}], limited to the period
    of the database (first_date to last_date)
    """
    terms = []
    for number in range(parliament_number_from_date(first_date), parliament_number_from_date(last_date) + 1):
        start = date_from_parliament_number(number)
        following = date_from_parliament_number(number + 1)
        end = (following - datetime.timedelta(days=1)).isoformat() if following else last_date
        terms.append({"label": f"{year_from_parliament_number(number)}-{year_from_parliament_number(number + 1)}",
                      "start_date": max(start.isoformat(), first_date), "end_date": min(end, last_date)})
    return terms


def generate_ranking_page(start_date: str | None = None, end_date: str | None = None) -> str:
    """
    Ranking of all the members on the given period: podiums and full table
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    """
    members = get_all_members(start_date, end_date)
    first_date, last_date = database_dates() or (None, None)
    return __template("ranking_page.html.jinja").render(css=get_css(), members=members,
                                                        podiums=global_podiums(members),
                                                        start_date=start_date or first_date,
                                                        end_date=end_date or last_date,
                                                        first_date=first_date, last_date=last_date,
                                                        terms=parliamentary_terms(first_date, last_date)
                                                        if first_date else [])
