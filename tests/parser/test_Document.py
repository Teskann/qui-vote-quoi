import pytest
import requests
from parser.Document import Document, InvalidDocumentException, scrap_documents_from_string


def test_init_and_str():
    # Valid document names => Should work as expected
    valid_documents = ["RC-B10-0023/2024", "RC-B10-0028/2024", "B9-0331/2022", "C9-0185/2022", "A9-0181/2022",
                       "A9-0138/2022", "A9-0137/2022", "RC-B10-0023/2024/REV1", "RC-B10-0023/2024/rev1"]
    for document in valid_documents:
        assert str(Document(document)) == document

    # Invalid documents => Should throw
    invalid_documents = ["azoizf", "lakjfhaz", "RC-RC-RC-B10-0023/2024", "A9-0137/20202"]
    for invalid_document in invalid_documents:
        print(invalid_document)
        with pytest.raises(InvalidDocumentException):
            Document(invalid_document)


def test_document_id():
    expected = {
        "RC-B10-0023/2024": "RC-10-2024-0023",
        "RC-B10-0028/2024": "RC-10-2024-0028",
        "RC-B10-0028/2024/REV1": "RC-10-2024-0028",
        "B9-0331/2022": "B-9-2022-0331",
        "C9-0185/2022": "C-9-2022-0185",
        "A9-0181/2022": "A-9-2022-0181",
        "A9-0138/2022": "A-9-2022-0138",
        "A9-0137/2022": "A-9-2022-0137"
    }

    for document, expected_id in expected.items():
        assert Document(document).document_id() == expected_id

def test_source_url():
    expected = {
        "RC-B10-0023/2024": "https://www.europarl.europa.eu/doceo/document/RC-10-2024-0023_FR.html",
        "RC-B10-0028/2024": "https://www.europarl.europa.eu/doceo/document/RC-10-2024-0028_FR.html",
        "B9-0331/2022": "https://www.europarl.europa.eu/doceo/document/B-9-2022-0331_FR.html",
        "A9-0181/2022": "https://www.europarl.europa.eu/doceo/document/A-9-2022-0181_FR.html",
        "A9-0138/2022": "https://www.europarl.europa.eu/doceo/document/A-9-2022-0138_FR.html",
        "A9-0137/2022": "https://www.europarl.europa.eu/doceo/document/A-9-2022-0137_FR.html"
    }

    for document, expected_url in expected.items():
        assert Document(document).source_url() == expected_url
        response = requests.get(Document(document).source_url())
        assert response.status_code == 200

def test_title():
    expected = {
        "RC-B10-0023/2024": "PROPOSITION DE RÉSOLUTION COMMUNE sur la situation au Venezuela",
        "RC-B10-0028/2024": "PROPOSITION DE RÉSOLUTION COMMUNE sur la pérennité du soutien financier et militaire apporté à l’Ukraine par les États membres de l’Union",
        "B9-0331/2022": "PROPOSITION DE RÉSOLUTION sur le statut de candidat à l’adhésion à l’UE de l’Ukraine, de la République de Moldavie et de la Géorgie",
        "A9-0181/2022": "RAPPORT concernant la position du Conseil sur le projet de budget rectificatif nº 3/2022 de l’Union européenne pour l’exercice 2022 – Financement du coût de l'accueil des personnes fuyant l’Ukraine",
        "A9-0138/2022": "RAPPORT sur la proposition de règlement du Parlement européen et du Conseil modifiant le règlement (UE) 2021/953 relatif à un cadre pour la délivrance, la vérification et l’acceptation de certificats COVID-19 interopérables de vaccination, de test et de rétablissement (certificat COVID numérique de l’UE) afin de faciliter la libre circulation pendant la pandémie de COVID-19",
        "A9-0137/2022": "RAPPORT sur la proposition de règlement du Parlement européen et du Conseil modifiant le règlement (UE) 2021/954 relatif à un cadre pour la délivrance, la vérification et l’acceptation de certificats COVID-19 interopérables de vaccination, de test et de rétablissement (certificat COVID numérique de l’UE) destinés aux ressortissants de pays tiers séjournant ou résidant légalement sur le territoire des États membres pendant la pandémie de COVID-19"
    }

    for document, expected_title in expected.items():
        assert Document(document).title() == expected_title

def test_scrap_documents_from_string():
    expected = {
        "Certificat COVID numérique de l’UE - citoyens de l'Union - EU Digital COVID Certificate - Union citizens - Digitales COVID-Zertifikat der EU – Unionsbürger - A9-0138/2022 - Juan Fernando López Aguilar - Rejet - Am 18": {"A9-0138/2022"},
        "Soutien temporaire exceptionnel au titre du Feader en réaction aux conséquences de l’invasion de l’Ukraine par la Russie - Exceptional temporary support under EAFRD in response to the impact of Russia’s invasion of Ukraine - Befristete Sonderunterstützung im Rahmen des ELER als Reaktion auf die russische Invasion der Ukraine - C9-0185/2022 - Article 1, § 1, point 1 - Am 1": {"C9-0185/2022"},
        "Statut de pays candidat de l'Ukraine, de la République de Moldavie et de la Géorgie - Candidate status of Ukraine, the Republic of Moldova and Georgia - Status der Ukraine, der Republik Moldau und Georgiens als Bewerberländer - RC-B9-0331/2022 - § 4/2": {"RC-B9-0331/2022"},
        "RC-B9-0331/2022 - § 6/2": {"RC-B9-0331/2022"},
        "Hello world RC-B9-0331/2022": {"RC-B9-0331/2022"},
        "RC-B9-0331/2022": {"RC-B9-0331/2022"},
        "The first is this RC-B9-0331/2022 then there is A9-0138/2022\nthen C9-0185/2022": {"RC-B9-0331/2022", "A9-0138/2022", "C9-0185/2022"},
        "The first is this RC-B9-0331/2022 duplicated RC-B9-0331/2022 then there is A9-0138/2022\nthen C9-0185/2022 C9-0185/2022 C9-0185/2022 C9-0185/2022": {"RC-B9-0331/2022", "A9-0138/2022", "C9-0185/2022"},
    }

    for input_string, expected_documents in expected.items():
        print(input_string)
        scraped_documents = scrap_documents_from_string(input_string)
        assert len(scraped_documents) == len(expected_documents)
        documents_to_str = set(map(str, scraped_documents))
        assert documents_to_str == expected_documents