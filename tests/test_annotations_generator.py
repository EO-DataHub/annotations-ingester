import collections
import json
import tempfile

from annotations_ingester.annotations_generator import get_uuid_from_graph, AnnotationsMessager


def test_get_uuid_from_graph():
    uuid = "0dee7f5c-9ac9-11ef-9bca-f23ebbee2fc5"
    file_contents = {
        "type": "Feature", "stac_version": "1.0.0", "id": "output-file-1730737404.7883582", "properties": {"created": "2024-11-04T16:23:24.788358Z", "datetime": "2024-11-04T16:23:24.788358Z", "updated": "2024-11-04T16:23:24.788358Z"}, "geometry": {"type": "Polygon", "coordinates": [[[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]]}, "links": [{"rel": "collection", "href": f"https://test.eodhp.com/files/eodhp-dev-workspaces/processing-results/cat_{uuid}/results-collection.json", "type": "application/json", "title": "Annotations Example Collection Outputs"}, {"rel": "self", "href": f"https://test.workspaces.dev.eodhp.com/files/eodhp-dev-workspaces/processing-results/cat_{uuid}/results-collection/output-file-1730737404.7883582.json", "type": "application/json"}, {"rel": "parent", "href": f"https://https://dev.eodatahub.org.ukuser-datasets/test.workspaces.dev.eodhp.com/files/eodhp-dev-workspaces/processing-results/cat_{uuid}", "type": "application/json", "title": "Annotations Example Collection Outputs"}, {"rel": "root", "href": "https://dev.eodatahub.org.uk"}], "assets": {"output-file": {"href": f"https://test.workspaces.dev.eodhp.com/files/eodhp-dev-workspaces/processing-results/cat_{uuid}/results-collection/output-file.txt", "type": "text/plain", "file:size": 17, "roles": ["data"]}}, "bbox": [-180, -90, 180, 90], "stac_extensions": [], "collection": "results-collection"}

    expected_uuid = get_uuid_from_graph(file_contents)

    assert expected_uuid == uuid

def test_process_delete():
    messenger = AnnotationsMessager(None, None, None, None)

    deleted = messenger.process_delete()

    assert isinstance(deleted, collections.abc.Sequence)



def test_process_update_body():
    messenger = AnnotationsMessager(None, None, None, None)

    body = {'links': [{'href': 'http://00000000-0000-0000-0000-000000000000'}]}
    actions = messenger.process_update_body(body, 'path', 'source', 'target')

    assert isinstance(actions, collections.abc.Sequence)