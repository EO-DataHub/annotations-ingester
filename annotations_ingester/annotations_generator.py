import logging
import os
import re
from typing import Sequence

import boto3
from eodhp_utils.messagers import CatalogueSTACChangeMessager, Messager
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


def convert_format(file_path: str, format: str):
    g = Graph()
    g.parse(file_path)
    return g.serialize(format=format)


def download_s3_file(file_name: str, bucket):  # , file_path: str):
    s3_client = boto3.client("s3")
    s3_client.download_file(bucket, file_name, file_name)
    file_contents = open(file_name).read()

    return file_contents

    # output_file = Path(file_path)
    # output_file.parent.mkdir(exist_ok=True, parents=True)
    # with open(file_path, 'w') as f:
    #     f.write(file_contents)


class AnnotationsMessager(CatalogueSTACChangeMessager):
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

    def process_update_stac(
        self,
        cat_path: str,
        stac: dict,
        **kwargs,
    ) -> Sequence[Messager.Action]:

        all_actions = []

        if is_file_immutable(cat_path):
            cache_control_header_length = 60 * 60 * 24 * 7  # seconds in a week
        else:
            cache_control_header_length = 0

        file_contents = download_s3_file(f"transformed/{cat_path}", self._dest_bucket)

        all_actions.append(
            Messager.S3UploadAction(
                bucket=self._dest_bucket,
                key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".ttl",
                file_body=convert_format(file_contents, "turtle"),
                mime_type="text/turtle",
            )
        )
        all_actions.append(
            Messager.S3UploadAction(
                bucket=self._dest_bucket,
                key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".jsonld",
                file_body=convert_format(file_contents, "json_ld"),
                mime_type="application/ld+json",
            )
        )

        return all_actions

    # def process_msg(self, msg: Message) -> Sequence[Messager.Action]:
    #     """
    #     This processes an input catalogue change message, loops over each changed entry in it,
    #     asks the implementation (in a task-specific subclass) to process each one separately.
    #     The set of actions is then returned for the superclass to run.
    #     """
    #     harvest_schema = eodhp_utils.pulsar.messages.generate_harvest_schema()
    #     input_change_msg = eodhp_utils.pulsar.messages.get_message_data(msg, harvest_schema)
    #
    #     # Does anything need this? Maybe configure the logger with it?
    #     # id = input_change_msg.get("id")
    #     input_bucket = input_change_msg.get("bucket_name")
    #     source = input_change_msg.get("source")
    #     target = input_change_msg.get("target")
    #
    #     s3_client = boto3.client('s3')
    #
    #     all_actions = []
    #     for change_type in ("added_keys",):#, "updated_keys", "deleted_keys"):
    #         for key in input_change_msg.get(change_type):
    #             # The key in the source bucket has format
    #             # "<harvest-pipeline-component>/<catalogue-path>"
    #             #
    #             # These two pieces must be separated.
    #             previous_step_prefix, cat_path = key.split("/", 1)
    #
    #             try:
    #                 if change_type == "added_keys":
    #                     # Updated or added.
    #
    #                     file_contents = download_s3_file(key, input_bucket, s3_client)
    #
    #                     if is_file_immutable(file_contents):
    #                         cache_control_header_length = 60*60*24*7  # seconds in a week
    #                     else:
    #                         cache_control_header_length = 0
    #
    #
    #                     # entry_actions = self.process_update(
    #                     #     input_bucket,
    #                     #     key,
    #                     #     cat_path,
    #                     #     source,
    #                     #     target,
    #                     # )
    #
    #                     all_actions.append(
    #                         Messager.S3UploadAction(
    #                             bucket=self._dest_bucket,
    #                             key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".ttl",
    #                             file_body=convert_format(file_contents, 'turtle'),
    #                             mime_type="text/turtle",
    #                         ))
    #                     all_actions.append(
    #                         Messager.S3UploadAction(
    #                             bucket=self._dest_bucket,
    #                             key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".jsonld",
    #                             file_body=convert_format(file_contents, 'json_ld'),
    #                             mime_type="application/ld+json",
    #                         )
    #                     )
    #
    #                 logging.debug(f"{all_actions=}")
    #             except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
    #                 if eodhp_utils.messagers._is_boto_error_temporary(e):
    #                     logging.exception(f"Temporary Boto error for {key=}")
    #                     all_actions.append(Messager.FailureAction(key=key, permanent=False))
    #                 else:
    #                     logging.exception(f"Permanent Boto error for {key=}")
    #                     all_actions.append(Messager.FailureAction(key=key, permanent=True))
    #             except eodhp_utils.messagers.TemporaryFailure:
    #                 logging.exception(f"TemporaryFailure processing {key=}")
    #                 all_actions.append(Messager.FailureAction(key=key, permanent=False))
    #             except Exception:
    #                 logging.exception(f"Exception processing {key=}")
    #                 all_actions.append(Messager.FailureAction(key=key, permanent=True))
    #
    #     return all_actions

    #
    # def add_cache_control_header(self):
    #     pass
    #
    #
    #
    # def process_stac_update(
    #     self,
    #     cat_path: str,
    #     stac: dict,
    #     **kwargs,
    # ) -> Sequence[Messager.Action]:
    #     ld_graph = self.generate_dcat(stac)
    #
    #     file_contents = 3
    #
    #     if ld_graph is None:
    #         return None
    #     else:
    #         if is_file_immutable(file_contents):
    #
    #         ld_ttl = ld_graph.serialize(format="turtle")
    #         ld_jsonld = ld_graph.serialize(format="json-ld")
    #
    #         # This saves the output directly to the catalogue public bucket. With a little nginx
    #         # config, this means it can appear at, say,
    #         #  /api/catalogue/stac/catalogs/my-catalog/collections/collection.jsonld
    #         return (
    #             Messager.S3UploadAction(
    #                 bucket=self._dest_bucket,
    #                 key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".ttl",
    #                 file_body=ld_ttl,
    #                 mime_type="text/turtle",
    #             ),
    #             Messager.S3UploadAction(
    #                 bucket=self._dest_bucket,
    #                 key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".jsonld",
    #                 file_body=ld_jsonld,
    #                 mime_type="application/ld+json",
    #             ),
    #         )
