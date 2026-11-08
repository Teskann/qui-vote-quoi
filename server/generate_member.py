import datetime
import functools
from os.path import join

import jinja2
from babel.dates import format_date

from database.members_index import get_all_members, get_member_group, get_groups_votes, get_group_recent_votes, database_dates, FINAL, AMENDMENTS, VOTE_KINDS
from server.common import get_css, TEMPLATES_PATH
from utils.date_management import parliament_number_from_date, date_from_parliament_number, year_from_parliament_number
from server.podiums import global_podiums, search_podiums, group_statistics, group_podiums, RENAMED_GROUPS
from server.filters import fr_number, fr_decimal, group_slug, HEADS_OF_LIST, add_flags, add_emojis, filter_political_group, political_group_logo, political_group_tooltip, to_pretty_date, class_from_vote_result, agree


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


@functools.cache
def __template(name: str) -> jinja2.Template:
    """
    Compiled once, as the compilation takes longer than the rendering
    """
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_PATH))
    env.filters["political_group"] = filter_political_group
    env.filters["political_group_logo"] = political_group_logo
    env.filters["group_slug"] = group_slug
    env.filters["political_group_tooltip"] = political_group_tooltip
    env.filters["to_pretty_date"] = to_pretty_date
    env.filters["class_from_vote_result"] = class_from_vote_result
    env.filters["search_podiums"] = search_podiums
    env.filters["fr_number"] = fr_number
    env.filters["fr_decimal"] = fr_decimal
    env.filters["add_flags"] = add_flags
    env.filters["add_emojis"] = add_emojis
    env.globals["agree"] = agree
    with open(join(TEMPLATES_PATH, name), encoding="utf-8") as f:
        return env.from_string(f.read())


