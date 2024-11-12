import collections

import pytest

from annotations_ingester.annotations_generator import (
    AnnotationsMessager,
    get_uuid_from_graph,
)


@pytest.fixture
def mock_uuid():
    return "12345678-1234-1234-1234-123456789012"


@pytest.fixture
def mock_file_contents(mock_uuid):
    return f"""
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dctype: <http://purl.org/dc/dcmitype/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sdo: <http://schema.org/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix vcard: <http://www.w3.org/2006/vcard/ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sdmx-attribute: <http://purl.org/linked-data/sdmx/2009/attribute#> .

@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix vann:    <http://purl.org/vocab/vann/> .
@prefix qb:      <http://purl.org/linked-data/cube#> .
@prefix daq:     <http://purl.org/eis/vocab/daq#> .
@prefix voaf:    <http://purl.org/vocommons/voaf#> .
@prefix oa:      <http://www.w3.org/ns/oa#> .
@prefix duv:     <http://www.w3.org/ns/duv#> .

@prefix dqv:     <http://www.w3.org/ns/dqv#> .

@prefix eodhqa: <https://eodatahub.org.uk/api/ontologies/qa/> .
@prefix eodh: <https://eodatahub.org.uk/api/ontologies/annotations/> .
@prefix eodhweblinks: <https://eodatahub.org.uk/api/ontologies/weblinks/> .

@prefix : <https://dev.eodatahub.org.uk/ades/qa-workspace/ogc-api/jobs/968dff48-6316-4c3a-9d3e-62d61c658a53> .


# Unresolved questions:
#  - Can we tie the author to a persistent identifier? eg https://eodatahub.org.uk/api/users/authorusername
#  - Can we relate this person to an organization?
#  - Can we obtain more information about the QA check pipeline? Should we use PROV and broader provenance support?
#  - Is there a better way to identify a workflow and a workflow job? eg, fit them into the single API hierarchy.
#  - What does NPL's 'check_version' represent?
#  - How do identify this output?
#    This uses https://dev.eodatahub.org.uk/ades/qa-workspace/ogc-api/jobs/968dff48-6316-4c3a-9d3e-62d61c658a53 but
#    we'd also need an identifier for a harvest from a Git repo, etc., so maybe we need an identifier for a harvest.

_:org
    a                           prov:Agent, prov:Organization;
    foaf:name                   "National Physical Laboratory"^^xsd:string
    .

_:author
    a                           prov:Agent, prov:Person;
    foaf:givenName              "S Malone"^^xsd:string;
    prov:actedOnBehalfOf        _:org
    .


<https://dev.eodatahub.org.uk/ades/qa-workspace/ogc-api/processes/qa-workflow-id>
    # Unsure if this should be an Entity or a SoftwareAgent.
    a                           prov:Entity
    .

<https://dev.eodatahub.org.uk/ades/qa-workspace/ogc-api/jobs/968dff48-6316-4c3a-9d3e-62d61c658a53>
    a                           prov:Activity;
    prov:used                   <https://dev.eodatahub.org.uk/ades/qa-workspace/ogc-api/processes/qa-workflow-id>;
    prov:wasAssociatedWith      _:author
    .


:qualityCheckResults {{
    :checkRun
        a                           eodhqa:EODHQualityMeasurementDataset;
        rdfs:label                  "documentation review d5e53c05-861e-4946-9951-cfabdbfc44fd";
        owl:sameAs                  <urn:uuid:{mock_uuid}>;
        eodhqa:datasetComputedOn    <https://dev.eodatahub.org.uk/api/catalogue/stac/catalogs/supported-datasets/ceda-stac-fastapi/collections/sentinel1_l1c> ;
        eodhqa:validityEnd          "2025-01-25T04:10:00Z"^^xsd:dateTime;
        eodhqa:weblink              :doc1, :doc2
        .

    :productDetailsCheck
        a                           dqv:QualityMeasurement ;
        dqv:computedOn              <https://dev.eodatahub.org.uk/api/catalogue/stac/catalogs/supported-datasets/ceda-stac-fastapi/collections/sentinel1_l1c> ;
        .
}}

:qualityCheckResults
    a                           dqv:QualityMetadata, prov:Entity ;
    prov:generatedAtTime        "2024-07-26T16:10:00Z"^^xsd:dateTime ;
    prov:wasGeneratedBy         <https://dev.eodatahub.org.uk/ades/qa-workspace/ogc-api/jobs/968dff48-6316-4c3a-9d3e-62d61c658a53>;
    prov:wasAttributedTo        _:author;
    .
"""  # noqa:E501


def test_get_uuid_from_graph(mock_uuid, mock_file_contents):
    actual_uuid = get_uuid_from_graph(mock_file_contents)

    assert actual_uuid == mock_uuid


def test_process_delete():
    messenger = AnnotationsMessager(None, None, None, None)

    deleted = messenger.process_delete()

    assert isinstance(deleted, collections.abc.Sequence)


def test_process_update_body(mock_file_contents, mock_uuid):
    bucket_name = 'test_bucket'
    messenger = AnnotationsMessager(None, bucket_name, None, None)

    body = mock_file_contents.encode("utf-8")
    actions = messenger.process_update_body(body, "path", "source", "target")

    assert isinstance(actions, collections.abc.Sequence)

    assert len(actions) == 2

    assert actions[0].bucket == bucket_name
    assert actions[0].cache_control == 'max-age=604800'
    assert mock_uuid in actions[0].key
