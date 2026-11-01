"""
Access to the European Parliament open data portal (https://data.europarl.europa.eu).

The plenary documents (votes results, roll-call votes results, ...) are published there as XML files.
The same files are also published on www.europarl.europa.eu/doceo, but this website is protected against
automated requests, whereas the open data portal is meant to be used by programs.
"""
import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.date_management import parliament_number_from_date

OPEN_DATA_URL = "https://data.europarl.europa.eu"
API_URL = f"{OPEN_DATA_URL}/api/v2"
JSON_LD = "application/ld+json"
TIMEOUT = 60

__session = None
__meps_cache = {}

# Number of "429 Too Many Requests" responses received, to tune the parallelism
throttled_requests = 0


class __CountingRetry(Retry):
    def increment(self, method=None, url=None, response=None, *args, **kwargs):
        global throttled_requests
        if response is not None and response.status == 429:
            throttled_requests += 1
        return super().increment(method, url, response, *args, **kwargs)


class OpenDataError(Exception):
    pass


def session() -> requests.Session:
    """
    HTTP session shared by all the requests to the open data portal, with retries on transient errors
    """
    global __session
    if __session is None:
        __session = requests.Session()
        retries = __CountingRetry(total=8, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                        allowed_methods=["GET"])
        __session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=64))
        __session.headers.update({"User-Agent": "qui-vote-quoi (https://qui-vote-quoi.org)"})
    return __session


def __get(url: str, **kwargs) -> requests.Response | None:
    """
    GET request. Returns None if the resource does not exist, raises OpenDataError on other errors.
    """
    response = session().get(url, timeout=TIMEOUT, **kwargs)
    if response.status_code in (204, 404):
        return None
    if response.status_code != 200:
        raise OpenDataError(f"Error {response.status_code} for {url}")
    return response


def plenary_document_reference(date: str, kind: str) -> str:
    """
    Reference of a plenary document
    :param date: date of the sitting as iso formatted string
    :param kind: "RCV" for roll-call votes results, "VOT" for votes results
    :return: for example "PV-10-2024-10-08-RCV"
    """
    return f"PV-{parliament_number_from_date(date)}-{date}-{kind}"


def __find_xml_distribution(reference: str, language: str) -> str | None:
    """
    Ask the API where the XML file of the given document is stored, in the given language.
    The file names are not consistent over time (for example PV-9-2022-06-23-VOT-FNL_fr.xml but
    PV-10-2024-10-08-VOT_fr.xml), so the API is the reliable way to find them.
    :return: path of the file relatively to the open data portal, None if not found
    """
    response = __get(f"{API_URL}/plenary-session-documents/{reference}",
                     params={"format": JSON_LD, "language": language})
    if response is None:
        return None
    suffix = f"_{language}.xml"
    for document in response.json().get("data", []):
        # Only the expression in the requested language is detailed, the other ones are plain identifiers
        for expression in document.get("is_realized_by", []):
            if not isinstance(expression, dict):
                continue
            for manifestation in expression.get("is_embodied_by", []):
                path = manifestation.get("is_exemplified_by", "") if isinstance(manifestation, dict) else ""
                if path.lower().endswith(suffix):
                    return path
    return None


def get_plenary_document_xml(reference: str, language: str = "fr") -> etree._Element | None:
    """
    Download and parse the XML file of a plenary document
    :param reference: reference of the document, for example "PV-10-2024-10-08-RCV"
    :param language: language of the document
    :return: root of the XML tree, None if the document does not exist
    """
    path = __find_xml_distribution(reference, language)
    candidates = [path] if path else []
    # Fallback, in case the document is published but not indexed by the API yet
    candidates.append(f"distribution/doc/{reference}_{language}.xml")
    for candidate in candidates:
        response = __get(f"{OPEN_DATA_URL}/{candidate}")
        if response is not None and response.content.strip():
            return etree.fromstring(response.content)
    return None


def get_meps_ids(parliamentary_term: int, country: str = "FR") -> set[str]:
    """
    Identifiers (PersId) of all the members who represented the given country during the given term
    :param parliamentary_term: parliamentary term number (9, 10, ...)
    :param country: ISO code of the country
    :return: set of identifiers
    """
    key = (parliamentary_term, country)
    if key not in __meps_cache:
        response = __get(f"{API_URL}/meps", params={
            "parliamentary-term": parliamentary_term,
            "country-of-representation": country,
            "format": JSON_LD,
            "offset": 0,
            "limit": 1000,
        })
        if response is None:
            raise OpenDataError(f"Could not get the MEPs of {country} for term {parliamentary_term}")
        __meps_cache[key] = {mep["identifier"] for mep in response.json()["data"]}
    return __meps_cache[key]


def get_sitting_dates(year: int) -> set[str]:
    """
    Dates of the plenary sittings of the given year, as iso formatted strings.
    The calendar is published in advance, so future sittings are included.
    """
    response = __get(f"{API_URL}/meetings", params={"year": year, "format": JSON_LD, "offset": 0, "limit": 1000})
    if response is None:
        return set()
    return {meeting["activity_date"] for meeting in response.json().get("data", [])
            if meeting.get("activity_date") and meeting.get("had_activity_type", "").endswith("PLENARY_SITTING")}
