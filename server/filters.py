import datetime
from babel.dates import format_date


def political_group_url(group_name):
    links = {
        "France / ECR :": "https://www.ecrgroup.eu/",
        "France / ENS :": "https://fr.wikipedia.org/wiki/L%27Europe_des_nations_souveraines",
        "France / PfE :": "https://www.patriotsforeurope.org/",
        "France / ID :": "https://www.facebook.com/IDgroupEP/",
        "France / PPE :": "https://www.eppgroup.eu/fr/",
        "France / Renew :": "https://www.reneweuropegroup.eu/fr",
        "France / S&D :": "https://www.socialistsanddemocrats.eu/",
        "France / The Left :": "https://left.eu/",
        "France / Verts/ALE :": "https://www.greens-efa.eu/en/",
        "France / NI :": "https://en.wikipedia.org/wiki/Non-attached_members",
    }
    return links[group_name] if group_name in links else ""


def political_group_class(group_name):
    classes = {
        "France / ECR :": "group_ecr",
        "France / ENS :": "group_ens",
        "France / PfE :": "group_pfe",
        "France / ID :": "group_id",
        "France / PPE :": "group_ppe",
        "France / Renew :": "group_renew",
        "France / S&D :": "group_sd",
        "France / The Left :": "group_left",
        "France / Verts/ALE :": "group_verts",
        "France / NI :": "group_ni",
    }
    return classes[group_name] if group_name in classes else "group_ni"

def political_group_tooltip(group_name):
    classes = {
        "France / ECR :": "Conservateurs et réformistes européens (droite à extrême droite)",
        "France / ENS :": "L'Europe des nations souveraines (extrême droite)",
        "France / PfE :": "Patriotes pour l'Europe (droite à extrême droite)",
        "France / ID :": "Parti Identité et démocratie (droite radicale à extrême)",
        "France / PPE :": "Groupe du Parti populaire européen (dentre droit à droite)",
        "France / Renew :": "Renew Europe (centre)",
        "France / S&D :": "Alliance progressiste des socialistes et démocrates au Parlement européen (gauche à centre gauche)",
        "France / The Left :": "Groupe de la Gauche au Parlement européen (gauche à extrême gauche)",
        "France / Verts/ALE :": "Groupe des Verts/Alliance libre européenne (centre gauche à gauche)",
        "France / NI :": "Non-inscrit au Parlement européen",
    }
    return classes[group_name] if group_name in classes else "Aucune information n'est connue au sujet de ce parti"


def class_from_vote_result(result):
    classes = {"+": "voted_for", "-": "voted_against", "0": "abstained"}
    return classes[result] if result in classes else "abstained"


def filter_political_group(group_name):
    group_name = group_name.replace("France / ", "")
    group_name = group_name[:-2]
    group_name = group_name.replace("The Left", "La Gauche").replace("Verts/ALE", "Les&nbsp;Verts")
    return group_name

def is_last_iterator(iterator):
    for i, item in enumerate(iterator):
        yield i == len(iterator) - 1, item

def to_pretty_date(date):
    return format_date(datetime.date.fromisoformat(date), format='long', locale='fr')