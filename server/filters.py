import datetime
import re
import threading
import time

from babel.dates import format_date

from database import storage
from database.members_index import is_final_vote  # Used by the templates
from utils.date_management import parliament_number_from_date, year_from_parliament_number


# Seconds during which the genders read from the database are reused
GENDERS_LIFETIME = 60
__genders_lock = threading.Lock()
__genders = {"read_at": None, "genders": {}}


def member_gender(member) -> str | None:
    """
    :param member: identifier of a member, or member as stored in the votes ({"id", ...})
    :return: "F", "M", or None if unknown
    """
    identifier = member.get("id") if isinstance(member, dict) else member
    with __genders_lock:
        if __genders["read_at"] is None or time.monotonic() - __genders["read_at"] > GENDERS_LIFETIME:
            __genders["genders"] = storage.read_genders()
            __genders["read_at"] = time.monotonic()
        return __genders["genders"].get(identifier)


def agree(members, masculine: str, feminine: str, unknown: str | None = None) -> str:
    """
    Word agreeing with the gender of the members
    :param members: a member (see member_gender), or a list of members
    :param unknown: word for a single member whose gender is unknown, the masculine one by default
    :return: for a list, the feminine word only if all the members are women
    """
    if isinstance(members, (list, tuple)):
        return feminine if members and all(member_gender(member) == "F" for member in members) else masculine
    gender = member_gender(members)
    return feminine if gender == "F" else masculine if gender == "M" or unknown is None else unknown


def political_group_url(group_name):
    links = {
        "France / ECR :": "https://www.ecrgroup.eu/",
        "France / ESN :": "https://fr.wikipedia.org/wiki/L%27Europe_des_nations_souveraines",
        "France / PfE :": "https://www.patriotsforeurope.org/",
        "France / ID :": "https://www.facebook.com/IDgroupEP/",
        "France / PPE :": "https://www.eppgroup.eu/fr/",
        "France / Renew :": "https://www.reneweuropegroup.eu/fr",
        "France / S&D :": "https://www.socialistsanddemocrats.eu/",
        "France / The Left :": "https://left.eu/",
        "France / Verts/ALE :": "https://www.greens-efa.eu/en/",
        "France / NI :": "https://en.wikipedia.org/wiki/Non-attached_members",
        "France / GUE/NGL :": "https://left.eu/the-group/",
        "France / ALDE :": "https://fr.wikipedia.org/wiki/Groupe_de_l%27Alliance_des_d%C3%A9mocrates_et_des_lib%C3%A9raux_pour_l%27Europe",
        "France / EFDD :": "https://fr.wikipedia.org/wiki/Groupe_Europe_de_la_libert%C3%A9_et_de_la_d%C3%A9mocratie_directe",
        "France / ENF :": "https://fr.wikipedia.org/wiki/Groupe_Europe_des_nations_et_des_libert%C3%A9s",
    }
    return links[group_name] if group_name in links else ""


def group_slug(group_name) -> str:
    """
    :return: identifier of the group in the URLs, for example "verts-ale" for "France / Verts/ALE :". A group which
    changed its name has the identifier of its current name (see RENAMED_GROUPS).
    """
    from server.podiums import RENAMED_GROUPS
    group_name = RENAMED_GROUPS.get(group_name, group_name)
    return re.sub(r"[^a-z0-9]+", "-", group_name.replace("France / ", "")[:-2].lower()).strip("-")


def political_group_logo(group_name) -> dict | None:
    """
    :return: {"url": <URL of the logo>, "brightness": <factor to lighten the logo on the dark theme, 1 if it's readable
    as it is>, "rounded": <the logo is a rounded square, whose corners are white in the file>}, None if the logo is
    unknown. The logos come from Wikimedia Commons (property "logo image" of the groups
    on Wikidata), they are public domain (text logos) but trademarked.
    """
    logos = {
        # Too dark for the dark background: lightened, keeping their colors, to a contrast of at least 4:1
        "France / ECR :": ("ecr.svg", 1.5),
        "France / ESN :": ("esn.svg", 2.5),
        "France / PfE :": ("pfe.svg", 2.5),
        "France / ID :": ("id.svg", 1.8),
        "France / PPE :": ("ppe.svg", 1.5),
        # Readable as they are
        "France / Renew :": ("renew.svg", 1),
        "France / S&D :": ("sd.svg", 1),
        "France / The Left :": ("left.svg", 1),
        "France / Verts/ALE :": ("verts.svg", 1),
        "France / EFDD :": ("efdd.png", 1),
    }
    from server.podiums import RENAMED_GROUPS
    group_name = RENAMED_GROUPS.get(group_name, group_name)
    if group_name not in logos:
        return None
    file, brightness = logos[group_name]
    return {"url": f"/static/groups/{file}", "brightness": brightness, "rounded": group_name == "France / EFDD :"}


def political_group_class(group_name):
    classes = {
        "France / ECR :": "group_ecr",
        "France / ESN :": "group_ens",
        "France / PfE :": "group_pfe",
        "France / ID :": "group_id",
        "France / PPE :": "group_ppe",
        "France / Renew :": "group_renew",
        "France / S&D :": "group_sd",
        "France / The Left :": "group_left",
        "France / Verts/ALE :": "group_verts",
        "France / NI :": "group_ni",
        "France / GUE/NGL :": "group_guengl",
        "France / ALDE :": "group_renew",
        "France / EFDD :": "group_ni",
        "France / ENF :": "group_id",
    }
    return classes[group_name] if group_name in classes else "group_ni"

def political_group_tooltip(group_name, date_1, date_2=None):
    classes = {
        "France / ECR :": "Conservateurs et réformistes européens (droite à extrême droite)",
        "France / ESN :": "L'Europe des nations souveraines (extrême droite)",
        "France / PfE :": "Patriotes pour l'Europe (droite à extrême droite)",
        "France / ID :": "Parti Identité et démocratie (droite radicale à extrême)",
        "France / PPE :": "Groupe du Parti populaire européen (centre droit à droite)",
        "France / Renew :": "Renew Europe (centre)",
        "France / S&D :": "Alliance progressiste des socialistes et démocrates au Parlement européen (gauche à centre gauche)",
        "France / The Left :": "Groupe de la Gauche au Parlement européen (gauche à extrême gauche)",
        "France / Verts/ALE :": "Groupe des Verts/Alliance libre européenne (centre gauche à gauche)",
        "France / NI :": "Non-inscrit au Parlement européen",
        "France / GUE/NGL :": "Groupe de la Gauche au Parlement européen (gauche à extrême gauche)",
        "France / ALDE :": "Alliance des démocrates et des libéraux pour l'Europe (centre)",
        "France / EFDD :": "Europe de la liberté et de la démocratie directe (droite à extrême droite)",
        "France / ENF :": "Europe des nations et des libertés (extrême droite)",
        "Total France :": "Tous les groupes français réunis",
        "Parlement Européen :": "Ensemble du parlement européen"
    }
    group_list = political_group_french_list(group_name, date_1, date_2)
    descr = classes[group_name] if group_name in classes else "Aucune information n'est connue au sujet de ce parti"
    return descr + ("<br/>" if group_list != "" else "") + group_list


