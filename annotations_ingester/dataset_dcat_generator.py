import dataclasses
import json
import logging
import sys
from abc import ABC
from copy import copy
from typing import Sequence, Union

import eodhp_utils.pulsar.messages
import pystac
from pulsar import Message
from pystac import Catalog, Collection, STACTypeError
from rdflib import DCAT, DCTERMS, RDF, Graph, Literal, URIRef

DOI_URL_PREFIX = "https://doi.org/"


# This is a prototype of how we might remove some of the duplicated Pulsar and S3 related
# functionality in the ingesters, harvesters and transformer.
class CatalogueChangeMessager:
    def __init__(self, s3_client):
        self._s3_client = s3_client

    class Action(ABC):  # noqa: B024
        pass

    @dataclasses.dataclass
    class OutputFileAction(Action):
        cat_path: str
        file_body: str

    @dataclasses.dataclass
    class S3UploadAction(Action):
        bucket: str
        key: str
        file_body: str

    @dataclasses.dataclass
    class MessageAction(Action):
        message_body: str
        topic: str

    def consume_update(
        self, key: str, source: str, target: str, output_root: str, bucket: str
    ) -> Sequence[Action]:
        file_body = eodhp_utils.aws.s3.get_file_s3(bucket, key, self._s3_client)

        try:
            file_body = json.loads(file_body)
        except ValueError:
            # Not a JSON file - consume it as a string
            logging.info(f"File {key} is not valid JSON.")

        return self.consume_update_file_contents(file_body)

    def consume_update_file_contents(self, file_body: Union[dict, str]) -> Sequence[Action]:
        return None

    def consume_delete(self):
        return None

    def consume(self, msg: Message, output_root):
        harvest_schema = eodhp_utils.pulsar.messages.generate_harvest_schema()
        data_dict = eodhp_utils.pulsar.messages.get_message_data(msg, harvest_schema)

        bucket_name = data_dict.get("bucket_name")
        source = data_dict.get("source")
        target = data_dict.get("target")

        output_data = copy.deepcopy(data_dict)
        output_data["added_keys"] = []
        output_data["updated_keys"] = []
        output_data["deleted_keys"] = []
        output_data["failed_files"] = {
            "temp_failed_keys": {
                "updated_keys": [],
                "added_keys": [],
                "deleted_keys": [],
            },
            "perm_failed_keys": {
                "updated_keys": [],
                "added_keys": [],
                "deleted_keys": [],
            },
        }
        error_data = copy.deepcopy(output_data)

        for change_type in ("added_keys", "updated_keys", "deleted_keys"):
            for key in data_dict.get(change_type):
                try:
                    updated_key = eodhp_utils.pulsar.messages.transform_key(key, source, target)

                    if change_type == "deleted_keys":
                        self.consume_delete(
                            key,
                            source,
                            target,
                            output_root,
                            bucket_name,
                        )

                        # Remove file from S3
                        eodhp_utils.pulsar.messages.delete_file_s3(bucket_name, updated_key)
                    else:
                        # Updated or added.
                        file_body = self.consume_update(
                            key,
                            source,
                            target,
                            output_root,
                            bucket_name,
                        )

                        # Upload file to S3
                        eodhp_utils.pulsar.messages.upload_file_s3(
                            file_body, bucket_name, updated_key
                        )
                        logging.info(f"Links successfully rewritten for file {key}")

                    output_data[change_type].append(updated_key)
                except eodhp_utils.pulsar.messages.URLAccessError as e:
                    logging.error(f"Unable to access key {key}: {e}")
                    error_data["failed_files"]["perm_failed_keys"][change_type].append(key)
                    continue
                except eodhp_utils.pulsar.messages.ClientError as e:
                    logging.error(f"Temporary error processing {change_type} key {key}: {e}")
                    output_data["failed_files"]["temp_failed_keys"][change_type].append(key)
                    continue
                except Exception as e:
                    logging.exception(f"Permanent error processing {change_type} key {key}: {e}")
                    output_data["failed_files"]["perm_failed_keys"][change_type].append(key)
                    continue

        return output_data, error_data


class DatasetDCATMessager(CatalogueChangeMessager):
    """
    Generates basic DCAT for catalogue entries. Supports Catalogs and Collections and is
    intended only to be sufficient for finding QA information linked to a dataset.
    """

    def consume_update(
        self,
        cat_path: str,
        file_body: Union[dict, str],
        **kwargs,
    ) -> Sequence[CatalogueChangeMessager.Action]:
        # Only concerned with STAC data here
        if not isinstance(file_body, dict) or "stac_version" not in file_body:
            return None

        # Generate the linked data representation.
        ld_graph = self.generate(file_body)

        # Save this to a bucket where the annotations service will find it.
        if ld_graph is None:
            return None
        else:
            ld_ttl = ld_graph.serialize(format="turtle")
            return (
                CatalogueChangeMessager.S3UploadAction(
                    "annotations-bucket", "/datasets/" + cat_path, ld_ttl
                ),
            )

    def generate(self, stac: dict) -> Graph:
        if stac.get("type") not in ("Catalog", "Collection"):
            return None

        try:
            stac_obj = pystac.read_dict(stac)
        except STACTypeError:
            return None

        if isinstance(stac_obj, Collection):
            return self.generate_for_collection(stac_obj)
        elif isinstance(stac_obj, Catalog):
            return self.generate_for_catalog(stac_obj)
        else:
            return None

    def generate_for_catalog(self, stac: Catalog) -> Graph:
        g = Graph()
        self_uriref = URIRef(stac.get_self_href())
        g.add((self_uriref, RDF.type, DCAT.Catalog))
        g.add((self_uriref, DCTERMS.identifier, self_uriref))

        return g

    def generate_for_collection(self, stac: Collection) -> Graph:
        g = Graph()
        self_uriref = URIRef(stac.get_self_href())
        g.add((self_uriref, RDF.type, DCAT.Dataset))
        g.add((self_uriref, DCTERMS.identifier, self_uriref))

        # The STAC Scientific extensions specifies that DOIs can be included as rel=cite-as links
        # (in URL form) or a sci:doi property (in bare form, such as 10.5270/S2_-742ikth).
        #
        # cite-as might not be a DOI, however, as it can be used more generally.
        cite_as = stac.get_single_link("cite-as").absolute_href
        sys.stderr.write(f"{cite_as=}")
        sci_doi = stac.extra_fields.get("sci:doi")

        if cite_as is not None:
            g.add((self_uriref, DCTERMS.identifier, URIRef(cite_as)))

            if cite_as.startswith(DOI_URL_PREFIX) and sci_doi is None:
                sci_doi = cite_as[len(DOI_URL_PREFIX) :]

        if sci_doi is not None:
            g.add((self_uriref, DCTERMS.identifier, Literal(sci_doi)))

        return g
