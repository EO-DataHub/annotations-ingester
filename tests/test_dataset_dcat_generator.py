import copy
import io
import json

import pytest
from rdflib import DCTERMS, Graph, Literal, URIRef
from rdflib.namespace import DCAT, RDF

from annotations_ingester.dataset_dcat_generator import DatasetDCATMessager, Messager

SOURCE_PATH = "https://example.link.for.test/"
TARGET = "/target_directory/"
OUTPUT_ROOT = "https://output.root.test"


@pytest.fixture
def mock_sentinel_collection():
    return {
        "type": "Collection",
        "stac_version": "1.0.0",
        "stac_extensions": [],
        "id": "sentinel2_ard",
        "title": "",
        "description": "sentinel 2 ARD",
        "links": [],
        "keywords": [],
        "license": "sentinel",
        "providers": [],
        "extent": {
            "spatial": {
                "bbox": [
                    [-9.00034454651177, 49.48562028352171, 3.1494256015866995, 61.33444247301668]
                ]
            },
            "temporal": {"interval": [["2023-01-01T11:14:51.000Z", "2023-11-01T11:43:49.000Z"]]},
        },
        "summaries": {
            "Instrument Family Name Abbreviation": ["MSI"],
            "NSSDC Identifier": ["2015-000A"],
            "Start Orbit Number": ["030408", "030422", "032553", "032567"],
            "Instrument Family Name": ["Multi-Spectral Instrument"],
            "Platform Number": ["2A", "2B"],
            "Start Relative Orbit Number": ["023", "037", "066", "080", "094", "123", "137"],
            "Ground Tracking Direction": ["ascending", "descending"],
        },
        "assets": {},
    }


@pytest.fixture
def mock_catalog():
    return {
        "type": "Catalog",
        "id": "stac-fastapi",
        "title": "stac-fastapi-elasticsearch",
        "description": "A STAC FastAPI with an Elasticsearch backend",
        "stac_version": "1.0.0",
        "conformsTo": [],
        "links": [
            {
                "rel": "self",
                "type": "application/json",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/",
            },
            {
                "rel": "root",
                "type": "application/json",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/",
            },
            {
                "rel": "data",
                "type": "application/json",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/collections",
            },
            {
                "rel": "conformance",
                "type": "application/json",
                "title": "STAC/WFS3 conformance classes implemented by this server",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/conformance",
            },
            {
                "rel": "search",
                "type": "application/geo+json",
                "title": "STAC search",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/search",
                "method": "GET",
            },
            {
                "rel": "search",
                "type": "application/geo+json",
                "title": "STAC search",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/search",
                "method": "POST",
            },
            {
                "rel": "child",
                "type": "application/json",
                "title": "Supported Datasets",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/catalogs/supported-datasets",
            },
            {
                "rel": "child",
                "type": "application/json",
                "title": "User Datasets",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/catalogs/user-datasets",
            },
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "OpenAPI service description",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/api",
            },
            {
                "rel": "service-doc",
                "type": "text/html",
                "title": "OpenAPI service documentation",
                "href": "https://dev.eodatahub.org.uk/api/catalogue/stac/api.html",
            },
        ],
        "stac_extensions": [],
    }


@pytest.mark.parametrize(
    "fake_entry",
    [
        json.loads('{"not_stac": "but is json"}'),
        json.loads('{"type": "Feature", "stac_version": "1.0.0"}'),
    ],
)
def test_ignores_irrelevant_entries(fake_entry):
    messager = DatasetDCATMessager(None, None)

    actions = messager.process_update_stac(cat_path="/a/b", stac=fake_entry, source=None, target=None)

    assert actions == []


def process_stac_to_graph(stac: dict) -> Graph:
    """Runs the DatasetDCATMessager on 'stac', expecting Turtle output which is parsed
    and returned."""
    messager = DatasetDCATMessager(None, None)

    actions = messager.process_update_stac(
        cat_path="/cat/path",
        stac=copy.deepcopy(stac),
        source=None,
        target=None,
    )

    assert len(actions) == 2

    for action in actions:
        assert isinstance(action, Messager.S3UploadAction)

        g = Graph()
        g.parse(io.StringIO(action.file_body), format=action.mime_type)

    return g


@pytest.fixture
def mock_root_cat():
    return {
        "stac_version": "1.0.0",
        "type": "Catalog",
        "id": "root",
        "title": "Root",
        "description": "Root descr",
        "links": [
            {"rel": "self", "href": "https://example.com/api/catalogue/stac"},
            {"rel": "root", "href": "https://example.com/api/catalogue/stac"},
        ],
    }


def test_generates_dcat_catalog_for_stac_catalog(mock_root_cat):
    g = process_stac_to_graph(mock_root_cat)

    rootURI = URIRef("https://example.com/api/catalogue/stac")
    assert (rootURI, RDF.type, DCAT.Catalog) in g
    assert (rootURI, DCTERMS.identifier, rootURI) in g


def test_generates_dcat_dataset_for_stac_collection(mock_sentinel2_l2a_col):
    g = process_stac_to_graph(mock_sentinel2_l2a_col)

    rootURI = URIRef("https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a")
    assert (rootURI, RDF.type, DCAT.Dataset) in g
    assert (rootURI, DCTERMS.identifier, rootURI) in g


@pytest.fixture
def mock_sentinel2_l2a_col():
    with open("test_data/test_dcat_generation_s2_l2a.json") as f:
        return json.load(f)


def test_adds_scientific_extension_identifiers(mock_sentinel2_l2a_col):
    """This checks that the DOIs in a 'cite-as' link and a 'sci:doi' property are added."""

    # This comes with only a cite-as link (and the URL form of a DOI)
    g = process_stac_to_graph(mock_sentinel2_l2a_col)

    rootURI = URIRef("https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a")
    assert (rootURI, DCTERMS.identifier, rootURI) in g
    assert (rootURI, DCTERMS.identifier, Literal("10.5270/S2_-742ikth")) in g
    assert (rootURI, DCTERMS.identifier, URIRef("https://doi.org/10.5270/S2_-742ikth")) in g

    # Try it with just the sci:doi field
    mock_sentinel2_l2a_col["sci:doi"] = "10.5270/S2_-742ikth"
    mock_sentinel2_l2a_col["links"] = list(
        filter(lambda link: link["rel"] != "cite_as", mock_sentinel2_l2a_col["links"])
    )

    g = process_stac_to_graph(mock_sentinel2_l2a_col)
    assert (rootURI, DCTERMS.identifier, URIRef("https://doi.org/10.5270/S2_-742ikth")) in g
    assert (rootURI, DCTERMS.identifier, Literal("10.5270/S2_-742ikth")) in g