def political_group_spectrum(group_name):
    classes = {
        "France / ECR :": 0.85,
        "France / ESN :": 0.95,
        "France / PfE :": 0.9,
        "France / ID :": 0.9,
        "France / PPE :": 0.8,
        "France / Renew :": 0.5,
        "France / S&D :": 0.2,
        "France / The Left :": 0.1,
        "France / Verts/ALE :": 0.3,
        "France / NI :": 1,
        "France / GUE/NGL :": 0.1,
        "France / ALDE :": 0.5,
        "France / EFDD :": 0.9,
        "France / ENF :": 0.95,
        "Parlement Européen :": 3,
        "Total France :": 2,
    }
    return classes[group_name] if group_name in classes else 1

# Heads of the French lists elected in each group, by parliamentary term: {<term>: {<group>: [(<list>, <identifier of
# the head of the list>)]}}. In 2014, France voted in 8 regional constituencies, each list had a head per constituency
# (source: Wikipedia, results of the 2014 European elections in France). The lists of Outre-Mer had one head per section:
# they are not given.
HEADS_OF_LIST = {
    10: {
        "France / PfE :": [("Liste RN", "131580")],  # Jordan Bardella
        "France / ECR :": [("Liste Reconquête", "256922")],  # Marion Maréchal
        "France / ESN :": [("Liste Reconquête", "256922")],
        "France / PPE :": [("Liste LR", "197534")],  # François-Xavier Bellamy
        "France / Renew :": [("Liste Ensemble", "135511")],  # Valérie Hayer
        "France / S&D :": [("Liste PS", "197694")],  # Raphaël Glucksmann
        "France / The Left :": [("Liste LFI", "197533")],  # Manon Aubry
        "France / Verts/ALE :": [("Liste EELV", "97236")],  # Marie Toussaint
    },
    9: {
        "France / ID :": [("Liste RN", "131580")],
        "France / PPE :": [("Liste LR", "197534")],
        "France / Renew :": [("Liste LREM", "197494")],  # Nathalie Loiseau
        "France / S&D :": [("Liste PS", "197694")],
        "France / The Left :": [("Liste LFI", "197533")],
        "France / Verts/ALE :": [("Liste EELV", "96740")],  # Yannick Jadot
    },
    8: {
        "France / ENF :": [
            ("Liste FN · Nord-Ouest", "28210"),  # Marine Le Pen
            ("Liste FN · Ouest", "124738"),  # Gilles Lebreton
            ("Liste FN · Est", "110977"),  # Florian Philippot
            ("Liste FN · Massif central-Centre", "124761"),  # Bernard Monot
            ("Liste FN · Sud-Ouest", "30190"),  # Louis Aliot
            ("Liste FN · Sud-Est", "1023"),  # Jean-Marie Le Pen
            ("Liste FN · Île-de-France", "124752"),  # Aymeric Chauprade
        ],
        "France / PPE :": [
            ("Liste UMP · Nord-Ouest", "124731"),  # Jérôme Lavrilleux
            ("Liste UMP · Ouest", "96849"),  # Alain Cadec
            ("Liste UMP · Est", "72779"),  # Nadine Morano
            ("Liste UMP · Massif central-Centre", "5565"),  # Brice Hortefeux
            ("Liste UMP · Sud-Ouest", "1179"),  # Michèle Alliot-Marie
            ("Liste UMP · Sud-Est", "124729"),  # Renaud Muselier
            ("Liste UMP · Île-de-France", "1204"),  # Alain Lamassoure
        ],
        "France / S&D :": [
            ("Liste PS-PRG · Nord-Ouest", "96948"),  # Gilles Pargneaux
            ("Liste PS-PRG · Ouest", "114279"),  # Isabelle Thomas
            ("Liste PS-PRG · Est", "124947"),  # Édouard Martin
            ("Liste PS-PRG · Massif central-Centre", "94282"),  # Jean-Paul Denanot
            ("Liste PS-PRG · Sud-Ouest", "103845"),  # Virginie Rozière
            ("Liste PS-PRG · Sud-Est", "28166"),  # Vincent Peillon
            ("Liste PS-PRG · Île-de-France", "1985"),  # Pervenche Berès
        ],
        "France / ALDE :": [
            ("Liste UDI-MoDem · Nord-Ouest", "96885"),  # Dominique Riquet
            ("Liste UDI-MoDem · Ouest", "124773"),  # Jean Arthuis
            ("Liste UDI-MoDem · Est", "28208"),  # Nathalie Griesbeck
            ("Liste UDI-MoDem · Sud-Ouest", "97022"),  # Robert Rochefort
            ("Liste UDI-MoDem · Sud-Est", "97137"),  # Sylvie Goulard
            ("Liste UDI-MoDem · Île-de-France", "4335"),  # Marielle de Sarnez
        ],
        "France / Verts/ALE :": [
            ("Liste EELV · Nord-Ouest", "96868"),  # Karima Delli
            ("Liste EELV · Ouest", "96740"),  # Yannick Jadot
            ("Liste EELV · Sud-Ouest", "96744"),  # José Bové
            ("Liste EELV · Sud-Est", "96743"),  # Michèle Rivasi
            ("Liste EELV · Île-de-France", "124693"),  # Pascal Durand
        ],
        "France / GUE/NGL :": [
            ("Liste Front de gauche · Sud-Ouest", "96742"),  # Jean-Luc Mélenchon
            ("Liste Front de gauche · Sud-Est", "96858"),  # Marie-Christine Vergiat
            ("Liste Front de gauche · Île-de-France", "96735"),  # Patrick Le Hyaric
        ],
    },
}


def political_group_french_list(group_name, date_1, date_2 = None):
    classes = {
        10: {
            "France / ECR :": "Liste Reconquête {}(Maréchal)",
            "France / ESN :": "Liste Reconquête {}(Maréchal)",
            "France / PfE :": "Liste RN {}(Bardella)",
            "France / PPE :": "Liste LR {}(Bellamy)",
            "France / Renew :": "Liste Ensemble {}(Hayer)",
            "France / S&D :": "Liste PS {}(Glucksmann)",
            "France / The Left :": "Liste LFI {}(Aubry)",
            "France / Verts/ALE :": "Liste EELV {}(Toussaint)",
            "France / GUE/NGL :": "Liste LFI {}(Aubry)"
        },
        9: {
            "France / ID :": "Liste RN {}(Bardella)",
            "France / PPE :": "Liste LR {}(Bellamy)",
            "France / Renew :": "Liste LREM {}(Loiseau)",
            "France / S&D :": "Liste PS {}(Glucksmann)",
            "France / The Left :": "Liste LFI {}(Manon Aubry)",
            "France / Verts/ALE :": "Liste EELV {}(Jadot)",
            "France / GUE/NGL :": "Liste LFI {}(Manon Aubry)"
        },
        8: {
            "France / ENF :": "Liste FN {}",
            "France / PPE :": "Liste UMP {}",
            "France / ALDE :": "Liste UDI-MoDem {}",
            "France / S&D :": "Liste PS {}",
            "France / Verts/ALE :": "Liste EELV {}",
            "France / GUE/NGL :": "Liste Front de gauche {}",
        }
    }

    if date_2 is None:
        nb = parliament_number_from_date(date_1)
        if nb not in classes:
            return ""
        return classes[nb][group_name].replace("{}", "").strip() if group_name in classes[nb] else ""

    def name_from_nb(nb):
        if group_name in classes[nb]:
            return classes[nb][group_name].replace("{}", f"{year_from_parliament_number(nb)} ").strip()
        return ""

    nb1 = parliament_number_from_date(date_1)
    nb2 = parliament_number_from_date(date_2)
    names = [name_from_nb(nb) for nb in range(nb1, nb2 + 1) if nb in classes]
    return ", ".join(filter(lambda x: x != "", names))


