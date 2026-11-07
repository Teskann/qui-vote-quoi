"""
Access to the European Parliament open data portal (https://data.europarl.europa.eu).

The plenary documents (votes results, roll-call votes results, ...) are published there as XML files.
The same files are also published on www.europarl.europa.eu/doceo, but this website is protected against
automated requests, whereas the open data portal is meant to be used by programs.
"""
import re

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.date_management import parliament_number_from_date

OPEN_DATA_URL = "https://data.europarl.europa.eu"
API_URL = f"{OPEN_DATA_URL}/api/v2"
JSON_LD = "application/ld+json"
DOCEO_URL = "https://www.europarl.europa.eu/doceo/document"
TIMEOUT = 60

__session = None
__meps_cache = {}
__mep_cache = {}
__corporate_bodies_cache = {}
__amendments_documents_cache = {}

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


def get_meps(parliamentary_term: int, country: str | None = "FR") -> list[dict]:
    """
    All the members who represented the given country during the given term
    :param parliamentary_term: parliamentary term number (8, 9, 10, ...)
    :param country: ISO code of the country, None for all the members
    :return: list of {"identifier": ..., "familyName": ..., "givenName": ..., ...}
    """
    key = (parliamentary_term, country)
    if key not in __meps_cache:
        params = {"parliamentary-term": parliamentary_term, "format": JSON_LD, "offset": 0, "limit": 5000}
        if country is not None:
            params["country-of-representation"] = country
        response = __get(f"{API_URL}/meps", params=params)
        if response is None:
            raise OpenDataError(f"Could not get the MEPs of {country} for term {parliamentary_term}")
        __meps_cache[key] = response.json()["data"]
    return __meps_cache[key]


def get_mep(identifier: str) -> dict:
    """
    Details of a member, including all their memberships: mandates (with the represented country), political groups,
    committees, ... with their periods
    :param identifier: identifier of the member (PersId)
    :return: {"identifier": ..., "hasMembership": [{"memberDuring": {"startDate": ..., "endDate": ...}, ...}], ...}
    """
    if identifier not in __mep_cache:
        response = __get(f"{API_URL}/meps/{identifier}", params={"format": JSON_LD})
        if response is None:
            raise OpenDataError(f"Could not get the member {identifier}")
        __mep_cache[identifier] = response.json()["data"][0]
    return __mep_cache[identifier]


def get_mep_gender(identifier: str) -> str | None:
    """
    :param identifier: identifier of the member (PersId)
    :return: "F", "M", or None if the gender is not given
    """
    gender = get_mep(identifier).get("hasGender", "")
    return {"FEMALE": "F", "MALE": "M"}.get(gender.rsplit("/", 1)[-1])


def get_corporate_body_label(identifier: str) -> str:
    """
    Short name of a corporate body (political group, committee, ...)
    :param identifier: identifier of the corporate body, for example "7150"
    :return: for example "PfE". The political groups have the same names as in the roll-call votes results.
    """
    if identifier not in __corporate_bodies_cache:
        response = __get(f"{API_URL}/corporate-bodies/{identifier}", params={"format": JSON_LD})
        if response is None:
            raise OpenDataError(f"Could not get the corporate body {identifier}")
        __corporate_bodies_cache[identifier] = response.json()["data"][0]["label"]
    return __corporate_bodies_cache[identifier]


def plenary_document_identifier(eu_document_code: str) -> str | None:
    """
    :param eu_document_code: for example "A10-0018/2025", "B10-0476/2026" or "RC-B10-0476/2026"
    :return: identifier of the document in the API, for example "A-10-2025-0018" or "RC-10-2026-0476". None if the code
    is not one of a plenary document.
    """
    match = re.match(r"^(RC-)?([A-Z])(\d+)-(\d+)/(\d{4})$", eu_document_code)
    if not match:
        return None
    joint, letter, term, number, year = match.groups()
    return f"{'RC' if joint else letter}-{term}-{year}-{number}"


def get_amendments_documents(eu_document_code: str, language: str = "fr") -> list[tuple[int, int, str]]:
    """
    Documents of the amendments tabled in plenary on a document. Each document gathers a range of amendments.
    :param eu_document_code: for example "A10-0018/2025"
    :return: [(<first amendment number>, <last amendment number>, <URL of the PDF document>)], empty if unknown
    """
    if eu_document_code not in __amendments_documents_cache:
        identifier = plenary_document_identifier(eu_document_code)
        response = __get(f"{API_URL}/plenary-documents/{identifier}",
                         params={"format": JSON_LD, "language": language}) if identifier else None
        documents = []
        for document in (response.json().get("data", [{}])[0].get("inverse_foresees_change_of", [])
                         if response is not None else []):
            numbers = re.search(r"-AM-(\d+)-(\d+)$", document.get("id", ""))
            paths = [manifestation.get("is_exemplified_by", "")
                     for expression in document.get("is_realized_by", []) if isinstance(expression, dict)
                     for manifestation in expression.get("is_embodied_by", []) if isinstance(manifestation, dict)]
            pdf = next((path for path in paths if path.lower().endswith(f"_{language}.pdf")),
                       next((path for path in paths if path.lower().endswith(".pdf")), None))
            # The files of some documents (amendments to joint motions for resolution) are not on the open data
            # portal: the document is then linked on the website of the parliament
            reference = document.get("id", "").split("/")[-1]
            url = f"{OPEN_DATA_URL}/{pdf}" if pdf else f"{DOCEO_URL}/{reference}_{language.upper()}.pdf"
            if numbers:
                documents.append((int(numbers[1]), int(numbers[2]), url))
        # Not kept when the API could not be reached, to try again later
        if response is not None:
            __amendments_documents_cache[eu_document_code] = documents
        return documents
    return __amendments_documents_cache[eu_document_code]


def amendment_document(amendment_number: str | None, documents: list[tuple[int, int, str]]) -> str | None:
    """
    :param amendment_number: number of an amendment, for example "162", "118PC8" or "§" (original text)
    :param documents: see get_amendments_documents
    :return: URL of the document of the amendment, None if unknown. The ranges may overlap: the narrowest one is used.
    """
    number = re.match(r"^\d+", amendment_number or "")
    if not number:
        return None
    matching = [document for document in documents if document[0] <= int(number[0]) <= document[1]]
    return min(matching, key=lambda document: document[1] - document[0])[2] if matching else None


def get_sitting_dates(year: int) -> set[str]:
    """
    Dates of the plenary sittings of the given year, as iso formatted strings.
    The calendar is published in advance, so future sittings are included.
    """
    response = __get(f"{API_URL}/meetings", params={"year": year, "format": JSON_LD, "offset": 0, "limit": 1000})
    if response is None:
        return set()
    dates = set()
    for meeting in response.json().get("data", []):
        if not str(meeting.get("had_activity_type", "")).endswith("PLENARY_SITTING"):
            continue
        # Depending on the year, the date is "2024-10-08" or {"@value": "2019-12-17T00:00:00+01:00", ...}
        date = meeting.get("activity_date") or meeting.get("eli-dl:activity_date")
        if isinstance(date, dict):
            date = date.get("@value")
        if date:
            dates.add(str(date)[:10])
    return dates
