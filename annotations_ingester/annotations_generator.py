from typing import Sequence

from eodhp_utils.messagers import CatalogueChangeBodyMessager, Messager
from rdflib import ConjunctiveGraph, Graph, URIRef
from rdflib.namespace import OWL, RDF


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
    ) -> Sequence[Messager.Action]:

        short_path = "/".join(cat_path.split("/")[:-1])

        graph = Graph()
        graph.parse(entry_body, format="trig")

        uuid = get_uuid_from_graph(entry_body)

        if uuid:
            cache_control_length = 60 * 60 * 24 * 7  # 1 week
        else:
            cache_control_length = 0

        turtle = graph.serialize(format="turtle")
        jsonld = graph.serialize(format="json-ld")

        key_root = f"catalogues{short_path}/annotations/{uuid}"

        return [
            Messager.S3UploadAction(
                key=key_root + ".ttl",
                file_body=turtle,
                mime_type="text/turtle",
                cache_control=f"max-age={cache_control_length}",
                bucket=self.output_bucket,
            ),
            Messager.S3UploadAction(
                key=key_root + ".jsonld",
                file_body=jsonld,
                mime_type="application/ld+json",
                cache_control=f"max-age={cache_control_length}",
                bucket=self.output_bucket,
            ),
        ]


def get_uuid_from_graph(file_contents: str) -> str:
    """Parses file data to find UUID"""

    graph = ConjunctiveGraph()
    graph.parse(data=file_contents, format="trig")

    # The entire QA run outputs are represented by a resource of type `eodhqa:EODHQualityMeasurementDataset`
    # There should be only one.
    eodhqa = URIRef("https://eodatahub.org.uk/api/ontologies/qa/")
    measurement_dset = next(
        graph.triples((None, RDF.type, eodhqa + "EODHQualityMeasurementDataset"))
    )[0]

    # The eodhqa:EODHQualityMeasurementDataset should always have an `owl:sameAs` triple with its UUID.
    uuid_ref = next(
        obj
        for obj in list(graph.objects(measurement_dset, OWL.sameAs))
        if str(obj).startswith("urn:uuid:")
    )
    uuid = str(uuid_ref)[len("urn:uuid:") :]

    return uuid