def class_from_vote_result(result):
    classes = {"+": "voted_for", "-": "voted_against", "0": "abstained", "absent": "absent"}
    return classes[result] if result in classes else "abstained"


def filter_political_group(group_name):
    group_name = group_name.replace("France / ", "")
    group_name = group_name[:-2]
    group_name = (group_name
                  .replace("The Left", "La Gauche")
                  .replace("Verts/ALE", "Les&nbsp;Verts")
                  .replace("Total France", "🇫🇷")
                  .replace("Parlement Européen", "🇪🇺"))
    return group_name

def is_last_iterator(iterator):
    for i, item in enumerate(iterator):
        yield i == len(iterator) - 1, item

def is_first_iterator(iterator):
    for i, item in enumerate(iterator):
        yield i == 0, item

def to_pretty_date(date):
    return format_date(datetime.date.fromisoformat(date), format='long', locale='fr')

def count_all_votes(data):
    """
    Get the number of votes for a specific result (+, -, 0)
    """
    return sum([len(data[x]) for x in data])

def set_page(data: dict, page):
    new = data.copy()
    new["page"] = page
    return new

def set_search(data: dict, search):
    new = data.copy()
    new["search"] = search
    return new

def page_range(size, current_page):
    pages_number = size // 25 + (1 if size % 25 != 0 else 0) + 1
    if pages_number <= 5:
        return list(range(1, pages_number))
    if current_page <= 3:
        return [1, 2, 3, 4, -1, pages_number - 1]

    if current_page > pages_number - 4:
        return [1, -1, pages_number - 4, pages_number - 3, pages_number - 2, pages_number - 1]

    return [1, -1, current_page - 1, current_page, current_page + 1, -1, pages_number - 1]

