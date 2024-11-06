import logging
import os
import re
from typing import Sequence

import boto3
from eodhp_utils.messagers import Messager, CatalogueChangeBodyMessager
from rdflib import Graph

CATALOGUE_PUBLIC_BUCKET_PREFIX = "/catalogs/supported-datasets/ceda-stac-catalogue/collections/"


def is_file_immutable(file_contents):
    lowercase = file_contents.lower()
    if re.search(
        "[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}",
        lowercase,
    ):
        logging.info("File is immutable")
        return True

    logging.info("File is not immutable")
    return False


def download_s3_file(file_name: str, bucket):  # , file_path: str):
    s3_client = boto3.client("s3")
    s3_client.download_file(bucket, file_name, file_name)
    file_contents = open(file_name).read()

    return file_contents

    # output_file = Path(file_path)
    # output_file.parent.mkdir(exist_ok=True, parents=True)
    # with open(file_path, 'w') as f:
    #     f.write(file_contents)


class AnnotationsMessager(CatalogueChangeBodyMessager):
    """
    Generates basic DCAT for catalogue entries. Supports Catalogs and Collections and is
    intended only to be sufficient for finding QA information linked to a dataset.

    The output is sent to the cataloge public static files bucket under a path matching the
    catalogue API endpoint for the dataset. For example:
        /catalogue/
    """

    def __init__(self, catalogue_public_bucket: str):
        self._dest_bucket = catalogue_public_bucket

    def process_delete(self):
        pass

    def process_update_body(
        self,
        entry_body: dict,
        cat_path: str,
        **kwargs,
    ) -> Sequence[Messager.Action]:


        g = Graph()
        g.parse(entry_body)

        uuid = '000000-0000-0000-000000' #get_uuid_from_graph()

        turtle = g.serialize(format="turtle")
        jsonld = g.serialize(format="json_ld")

        return [
            Messager.S3UploadAction(
                key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + f"/annotations/{uuid}.ttl",
                file_body=turtle,
                mime_type="text/turtle",
            ),
            Messager.S3UploadAction(
                key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + f"/annotations/{uuid}.jsonld",
                file_body=jsonld,
                mime_type="application/ld+json",
            )
        ]