def generate_member_page(member: dict, filters: dict, corrections: list[dict]) -> str:
    """
    :param member: see get_member, with the filters applied
    :param filters: see filters_context
    :param corrections: votes on which the member voted by mistake, see get_member_corrections
    """
    return __template("member_page.html.jinja").render(css=get_css(), member=member, filters=filters,
                                                       corrections=corrections,
                                                       months=absenteeism_per_month(member) if "months" in member else [],
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


# Kinds of votes of the statistics, by value of the "votes" parameter of the URL
FILTER_VOTES = {"tous": VOTE_KINDS, "finaux": (FINAL,), "amendements": (AMENDMENTS,)}


def filters_context(start_date: str | None, end_date: str | None, votes: str | None) -> dict:
    """
    Filters of the statistics (see filters.html.jinja)
    :param start_date: first day of the period, as iso formatted string. None for the beginning of the database.
    :param end_date: last day of the period, included. None for the end of the database.
    :param votes: votes counted, see FILTER_VOTES. All the votes when unknown.
    :return: {"start_date", "end_date", "votes", "kinds", "first_date", "last_date", "terms"}. "start_date" and
    "end_date" are those of the database when not given, and are kept within those of the database.
    """
    first_date, last_date = database_dates() or (None, None)
    votes = votes if votes in FILTER_VOTES else "tous"
    if first_date:
        # Dates beyond those of the database (today, for example) are brought back to them
        start_date = max(start_date, first_date) if start_date else first_date
        end_date = min(end_date, last_date) if end_date else last_date
    return {"start_date": start_date, "end_date": end_date, "votes": votes,
            "kinds": FILTER_VOTES[votes], "first_date": first_date, "last_date": last_date,
            "terms": parliamentary_terms(first_date, last_date) if first_date else []}


def generate_ranking_page(filters: dict, by_group: bool = False) -> str:
    """
    Ranking of all the members on the given period: podiums and full table
    :param filters: see filters_context
    :param by_group: rank the political groups, the members being listed under their group
    """
    members = get_all_members(filters["start_date"], filters["end_date"], filters["kinds"])
    groups = group_statistics(members)
    return __template("ranking_page.html.jinja").render(css=get_css(), members=members, groups=groups,
                                                        by_group=by_group, filters=filters,
                                                        podiums=group_podiums(groups) if by_group
                                                        else global_podiums(members))


def __competition_rank(value, values: list) -> int:
    """
    :return: rank of value among values, by decreasing value. Equal values share the same rank (1, 1, 3, ...).
    """
    return 1 + sum(1 for other in values if other > value)


def __heads_of_list(group: str, all_members: list[dict]) -> list[dict]:
    """
    :return: [{"member": <statistics of the member, see get_all_members>, "lists": [{"terms": "2019-2024, 2024-2029",
    "list": "Liste LFI"}], "other_group": <group the member sat in instead of this one during their last term as head of
    list, None if it's this one>, "current": <the last term is the current one>}] for the heads of the French lists
    elected in the group, most recent first. A member head of list for several terms is given once. See HEADS_OF_LIST.
    :param all_members: statistics of the members over the whole database, see get_all_members
    """
    members = {member["id"]: member for member in all_members}
    current_term = parliament_number_from_date(datetime.date.today().isoformat())
    heads = {}
    for term, lists in sorted(HEADS_OF_LIST.items(), reverse=True):
        label = f"{year_from_parliament_number(term)}-{year_from_parliament_number(term + 1)}"
        start, end = date_from_parliament_number(term), date_from_parliament_number(term + 1)
        for name, entries in lists.items():
            if RENAMED_GROUPS.get(name, name) != group:
                continue
            for list_name, identifier in entries:
                if identifier not in members:
                    continue
                head = heads.setdefault(identifier, {"member": members[identifier], "lists": {}, "other_group": None,
                                                     "current": term == current_term})
                head["lists"].setdefault(list_name, []).insert(0, label)
                # The end of the current term is not known yet
                sat_in = get_member_group(identifier, start.isoformat(), end.isoformat() if end else None)
                if len(head["lists"]) == 1 and len(head["lists"][list_name]) == 1 and sat_in \
                        and RENAMED_GROUPS.get(sat_in, sat_in) != group:
                    head["other_group"] = sat_in
    return [{**head, "lists": [{"terms": ", ".join(terms), "list": list_name} for list_name, terms in head["lists"].items()]}
            for head in heads.values()]


def __group_recent_votes(group: str, all_members: list[dict]) -> list[dict]:
    """
    :param group: current name of the group (see RENAMED_GROUPS)
    :param all_members: statistics of the members over the whole database, see get_all_members
    :return: see get_group_recent_votes, whatever the filters, like the recent votes of the members
    """
    names = {group} | {old for old, new in RENAMED_GROUPS.items() if new == group}
    months = [month for member in all_members if RENAMED_GROUPS.get(member["group"], member["group"]) == group
              for month in member["months"]]
    return get_group_recent_votes(names, max(months)) if months else []


def generate_group_page(slug: str, filters: dict) -> str | None:
    """
    Page of a political group: statistics of its members, cohesion, and how often it votes like the other groups
    :param slug: identifier of the group in the URL, see group_slug
    :param filters: see filters_context
    :return: None if there is no such group in the database
    """
    all_groups = group_statistics(all_members := get_all_members())
    if not any(group_slug(group["group"]) == slug for group in all_groups):
        return None
    groups = group_statistics(get_all_members(filters["start_date"], filters["end_date"], filters["kinds"]))
    # The group may have no vote on the period: its page is still shown, with the filters to change it
    group = next((group for group in groups if group_slug(group["group"]) == slug), None)
    if group is None:
        name = next(group["group"] for group in all_groups if group_slug(group["group"]) == slug)
        return __template("group_page.html.jinja").render(css=get_css(), group={"group": name}, filters=filters,
                                                          slug=slug, empty=True,
                                                          today=datetime.date.today().isoformat())

    def current(name):
        return RENAMED_GROUPS.get(name, name)

    votes = get_groups_votes(filters["start_date"], filters["end_date"], filters["kinds"])
    # {<group>: [<number of votes>, <sum of the shares>]}, the renamed groups being merged
    cohesion_totals = {}
    for name, (count, shares) in votes["cohesion"].items():
        total = cohesion_totals.setdefault(current(name), [0, 0])
        total[0] += count
        total[1] += shares
    cohesions = {name: shares / count for name, (count, shares) in cohesion_totals.items()
                 if name in {other["group"] for other in groups}}
    cohesion = cohesions.get(group["group"])

    proximity = {}
    for (name, other), (same, total) in votes["proximity"].items():
        if current(name) == group["group"] and current(other) != group["group"]:
            entry = proximity.setdefault(current(other), {"group": current(other), "same": 0, "total": 0})
            entry["same"] += same
            entry["total"] += total
    for entry in proximity.values():
        entry["rate"] = entry["same"] / entry["total"]

    # Ranks among the groups of the database
    ranks = {key: __competition_rank(group[key], [other[key] for other in groups])
             for key in ("members_count", "absent_rate", "corrections_average")}
    ranks["cohesion"] = __competition_rank(cohesion, list(cohesions.values())) if cohesion is not None else None

    return __template("group_page.html.jinja").render(
        css=get_css(), group=group, today=datetime.date.today().isoformat(), ranks=ranks, filters=filters, slug=slug,
        heads_of_list=__heads_of_list(group["group"], all_members),
        recent=__group_recent_votes(group["group"], all_members),
        empty=False,
        groups_count=len(groups), cohesion_groups_count=len(cohesions),
        cohesion=cohesion, cohesion_votes=cohesion_totals.get(group["group"], [0])[0],
        proximity=sorted(proximity.values(), key=lambda entry: -entry["rate"]))