def create_flags_keywords():
    flags_keywords_ = {
            "🇦🇫": ["Afghanistan", "Afghan", "Afghans", "Afghane", "Afghanes", "Kaboul", "Herat"],
            "🇦🇱": ["Albanie", "Albanais", "Albanais", "Albanaise", "Albanaises", "Tirana", "Durrës"],
            "🇩🇿": ["Algérie", "Algérien", "Algériens", "Algérienne", "Algériennes", "Alger", "Oran"],
            "🇦🇩": ["Andorre", "Andorran", "Andorrans", "Andorrane", "Andorranes", "Andorre-la-Vieille", "Escaldes-Engordany"],
            "🇦🇴": ["Angola", "Angolais", "Angolais", "Angolaise", "Angolaises", "Luanda", "Huambo"],
            "🇦🇬": ["Antigua-et-Barbuda", "Antiguais", "Antiguais", "Antiguaise", "Antiguaises", "Saint John's", "Codrington"],
            "🇦🇷": ["Argentine", "Argentin", "Argentins", "Argentine", "Argentines", "Buenos Aires", "Córdoba"],
            "🇦🇲": ["Arménie", "Arménien", "Arméniens", "Arménienne", "Arméniennes", "Erevan", "Gyumri"],
            "🇦🇺": ["Australie", "Australien", "Australiens", "Australienne", "Australiennes", "Canberra", "Sydney"],
            "🇦🇹": ["Autriche", "Autrichien", "Autrichiens", "Autrichienne", "Autrichiennes", "Vienne", "Graz"],
            "🇦🇿": ["Azerbaïdjan", "Azerbaïdjanais", "Azerbaïdjanais", "Azerbaïdjanaise", "Azerbaïdjanaises", "Bakou", "Gandja"],
            "🇧🇸": ["Bahamas", "Bahamien", "Bahamiens", "Bahamienne", "Bahamiennes", "Nassau", "Freeport"],
            "🇧🇭": ["Bahreïn", "Bahreïnien", "Bahreïniens", "Bahreïnienne", "Bahreïniennes", "Manama", "Muharraq"],
            "🇧🇩": ["Bangladesh", "Bangladais", "Bangladais", "Bangladaise", "Bangladaises", "Dacca", "Chittagong"],
            "🇧🇧": ["Barbade", "Barbadien", "Barbadiens", "Barbadienne", "Barbadiennes", "Bridgetown", "Speightstown"],
            "🇧🇾": ["Biélorussie", "Biélorusse", "Biélorusses", "Biélorusse", "Biélorusses", "Minsk", "Gomel"],
            "🇧🇪": ["Belgique", "Belge", "Belges", "Belge", "Belges", "Bruxelles", "Anvers"],
            "🇧🇿": ["Belize", "Bélizien", "Béliziens", "Bélizienne", "Béliziennes", "Belmopan", "Belize City"],
            "🇧🇯": ["Bénin", "Béninois", "Béninois", "Béninoise", "Béninoises", "Porto-Novo", "Cotonou"],
            "🇧🇹": ["Bhoutan", "Bhoutanais", "Bhoutanais", "Bhoutanaise", "Bhoutanaises", "Thimphou", "Phuentsholing"],
            "🇧🇴": ["Bolivie", "Bolivien", "Boliviens", "Bolivienne", "Boliviennes", "Sucre", "La Paz"],
            "🇧🇦": ["Bosnie-Herzégovine", "Bosniaque", "Bosniaques", "Bosniaque", "Bosniaques", "Sarajevo", "Banja Luka"],
            "🇧🇼": ["Botswana", "Botswanais", "Botswanais", "Botswanaise", "Botswanaises", "Gaborone", "Francistown"],
            "🇧🇷": ["Brésil", "Brésilien", "Brésiliens", "Brésilienne", "Brésiliennes", "Brasilia", "São Paulo"],
            "🇧🇳": ["Brunei", "Brunéien", "Brunéiens", "Brunéienne", "Brunéiennes", "Bandar Seri Begawan", "Kuala Belait"],
            "🇧🇬": ["Bulgarie", "Bulgare", "Bulgare", "Bulgare", "Bulgares", "Sofia", "Plovdiv"],
            "🇧🇫": ["Burkina Faso", "Burkinabè", "Burkinabè", "Burkinabè", "Burkinabè", "Ouagadougou", "Bobo-Dioulasso"],
            "🇧🇮": ["Burundi", "Burundais", "Burundais", "Burundaise", "Burundaises", "Gitega", "Bujumbura"],
            "🇨🇻": ["Cap-Vert", "Cap-Verdien", "Cap-Verdiens", "Cap-Verdienne", "Cap-Verdiennes", "Praia", "Mindelo"],
            "🇰🇭": ["Cambodge", "Cambodgien", "Cambodgiens", "Cambodgienne", "Cambodgiennes", "Phnom Penh", "Siem Reap"],
            "🇨🇲": ["Cameroun", "Camerounais", "Camerounais", "Camerounaise", "Camerounaises", "Yaoundé", "Douala"],
            "🇨🇦": ["Canada", "Canadien", "Canadiens", "Canadienne", "Canadiennes", "Ottawa", "Toronto"],
            "🇨🇫": ["République Centrafricaine", "Centrafricain", "Centrafricains", "Centrafricaine", "Centrafricaines", "Bangui", "Bimbo"],
            "🇹🇩": ["Tchad", "Tchadien", "Tchadiens", "Tchadienne", "Tchadiennes", "N'Djaména", "Moundou"],
            "🇨🇱": ["Chili", "Chilien", "Chiliens", "Chilienne", "Chiliennes", "Santiago", "Valparaíso"],
            "🇨🇳": ["Chine", "Chinois", "Chinois", "Chinoise", "Chinoises", "Pékin", "Shanghai"],
            "🇨🇴": ["Colombie", "Colombien", "Colombiens", "Colombienne", "Colombiennes", "Bogota", "Medellín"],
            "🇰🇲": ["Comores", "Comorien", "Comoriens", "Comorienne", "Comoriennes", "Moroni", "Mutsamudu"],
            "🇨🇬": ["République du Congo", "Congolais", "Congolais", "Congolaise", "Congolaises", "Brazzaville", "Pointe-Noire"],
            "🇨🇩": ["République Démocratique du Congo", "Congolais", "Congolais", "Congolaise", "Congolaises", "Kinshasa", "Lubumbashi"],
            "🇨🇷": ["Costa Rica", "Costaricien", "Costariciens", "Costaricienne", "Costariciennes", "San José", "Alajuela"],
            "🇭🇷": ["Croatie", "Croate", "Croates", "Croate", "Croates", "Zagreb", "Split"],
            "🇨🇺": ["Cuba", "Cubain", "Cubains", "Cubaine", "Cubaines", "La Havane", "Santiago de Cuba"],
            "🇨🇾": ["Chypre", "Chypriote", "Chypriotes", "Chypriote", "Chypriotes", "Nicosie", "Limassol"],
            "🇨🇿": ["République Tchèque", "Tchèque", "Tchèques", "Tchèque", "Tchèques", "Prague", "Brno"],
            "🇩🇰": ["Danemark", "Danois", "Danois", "Danoise", "Danoises", "Copenhague", "Aarhus"],
            "🇩🇯": ["Djibouti", "Djiboutien", "Djiboutiens", "Djiboutienne", "Djiboutiennes", "Djibouti", "Ali Sabieh"],
            "🇩🇲": ["Dominique", "Dominiquais", "Dominiquais", "Dominiquaise", "Dominiquaises", "Roseau", "Portsmouth"],
            "🇩🇴": ["République Dominicaine", "Dominicain", "Dominicains", "Dominicaine", "Dominicaines", "Saint-Domingue", "Santiago"],
            "🇪🇨": ["Équateur", "Équatorien", "Équatoriens", "Équatorienne", "Équatoriennes", "Quito", "Guayaquil"],
            "🇪🇬": ["Égypte", "Égyptien", "Égyptiens", "Égyptienne", "Égyptiennes", "Le Caire", "Alexandrie"],
            "🇸🇻": ["El Salvador", "Salvadorien", "Salvadoriens", "Salvadorienne", "Salvadoriennes", "San Salvador", "Santa Ana"],
            "🇬🇶": ["Guinée Équatoriale", "Équatoguinéen", "Équatoguinéens", "Équatoguinéenne", "Équatoguinéennes", "Malabo", "Bata"],
            "🇪🇷": ["Érythrée", "Érythréen", "Érythréens", "Érythréenne", "Érythréennes", "Asmara", "Massawa"],
            "🇪🇪": ["Estonie", "Estonien", "Estoniens", "Estonienne", "Estoniennes", "Tallinn", "Tartu"],
            "🇪🇹": ["Éthiopie", "Éthiopien", "Éthiopiens", "Éthiopienne", "Éthiopiennes", "Addis-Abeba", "Gondar"],
            "🇫🇯": ["Fidji", "Fidjien", "Fidjiens", "Fidjienne", "Fidjiennes", "Suva", "Nadi"],
            "🇫🇮": ["Finlande", "Finlandais", "Finlandais", "Finlandaise", "Finlandaises", "Helsinki", "Espoo"],
            "🇫🇷": ["France", "Français", "Français", "Française", "Françaises", "Paris", "Marseille"],
            "🇬🇦": ["Gabon", "Gabonais", "Gabonais", "Gabonaise", "Gabonaises", "Libreville", "Port-Gentil"],
            "🇬🇲": ["Gambie", "Gambien", "Gambiens", "Gambienne", "Gambiennes", "Banjul", "Serrekunda"],
            "🇬🇪": ["Géorgie", "Géorgien", "Géorgiens", "Géorgienne", "Géorgiennes", "Tbilissi", "Batoumi"],
            "🇩🇪": ["Allemagne", "Allemand", "Allemands", "Allemande", "Allemandes", "Berlin", "Munich"],
            "🇬🇭": ["Ghana", "Ghanéen", "Ghanéens", "Ghanéenne", "Ghanéennes", "Accra", "Kumasi"],
            "🇬🇷": ["Grèce", "Grec", "Grecs", "Grecque", "Grecques", "Athènes", "Thessalonique"],
            "🇬🇩": ["Grenade", "Grenadien", "Grenadiens", "Grenadienne", "Grenadiennes", "Saint-Georges", "Gouyave"],
            "🇬🇹": ["Guatemala", "Guatémaltèque", "Guatémaltèques", "Guatémaltèque", "Guatémaltèques", "Guatemala", "Mixco"],
            "🇬🇳": ["Guinée", "Guinéen", "Guinéens", "Guinéenne", "Guinéennes", "Conakry", "Nzérékoré"],
            "🇬🇼": ["Guinée-Bissau", "Bissaoguinéen", "Bissaoguinéens", "Bissaoguinéenne", "Bissaoguinéennes", "Bissau", "Gabú"],
            "🇬🇾": ["Guyana", "Guyanien", "Guyaniens", "Guyanienne", "Guyaniennes", "Georgetown", "Linden"],
            "🇭🇹": ["Haïti", "Haïtien", "Haïtiens", "Haïtienne", "Haïtiennes", "Port-au-Prince", "Cap-Haïtien"],
            "🇭🇳": ["Honduras", "Hondurien", "Honduriens", "Hondurienne", "Honduriennes", "Tegucigalpa", "San Pedro Sula"],
            "🇭🇺": ["Hongrie", "Hongrois", "Hongrois", "Hongroise", "Hongroises", "Budapest", "Debrecen"],
            "🇮🇸": ["Islande", "Islandais", "Islandais", "Islandaise", "Islandaises", "Reykjavik", "Kópavogur"],
            "🇮🇳": ["Inde", "Indien", "Indiens", "Indienne", "Indiennes", "New Delhi", "Mumbai"],
            "🇮🇩": ["Indonésie", "Indonésien", "Indonésiens", "Indonésienne", "Indonésiennes", "Jakarta", "Surabaya"],
            "🇮🇷": ["Iran", "Iranien", "Iraniens", "Iranienne", "Iraniennes", "Téhéran", "Ispahan"],
            "🇮🇶": ["Iraq", "Irak", "Irakien", "Irakiens", "Irakienne", "Irakiennes", "Bagdad", "Bassorah"],
            "🇮🇪": ["Irlande", "Irlandais", "Irlandais", "Irlandaise", "Irlandaises", "Dublin", "Cork"],
            "🇮🇱": ["Israël", "Israélien", "Israéliens", "Israélienne", "Israéliennes", "Jérusalem", "Tel Aviv"],
            "🇮🇹": ["Italie", "Italien", "Italiens", "Italienne", "Italiennes", "Rome", "Milan"],
            "🇯🇲": ["Jamaïque", "Jamaïcain", "Jamaïcains", "Jamaïcaine", "Jamaïcaines", "Kingston", "Montego Bay"],
            "🇯🇵": ["Japon", "Japonais", "Japonais", "Japonaise", "Japonaises", "Tokyo", "Osaka"],
            "🇯🇴": ["Jordanie", "Jordanien", "Jordaniens", "Jordanienne", "Jordaniennes", "Amman", "Aqaba"],
            "🇰🇿": ["Kazakhstan", "Kazakh", "Kazakhs", "Kazakhe", "Kazakhes", "Astana", "Almaty"],
            "🇰🇪": ["Kenya", "Kenyan", "Kenyans", "Kenyane", "Kenyanes", "Nairobi", "Mombasa"],
            "🇰🇮": ["Kiribati", "Kiribatien", "Kiribatiens", "Kiribatienne", "Kiribatiennes", "Tarawa", "Bairiki"],
            "🇰🇼": ["Koweït", "Koweïtien", "Koweïtiens", "Koweïtienne", "Koweïtiennes", "Koweït", "Al Jahra"],
            "🇰🇬": ["Kirghizistan", "Kirghiz", "Kirghiz", "Kirghize", "Kirghizes", "Bichkek", "Och"],
            "🇱🇦": ["Laos", "Laotien", "Laotiens", "Laotienne", "Laotiennes", "Vientiane", "Luang Prabang"],
            "🇱🇻": ["Lettonie", "Letton", "Lettons", "Lettone", "Lettones", "Riga", "Daugavpils"],
            "🇱🇧": ["Liban", "Libanais", "Libanais", "Libanaise", "Libanaises", "Beyrouth", "Tripoli"],
            "🇱🇸": ["Lesotho", "Lésothan", "Lésothans", "Lésothane", "Lésothanes", "Maseru", "Mafeteng"],
            "🇱🇷": ["Liberia", "Libérien", "Libériens", "Libérienne", "Libériennes", "Monrovia", "Gbarnga"],
            "🇱🇾": ["Libye", "Libyen", "Libyens", "Libyenne", "Libyennes", "Tripoli", "Benghazi"],
            "🇱🇮": ["Liechtenstein", "Liechtensteinois", "Liechtensteinois", "Liechtensteinoise", "Liechtensteinoises", "Vaduz", "Schaan"],
            "🇱🇹": ["Lituanie", "Lituanien", "Lituaniens", "Lituanienne", "Lituaniennes", "Vilnius", "Kaunas"],
            "🇱🇺": ["Luxembourg", "Luxembourgeois", "Luxembourgeois", "Luxembourgeoise", "Luxembourgeoises", "Luxembourg", "Esch-sur-Alzette"],
            "🇲🇰": ["Macédoine du Nord", "Macédonien", "Macédoniens", "Macédonienne", "Macédoniennes", "Skopje", "Bitola"],
            "🇲🇬": ["Madagascar", "Malgache", "Malgaches", "Malgache", "Malgaches", "Antananarivo", "Toamasina"],
            "🇲🇼": ["Malawi", "Malawien", "Malawiens", "Malawienne", "Malawiennes", "Lilongwe", "Blantyre"],
            "🇲🇾": ["Malaisie", "Malaisien", "Malaisiens", "Malaisienne", "Malaisiennes", "Kuala Lumpur", "George Town"],
            "🇲🇻": ["Maldives", "Maldivien", "Maldiviens", "Maldivienne", "Maldiviennes", "Malé", "Addu City"],
            "🇲🇱": ["Mali", "Malien", "Maliens", "Malienne", "Maliennes", "Bamako", "Sikasso"],
            "🇲🇹": ["Malte", "Maltais", "Maltais", "Maltaise", "Maltaises", "La Valette", "Birkirkara"],
            "🇲🇭": ["Îles Marshall", "Marshallais", "Marshallais", "Marshallaise", "Marshallaises", "Majuro", "Ebeye"],
            "🇲🇷": ["Mauritanie", "Mauritanien", "Mauritaniens", "Mauritanienne", "Mauritaniennes", "Nouakchott", "Nouadhibou"],
            "🇲🇺": ["Maurice", "Mauricien", "Mauriciens", "Mauricienne", "Mauriciennes", "Port-Louis", "Curepipe"],
            "🇲🇽": ["Mexique", "Mexicain", "Mexicains", "Mexicaine", "Mexicaines", "Mexico", "Guadalajara"],
            "🇫🇲": ["Micronésie", "Micronésien", "Micronésiens", "Micronésienne", "Micronésiennes", "Palikir", "Weno"],
            "🇲🇩": ["Moldavie", "Moldave", "Moldaves", "Moldave", "Moldaves", "Chisinau", "Tiraspol"],
            "🇲🇨": ["Monaco", "Monégasque", "Monégasques", "Monégasque", "Monégasques", "Monaco", "Monte-Carlo"],
            "🇲🇳": ["Mongolie", "Mongol", "Mongols", "Mongole", "Mongoles", "Oulan-Bator", "Erdenet"],
            "🇲🇪": ["Monténégro", "Monténégrin", "Monténégrins", "Monténégrine", "Monténégrines", "Podgorica", "Nikšić"],
            "🇲🇦": ["Maroc", "Marocain", "Marocains", "Marocaine", "Marocaines", "Rabat", "Casablanca"],
            "🇲🇿": ["Mozambique", "Mozambicain", "Mozambicains", "Mozambicaine", "Mozambicaines", "Maputo", "Beira"],
            "🇲🇲": ["Birmanie", "Birman", "Birmans", "Birmane", "Birmanes", "Naypyidaw", "Yangon"],
            "🇳🇦": ["Namibie", "Namibien", "Namibiens", "Namibienne", "Namibiennes", "Windhoek", "Walvis Bay"],
            "🇳🇷": ["Nauru", "Nauruan", "Nauruans", "Nauruane", "Nauruanes", "Yaren", "Meneng"],
            "🇳🇵": ["Népal", "Népalais", "Népalais", "Népalaise", "Népalaises", "Katmandou", "Pokhara"],
            "🇳🇱": ["Pays-Bas", "Néerlandais", "Néerlandais", "Néerlandaise", "Néerlandaises", "Amsterdam", "Rotterdam"],
            "🇳🇿": ["Nouvelle-Zélande", "Néo-Zélandais", "Néo-Zélandais", "Néo-Zélandaise", "Néo-Zélandaises", "Wellington", "Auckland"],
            "🇳🇮": ["Nicaragua", "Nicaraguayen", "Nicaraguayens", "Nicaraguayenne", "Nicaraguayennes", "Managua", "León"],
            "🇳🇪": ["Niger", "Nigérien", "Nigériens", "Nigérienne", "Nigériennes", "Niamey", "Zinder"],
            "🇳🇬": ["Nigeria", "Nigérian", "Nigérians", "Nigériane", "Nigérianes", "Abuja", "Lagos"],
            "🇰🇵": ["Corée du Nord", "Nord-Coréen", "Nord-Coréens", "Nord-Coréenne", "Nord-Coréennes", "Pyongyang", "Kaesong"],
            "🇳🇴": ["Norvège", "Norvégien", "Norvégiens", "Norvégienne", "Norvégiennes", "Oslo", "Bergen"],
            "🇴🇲": ["Oman", "Omanais", "Omanais", "Omanienne", "Omaniennes", "Mascate", "Salalah"],
            "🇵🇰": ["Pakistan", "Pakistanais", "Pakistanais", "Pakistanaise", "Pakistanaises", "Islamabad", "Karachi"],
            "🇵🇼": ["Palaos", "Paluan", "Paluans", "Paluanne", "Paluanes", "Ngerulmud", "Koror"],
            "🇵🇦": ["Panama", "Panaméen", "Panaméens", "Panaméenne", "Panaméennes", "Panama", "Colón"],
            "🇵🇬": ["Papouasie-Nouvelle-Guinée", "Papouasien", "Papouasiens", "Papouasienne", "Papouasiennes", "Port Moresby", "Lae"],
            "🇵🇾": ["Paraguay", "Paraguayen", "Paraguayens", "Paraguayenne", "Paraguayennes", "Asunción", "Ciudad del Este"],
            "🇵🇪": ["Pérou", "Péruvien", "Péruviens", "Péruvienne", "Péruviennes", "Lima", "Arequipa"],
            "🇵🇭": ["Philippines", "Philippin", "Philippins", "Philippine", "Philippines", "Manille", "Cebu"],
            "🇵🇱": ["Pologne", "Polonais", "Polonais", "Polonaise", "Polonaises", "Varsovie", "Cracovie"],
            "🇵🇹": ["Portugal", "Portugais", "Portugais", "Portugaise", "Portugaises", "Lisbonne", "Porto"],
            "🇶🇦": ["Qatar", "Qatarien", "Qatariens", "Qatarienne", "Qatariennes", "Doha", "Al Wakrah"],
            "🇰🇷": ["Corée du Sud", "Sud-Coréen", "Sud-Coréens", "Sud-Coréenne", "Sud-Coréennes", "Séoul", "Busan"],
            "🇷🇴": ["Roumanie", "Roumain", "Roumains", "Roumaine", "Roumaines", "Bucarest", "Cluj-Napoca"],
            "🇷🇺": ["Russie", "Russe", "Russes", "Russe", "Russes", "Moscou", "Saint-Pétersbourg"],
            "🇷🇼": ["Rwanda", "Rwandais", "Rwandais", "Rwandaise", "Rwandaises", "Kigali", "Butare"],
            "🇼🇸": ["Samoa", "Samoan", "Samoans", "Samoane", "Samoanes", "Apia", "Faleasiu"],
            "🇸🇲": ["Saint-Marin", "Saint-Marinais", "Saint-Marinais", "Saint-Marinaise", "Saint-Marinaises", "Saint-Marin", "Serravalle"],
            "🇸🇹": ["Sao Tomé-et-Principe", "Santoméen", "Santoméens", "Santoméenne", "Santoméennes", "Sao Tomé", "Santo Antonio"],
            "🇸🇳": ["Sénégal", "Sénégalais", "Sénégalais", "Sénégalaise", "Sénégalaises", "Dakar", "Saint-Louis"],
            "🇷🇸": ["Serbie", "Serbe", "Serbes", "Serbe", "Serbes", "Belgrade", "Novi Sad"],
            "🇸🇨": ["Seychelles", "Seychellois", "Seychellois", "Seychelloise", "Seychelloises", "Victoria", "Beau Vallon"],
            "🇸🇱": ["Sierra Leone", "Sierra-Léonais", "Sierra-Léonais", "Sierra-Léonaise", "Sierra-Léonaises", "Freetown", "Bo"],
            "🇸🇬": ["Singapour", "Singapourien", "Singapouriens", "Singapourienne", "Singapouriennes", "Singapour", "Jurong"],
            "🇸🇰": ["Slovaquie", "Slovaque", "Slovaques", "Slovaque", "Slovaques", "Bratislava", "Košice"],
            "🇸🇮": ["Slovénie", "Slovène", "Slovènes", "Slovène", "Slovènes", "Ljubljana", "Maribor"],
            "🇸🇧": ["Salomon", "Salomonien", "Salomoniens", "Salomonienne", "Salomoniennes", "Honiara", "Auki"],
            "🇸🇴": ["Somalie", "Somalien", "Somaliens", "Somalienne", "Somaliennes", "Mogadiscio", "Hargeisa"],
            "🇿🇦": ["Afrique du Sud", "Sud-Africain", "Sud-Africains", "Sud-Africaine", "Sud-Africaines", "Pretoria", "Johannesbourg"],
            "🇸🇸": ["Soudan du Sud", "Sud-Soudanais", "Sud-Soudanais", "Sud-Soudanaise", "Sud-Soudanaises", "Djouba", "Malakal"],
            "🇪🇸": ["Espagne", "Espagnol", "Espagnols", "Espagnole", "Espagnoles", "Madrid", "Barcelone"],
            "🇱🇰": ["Sri Lanka", "Sri-Lankais", "Sri-Lankais", "Sri-Lankaise", "Sri-Lankaises", "Colombo", "Kandy"],
            "🇸🇩": ["Soudan", "Soudanais", "Soudanais", "Soudanaise", "Soudanaises", "Khartoum", "Omdourman"],
            "🇸🇷": ["Suriname", "Surinamien", "Surinamiens", "Surinamienne", "Surinamiennes", "Paramaribo", "Lelydorp"],
            "🇸🇿": ["Eswatini", "Swazi", "Swazis", "Swazie", "Swazies", "Mbabane", "Manzini"],
            "🇸🇪": ["Suède", "Suédois", "Suédois", "Suédoise", "Suédoises", "Stockholm", "Göteborg"],
            "🇨🇭": ["Suisse", "Suisse", "Suisses", "Suisse", "Suisses", "Berne", "Zurich"],
            "🇸🇾": ["Syrie", "Syrien", "Syriens", "Syrienne", "Syriennes", "Damas", "Alep"],
            "🇹🇼": ["Taïwan", "Taïwanais", "Taïwanais", "Taïwanaise", "Taïwanaises", "Taipei", "Kaohsiung"],
            "🇹🇯": ["Tadjikistan", "Tadjik", "Tadjiks", "Tadjike", "Tadjikes", "Douchanbé", "Khodjent"],
            "🇹🇿": ["Tanzanie", "Tanzanien", "Tanzaniens", "Tanzanienne", "Tanzaniennes", "Dodoma", "Dar es Salam"],
            "🇹🇭": ["Thaïlande", "Thaïlandais", "Thaïlandais", "Thaïlandaise", "Thaïlandaises", "Bangkok", "Chiang Mai"],
            "🇹🇱": ["Timor oriental", "Est-Timorais", "Est-Timorais", "Est-Timoraise", "Est-Timoraises", "Dili", "Baucau"],
            "🇹🇬": ["Togo", "Togolais", "Togolais", "Togolaise", "Togolaises", "Lomé", "Sokodé"],
            "🇹🇴": ["Tonga", "Tongien", "Tongiens", "Tongienne", "Tongiennes", "Nuku'alofa", "Neiafu"],
            "🇹🇹": ["Trinité-et-Tobago", "Trinidadien", "Trinidadiens", "Trinidadienne", "Trinidadiennes", "Port-d'Espagne", "San Fernando"],
            "🇹🇳": ["Tunisie", "Tunisien", "Tunisiens", "Tunisienne", "Tunisiennes", "Tunis", "Sfax"],
            "🇹🇷": ["Turquie", "Turc", "Turcs", "Turque", "Turques", "Ankara", "Istanbul"],
            "🇹🇲": ["Turkménistan", "Turkmène", "Turkmènes", "Turkmène", "Turkmènes", "Achgabat", "Turkmenabat"],
            "🇹🇻": ["Tuvalu", "Tuvaluan", "Tuvaluans", "Tuvaluane", "Tuvaluanes", "Funafuti", "Vaiaku"],
            "🇺🇬": ["Ouganda", "Ougandais", "Ougandais", "Ougandaise", "Ougandaises", "Kampala", "Gulu"],
            "🇺🇦": ["Ukraine", "Ukrainien", "Ukrainiens", "Ukrainienne", "Ukrainiennes", "Kiev", "Kharkiv"],
            "🇦🇪": ["Émirats arabes unis", "Émirien", "Émiriens", "Émirienne", "Émiriennes", "Abou Dhabi", "Dubaï"],
            "🇬🇧": ["Royaume-Uni", "Britannique", "Britanniques", "Britannique", "Britanniques", "Londres", "Manchester"],
            "🇺🇸": ["États-Unis", "Américain", "Américains", "Américaine", "Américaines", "Washington D.C.", "New York"],
            "🇺🇾": ["Uruguay", "Uruguayen", "Uruguayens", "Uruguayenne", "Uruguayennes", "Montevideo", "Salto"],
            "🇺🇿": ["Ouzbékistan", "Ouzbek", "Ouzbeks", "Ouzbèke", "Ouzbèkes", "Tachkent", "Samarcande"],
            "🇻🇺": ["Vanuatu", "Vanuatuan", "Vanuatuans", "Vanuatuan", "Vanuatuannes", "Port-Vila", "Luganville"],
            "🇻🇦": ["Vatican", "Vatican", "Vaticans", "Vaticane", "Vaticanes", "Vatican"],
            "🇻🇪": ["Venezuela", "Vénézuélien", "Vénézuéliens", "Vénézuélienne", "Vénézuéliennes", "Caracas", "Maracaibo"],
            "🇻🇳": ["Vietnam", "Viêt Nam", "Vietnamien", "Vietnamiens", "Vietnamienne", "Vietnamiennes", "Hanoï", "Hô-Chi-Minh-Ville"],
            "🇾🇪": ["Yémen", "Yéménite", "Yéménites", "Yéménite", "Yéménites", "Sanaa", "Aden"],
            "🇿🇲": ["Zambie", "Zambien", "Zambiens", "Zambienne", "Zambiennes", "Lusaka", "Kitwe"],
            "🇿🇼": ["Zimbabwe", "Zimbabwéen", "Zimbabwéens", "Zimbabwéenne", "Zimbabwéennes", "Harare", "Bulawayo"],
            "🇵🇸": ["Palestine", "Palestinien", "Palestiniens", "Palestinienne", "Palestiniennes", "Ramallah", "Gaza"],
            "🇭🇰": ["Hong Kong", "Hongkongais", "Hongkongais", "Hongkongaise", "Hongkongaises", "Hong Kong", "Kowloon"],
            "🇲🇴": ["Macao", "Macanais", "Macanais", "Macanaise", "Macanaises", "Macao", "Taipa"],
            "🇽🇰": ["Kosovo", "Kosovar", "Kosovars", "Kosovare", "Kosovares", "Pristina", "Mitrovica"],
            "🇪🇭": ["Sahara occidental", "Sahraoui", "Sahraouis", "Sahraouie", "Sahraouies", "El-Aaiun", "Dakhla"],
            "🏳️‍🌈": ["LGBT", "LGBTI", "LGBTI+", "LGBTIQ", "LGBTIQ+", "LGBTQI", "LGBTQI+", "LGBTQIA+", "homosexuel", "homosexuels", "homosexuelle", "homosexuelles", "transsexuel", "transsexuels"]
        }

    for flag, keywords in flags_keywords_.items():
        flags_keywords_[flag] = re.compile(r"(?:\W|^)(" + "|".join([re.escape(keyword) for keyword in keywords]) + r")(?:\W|$)", flags=re.IGNORECASE)
    return flags_keywords_

