import io
import json
import logging
import os
import re
import tempfile
from typing import Sequence

from eodhp_utils.messagers import Messager, CatalogueChangeBodyMessager
from rdflib import Graph


class AnnotationsMessager(CatalogueChangeBodyMessager):
    """
    Generates basic DCAT for catalogue entries. Supports Catalogs and Collections and is
    intended only to be sufficient for finding QA information linked to a dataset.

    The output is sent to the catalogue public static files bucket under a path matching the
    catalogue API endpoint for the dataset. For example:
        /catalogue/
    """

    def process_delete(self, **kwargs):
        return []

    def process_update_body(
        self,
        entry_body: dict,
        cat_path: str,
        source: str,
        target: str,
        **kwargs,
    ) -> Sequence[Messager.Action]:

        short_path = "/".join(cat_path.split("/")[:-1])

        # file_contents = json.dumps(entry_body.decode("utf-8"))
        # stream = io.StringIO(file_contents)
        #
        # graph = Graph()
        # graph.parse(stream)

        with tempfile.NamedTemporaryFile() as tf:
            tf.write(entry_body)
            graph = Graph()

            graph.parse(tf.name, format="trig")

            uuid = get_uuid_from_graph(entry_body.decode("utf-8"))

            if uuid:
                cache_control = 60*60*24*7 # 1 week
            else:
                cache_control = 0

            turtle = graph.serialize(format="turtle")
            jsonld = graph.serialize(format="json-ld")

        key_root = f"catalogues/{short_path}/annotations/{uuid}"

        return [
            Messager.S3UploadAction(
                key=key_root + ".ttl",
                file_body=turtle,
                mime_type="text/turtle",
                cache_control=str(cache_control),
                bucket=self.output_bucket,
            ),
            Messager.S3UploadAction(
                key=key_root + ".jsonld",
                file_body=jsonld,
                mime_type="application/ld+json",
                cache_control=str(cache_control),
                bucket=self.output_bucket,
            )
    ]


def get_uuid_from_graph(file_contents):
    """
    Looks for a line containing the UUID that looks like this:
    `owl:sameAs                  <urn:uuid:12345678-1234-1234-1234-123456789012>;`
    """

    pattern = r'owl:sameAs\s+<urn:uuid:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})>;'

    match = re.search(pattern, file_contents)

    if match:
        uuid = match.group(1)
    else:
        uuid = None
        logging.error("UUID not found")

    return uuid
