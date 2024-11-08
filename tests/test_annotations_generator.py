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
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix : <https://test.com> .

:qualityCheckResults {{
    :checkRun
        owl:sameAs                  <urn:uuid:{mock_uuid}>;
        .
}}
"""  # noqa:E501


def test_get_uuid_from_graph(mock_uuid, mock_file_contents):

    expected_uuid = get_uuid_from_graph(mock_file_contents)

    assert expected_uuid == mock_uuid


def test_process_delete():
    messenger = AnnotationsMessager(None, None, None, None)

    deleted = messenger.process_delete()

    assert isinstance(deleted, collections.abc.Sequence)


def test_process_update_body(mock_file_contents):
    messenger = AnnotationsMessager(None, None, None, None)

    body = mock_file_contents.encode("utf-8")
    actions = messenger.process_update_body(body, "path", "source", "target")

    assert isinstance(actions, collections.abc.Sequence)