flags_keywords = create_flags_keywords()

def add_flags(title):
    flags = []
    for flag, keywords in flags_keywords.items():
        if re.search(keywords, title):
            flags.append(flag)
    return " ".join(flags) + " "

def create_emojis_keywords():
    emoji_keywords_ = {
        "🌱": ["agriculture", "agricultures", "agricole", "agricoles"],
        "🧬": ["génétiquement", "OGM", "génétique", "gène", "gènes", "génétiques"],
        "🌽": ["maïs"],
        "🌾": ["blé", "blés"],
        "🦠": ["virus", "covid-19", "bactérie", "bactéries", "pandémie", "maladie", "maladies"],
        "💉": ["vaccin", "vaccins", "vaccination", "vaccinations"],
        "☢️": ["atomique", "nucléaire", "atomiques", "nucléaires", "iter"],
        "♀️": ["femmes", "féminicide", "violences conjugales", "féminisme", "féministe", "féministes", "avortement", "avortements", "avorter", "viol", "harcèlement sexuel", "sexiste", "sexisme"],
        "💣": ["terrorisme", "terroriste", "terroristes", "terrorismes"],
        "💥": ["attaque", "guerre", "guerres", "conflit", "conflits", "invasion", "armé", "armés", "armées", "armée", "arme", "armement", "armes", "missile", "missiles", "militaire", "militaires", "bombardement", "bombardements", "bombe", "bombes"],
        "☠️": ["génocide", "génocides", "crime de guerre", "crimes de guerre", "crime contre l'humanité", "crime", "crimes", "criminalité"],
        "🍗": ["viande", "viandes", "volaille", "boeuf", "produits animaux", "origine animale"],
        "🐟": ["poisson", "poissons", "crustacé", "crustacés", "fruits de mer", "saumon", "saumons", "colin", "colins"],
        "🌳": ["environnement", "environnementale", "environnementales", "environnemental", "environnementaux", "forêt", "forêts", "forestiers", "forestier", "forestières", "forestière", "pollution", "pollutions", "polluants", "durable", "renouvelable", "renouvelables", "carbone", "hydrogène", "biogaz", "biocarburant", "biocarburants", "propre", "propres"],
        "🔥": ["incendie", "incendies"],
        "🌊": ["tsunami", "tsunamis", "raz-de-marée", "inondation", "inondations"],
        "🌋": ["volcan", "volcans", "volcanique", "volcaniques"],
        "🌡️": ["climatique", "climatiques", "effet de serre"],
        "💡": ["énergie", "énergies", "électricité"],
        "🖥️": ["cybersécurité", "cyberattaque", "cyberdéfense", "malware", "piratage", "données à caractère personnel", "protection des données", "numérique", "numériques"],
        "🛰️": ["satellites", "satellite", "gps", "galileo", "starlink"],
        "🚀": ["fusée", "spatial", "spatiale", "ESA"],
        "🧪": ["limites maximales applicables aux résidus", "chimiques", "chimique", "substances actives"],
        "🏥": ["médicaments", "médicament", "santé", "hôpital", "hôpitaux", "médecins", "médecin", "personnel médical", "sécurité sociale"],
        "🫧": ["hygiène"],
        "💶": ["monnaie", "monnaies", "euros", "budget", "budgets", "économie", "économies", "économique", "économiques","dépôts", "banque", "banques", "taux d'intérêt", "financement", "coûts", "coût", "dépenses", "recettes", "capitaux", "capital"],
        "🚗": ["routier", "routière", "routiers", "routières", "voiture", "voitures", "camions", "camion"],
        "✈️": ["aviation", "avion", "aéro", "aérienne", "aérien", "aériens", "aériennes"],
        "🚅": ["train", "ferroviaire", "ferroviaires", "chemin de fer", "chemins de fer"],
        "🛥️": ["maritime", "bateau", "bateaux", "maritimes", "voie navigable", "voies navigables"],
        "🚌": ["autobus", "autocar", "bus", "bus", "transport en commun", "transports en commun"],
        "⚽": ["sport", "sports", "activité physique", "activités physiques", "football", "FIFA", "UEFA"],
        "🎣": ["pêche", "pêches", "pêcherie", "pêcheries"],
        "🌍": ["frontière", "frontières", "mondialisation", "libre-échange", "transfrontalier", "transfrontaliers", "transfrontalières", "transfrontalière", "transfrontière", "transfrontières"],
        "❓": ["Document au nom inconnu"],
        "♿": ["handicap", "handicapés", "handicapées", "handicapé", "handicapée"],
        "📈": ["croissance"],
        "🔒": ["sécurité", "sécurités", "chiffrement"],
        "⚖️": ["parquet", "justice", "judiciaire", "judiciaires", "cour de justice", "pénale", "pénal", "pénales", "sanctions", "tribunal", "tribunaux", "condamnation"]
    }
    for flag, keywords in emoji_keywords_.items():
        emoji_keywords_[flag] = re.compile(r"(?:\W|^)(" + "|".join([re.escape(keyword) for keyword in keywords]) + r")(?:\W|$)", flags=re.IGNORECASE)
    return emoji_keywords_

