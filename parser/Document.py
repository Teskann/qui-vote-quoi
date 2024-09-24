import re
import requests


class InvalidDocumentException(Exception):
    """
    Exception to manage Document code parsing errors
    """
    pass


class Document:
    """
    Manage European Parliament Documents
    """

    rexeg_str = r"([^-\s]+-)?([ABCPTM])(\d{1,2})-(\d{4})/(\d{4})"
    regex = re.compile("^" + rexeg_str + "$")

    def __init__(self, eu_document_code: str):
        """
        Construct a document from its code
        If the document code is invalid, it raises InvalidDocumentException
        :param eu_document_code: for example: "RC-B9-0331/2022"
        """
        match = Document.regex.match(eu_document_code)
        if not match:
            raise InvalidDocumentException(f"The document code {eu_document_code} is invalid")
        self.prefix = match.group(1)[:-1] if match.group(1) else None
        self.letter = match.group(2)
        self.legislature_number = match.group(3)
        self.document_number = match.group(4)
        self.publication_date = match.group(5)
        self.__title = None
        self.__description = None

    def __str__(self) -> str:
        return f"{self.prefix + "-" if self.prefix else ""}{self.letter}{self.legislature_number}-{self.document_number}/{self.publication_date}"

    def __letter_conversion(self) -> str:
        if self.prefix == "RC":
            return "RC"
        return self.letter

    def document_id(self) -> str:
        """
        Get the ID of the document, as it's expected in europarl APIs and URLs
        """
        return f"{self.__letter_conversion()}-{self.legislature_number}-{self.publication_date}-{self.document_number}"

    def __get_title_and_description_from_api(self):
        """
        Retrieve the document name and description (if possible) and cache the names in member variables
        :return:
        """
        url = f"https://data.europarl.europa.eu/api/v2/documents/{self.document_id()}?format=application%2Fld%2Bjson&language=fr"
        response = requests.get(url)
        if response.status_code != 200:
            self.__title = "Document au nom inconnu"
            self.__description = "Nous ne sommes pas parvenus à récupérer le nom de ce document"
            return
        data = response.json()
        try:
            self.__title = data["data"][0]["is_realized_by"][0]["title"]["fr"]
            self.__description = data["data"][0]["is_realized_by"][0]["title_alternative"]["fr"]
        except (KeyError, IndexError):
            self.__title = "Document au nom inconnu"
            self.__description = "Nous ne sommes pas parvenus à récupérer le nom de ce document"

    def title(self) -> str:
        """
        Return the title of the document
        """
        if self.__title is None:
            self.__get_title_and_description_from_api()
        return self.__title

    def description(self) -> str:
        """
        Return the description of the document
        """
        if self.__description is None:
            self.__get_title_and_description_from_api()
        return self.__description

    def source_url(self) -> str:
        """
        Returns the URL to the document itself
        """
        return f"https://www.europarl.europa.eu/doceo/document/{self.document_id()}_FR.html"

    def to_dict(self) -> dict:
        return {
            "title": self.title(),
            "description": self.description(),
            "source_url": self.source_url(),
        }

def scrap_documents_from_string(text) -> set[Document]:
    """
    Find all document codes in `text` and create a Document object for each.
    Duplicated are not included.
    :param text: text to search
    :return: set of Document
    """
    rexexp = re.compile(f"(^|\\s+)({Document.rexeg_str})($|\\s+)", flags=re.MULTILINE | re.IGNORECASE)
    matches = rexexp.findall(text)
    all_documents_str = set()
    for match in matches:
        all_documents_str.add(str(match[1]))
    all_documents = set(map(lambda s: Document(s), all_documents_str))
    return all_documents
