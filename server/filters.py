import datetime
import re

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
        "France / GUE/NGL :": "https://left.eu/the-group/",
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
        "France / GUE/NGL :": "group_guengl",
    }
    return classes[group_name] if group_name in classes else "group_ni"

def political_group_tooltip(group_name):
    classes = {
        "France / ECR :": "Conservateurs et réformistes européens (droite à extrême droite)",
        "France / ENS :": "L'Europe des nations souveraines (extrême droite)",
        "France / PfE :": "Patriotes pour l'Europe (droite à extrême droite)",
        "France / ID :": "Parti Identité et démocratie (droite radicale à extrême)",
        "France / PPE :": "Groupe du Parti populaire européen (centre droit à droite)",
        "France / Renew :": "Renew Europe (centre)",
        "France / S&D :": "Alliance progressiste des socialistes et démocrates au Parlement européen (gauche à centre gauche)",
        "France / The Left :": "Groupe de la Gauche au Parlement européen (gauche à extrême gauche)",
        "France / Verts/ALE :": "Groupe des Verts/Alliance libre européenne (centre gauche à gauche)",
        "France / NI :": "Non-inscrit au Parlement européen",
        "France / GUE/NGL :": "Groupe de la Gauche au Parlement européen (gauche à extrême gauche)",
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

def add_flags(title):
    flags_keywords = {
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
        "🇮🇶": ["Irak", "Irakien", "Irakiens", "Irakienne", "Irakiennes", "Bagdad", "Bassorah"],
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
        "🇲🇰": ["Macédoine du Nord", "Macédonien", "Macédoniens", "Macédonienne", "Macédoniennes", "Skopje", "Bitola"],
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
        "🇲🇩": ["Moldavie", "Moldave", "Moldaves", "Moldave", "Moldaves", "Chisinau", "Tiraspol"],
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
        "🇻🇳": ["Vietnam", "Vietnamien", "Vietnamiens", "Vietnamienne", "Vietnamiennes", "Hanoï", "Hô-Chi-Minh-Ville"],
        "🇾🇪": ["Yémen", "Yéménite", "Yéménites", "Yéménite", "Yéménites", "Sanaa", "Aden"],
        "🇿🇲": ["Zambie", "Zambien", "Zambiens", "Zambienne", "Zambiennes", "Lusaka", "Kitwe"],
        "🇿🇼": ["Zimbabwe", "Zimbabwéen", "Zimbabwéens", "Zimbabwéenne", "Zimbabwéennes", "Harare", "Bulawayo"],
        "🇵🇸": ["Palestine", "Palestinien", "Palestiniens", "Palestinienne", "Palestiniennes", "Ramallah", "Gaza"],
        "🇭🇰": ["Hong Kong", "Hongkongais", "Hongkongais", "Hongkongaise", "Hongkongaises", "Hong Kong", "Kowloon"],
        "🇲🇴": ["Macao", "Macanais", "Macanais", "Macanaise", "Macanaises", "Macao", "Taipa"],
        "🇽🇰": ["Kosovo", "Kosovar", "Kosovars", "Kosovare", "Kosovares", "Pristina", "Mitrovica"],
        "🇼🇸": ["Samoa", "Samoan", "Samoans", "Samoane", "Samoanes", "Apia", "Faleasiu"],
        "🇹🇼": ["Taïwan", "Taïwanais", "Taïwanais", "Taïwanaise", "Taïwanaises", "Taipei", "Kaohsiung"],
        "🇪🇭": ["Sahara occidental", "Sahraoui", "Sahraouis", "Sahraouie", "Sahraouies", "El-Aaiun", "Dakhla"],
        "🏳️‍🌈": ["LGBT", "LGBTI", "LGBTI+", "LGBTIQ", "LGBTIQ+", "LGBTQI", "LGBTQI+", "LGBTQIA+", "homosexuel", "homosexuels", "homosexuelle", "homosexuelles", "transsexuel", "transsexuels"]
    }
    flags = []
    def match_keyword(text, keyword):
        keyword_regex = re.compile(r"(?:\W|^)(" + keyword + r")(?:\W|$)", flags=re.IGNORECASE)
        match = re.search(keyword_regex, text)
        return match is not None

    for flag, keywords in flags_keywords.items():
        if any([match_keyword(title, keyword) for keyword in keywords]):
            flags.append(flag)
    return " ".join(flags) + " "