emoji_keywords = create_emojis_keywords()

def add_emojis(title):
    emojis = []
    for emoji, keywords in emoji_keywords.items():
        if re.search(keywords, title):
            emojis.append(emoji)
        if len(emojis) >= 3:
            break
    return " ".join(emojis) + " "


def vote_results_per_group(data: dict):
    results_per_group = {}

    def get_number_of_votes(group, vote_type, votes):
        if vote_type not in votes:
            return 0
        if group not in votes[vote_type]:
            return 0
        return len(votes[vote_type][group])

    def majority(votes_for, votes_against):
        """
        The abstentions don't count in the result of a vote: only the votes for and against are compared. None when
        they are equal (no majority, or only abstentions).
        """
        return None if votes_for == votes_against else votes_for > votes_against

    def voted_for_this_document(group, votes):
        return majority(get_number_of_votes(group, "+", votes), get_number_of_votes(group, "-", votes))

    def france_voted_for_this_document(votes):
        return majority(sum(len(members) for members in votes.get("+", {}).values()),
                        sum(len(members) for members in votes.get("-", {}).values()))

    def get_all_groups(votes):
        all_groups = set()
        for vote_type in votes:
            all_groups.update(set(votes[vote_type].keys()))
        return all_groups

    for document, results in data.items():
        if "votes" not in results or results["votes"] == {} or not results["global"]["was_roll_call_voted"]:
            continue
        all_groups = get_all_groups(results["votes"])
        results_per_group[document] = {}
        for group in all_groups:
            results_per_group[document][group] = voted_for_this_document(group, results["votes"])
        results_per_group[document]["Parlement Européen :"] = results["global"]["was_adopted"]
        results_per_group[document]["Parlement Européen :"] = results["global"]["was_adopted"]
        results_per_group[document]["Total France :"] = france_voted_for_this_document(results["votes"])

    return results_per_group

