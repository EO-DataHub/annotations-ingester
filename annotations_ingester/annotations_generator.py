import json
import logging
import re
import tempfile
from typing import Sequence

from eodhp_utils.messagers import Messager, CatalogueChangeBodyMessager
from rdflib import Graph

CATALOGUE_PUBLIC_BUCKET_PREFIX = "/catalogs/supported-datasets/ceda-stac-catalogue/collections/"


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

        with tempfile.NamedTemporaryFile() as tf:
            tf.write(entry_body)
            graph = Graph()
            graph.parse(tf.name)

            uuid = get_uuid_from_graph(entry_body)

            if uuid:
                cache_control = 60*60*24*7 # 1 week
            else:
                cache_control = 0

            turtle = graph.serialize(format="turtle")
            jsonld = graph.serialize(format="json-ld")

            key_root = CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + f"/annotations/{uuid}"

            return [
                Messager.S3UploadAction(
                    key=key_root + ".ttl",
                    file_body=turtle,
                    mime_type="text/turtle",
                    cache_control=str(cache_control),
                ),
                Messager.S3UploadAction(
                    key=key_root + ".jsonld",
                    file_body=jsonld,
                    mime_type="application/ld+json",
                    cache_control=str(cache_control),
                )
            ]


def get_uuid_from_graph(file_contents):
    decoded = json.loads(file_contents.decode('utf-8'))

    link = decoded.get("links")[0].get("href")

    uuid = re.search("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", link.lower())

    if uuid is None:
        logging.error("UUID not found")

    return uuid.group()