class SearchCorrelations:
    """
    How often the groups voted alike on the documents found by a search. The documents are added one by one, so that
    they don't have to be kept in memory: only the position of each group is kept.
    """

    def __init__(self):
        self.groups = {"Parlement Européen :", "Total France :"}
        # [{<group>: <position on the document, see vote_results_per_group>}]
        self.positions = []

    def add(self, results: dict):
        """
        :param results: a document found, as displayed on the results page
        """
        for vote_type in results["votes"]:
            self.groups.update(results["votes"][vote_type].keys())
        self.positions.extend(vote_results_per_group({None: results}).values())

    def correlations(self) -> dict:
        all_groups = sorted(self.groups, key=political_group_spectrum)
        correlations = {}
        for i, group_1 in enumerate(all_groups):
            correlations[group_1] = {}
            for j in range(len(all_groups)):
                group_2 = all_groups[j]
                if j <= i:
                    correlations[group_1][group_2] = None
                    continue
                correlations[group_1][group_2] = 0
                valid_documents = 0
                for per_group in self.positions:
                    if group_1 not in per_group and group_2 not in per_group:
                        continue
                    elif group_1 in per_group and per_group[group_1] is None or group_2 in per_group and per_group[group_2] is None:
                        continue
                    elif group_1 in per_group and group_2 in per_group:
                        valid_documents += 1
                        correlations[group_1][group_2] += per_group[group_1] == per_group[group_2]
                if valid_documents == 0:
                    correlations[group_1][group_2] = None
                else:
                    correlations[group_1][group_2] /= valid_documents
        return correlations


def to_html_id(input_string: str):
    return re.sub(r'[^a-zA-Z0-9\-]', '-', input_string)


def fr_number(number) -> str:
    """
    Format a number the French way: thousands separated by a narrow no-break space (1 000)
    """
    return f"{number:,}".replace(",", "\u202f")


def fr_decimal(number) -> str:
    """
    Format a number with one decimal the French way (1 234,5), without the decimal when it's 0 (1 234)
    """
    return f"{number:,.1f}".removesuffix(".0").replace(",", "\u202f").replace(".", ",")
