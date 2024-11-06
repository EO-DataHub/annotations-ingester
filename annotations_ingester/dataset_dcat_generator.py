import sys
from typing import Sequence

import pystac
from pystac import Catalog, Collection, STACTypeError
from rdflib import DCAT, DCTERMS, RDF, Graph, Literal, URIRef

from eodhp_utils.messagers import CatalogueSTACChangeMessager, Messager

DOI_URL_PREFIX = "https://doi.org/"
CATALOGUE_PUBLIC_BUCKET_PREFIX = "/catalogue/"


class DatasetDCATMessager(CatalogueSTACChangeMessager):
    """
    Generates basic DCAT for catalogue entries. Supports Catalogs and Collections and is
    intended only to be sufficient for finding QA information linked to a dataset.

    The output is sent to the cataloge public static files bucket under a path matching the
    catalogue API endpoint for the dataset. For example:
        /catalogue/
    """

    def __init__(self, catalogue_public_bucket: str):
        self._dest_bucket = catalogue_public_bucket

    def process_update_stac(
        self,
        cat_path: str,
        stac: dict,
        **kwargs,
    ) -> Sequence[Messager.Action]:
        ld_graph = self.generate_dcat(stac)

        if ld_graph is None:
            return None
        else:
            ld_ttl = ld_graph.serialize(format="turtle")
            ld_jsonld = ld_graph.serialize(format="json-ld")

            # This saves the output directly to the catalogue public bucket. With a little nginx
            # config, this means it can appear at, say,
            #  /api/catalogue/stac/catalogs/my-catalog/collections/collection.jsonld
            return (
                Messager.S3UploadAction(
                    bucket=self._dest_bucket,
                    key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".ttl",
                    file_body=ld_ttl,
                    mime_type="text/turtle",
                ),
                Messager.S3UploadAction(
                    bucket=self._dest_bucket,
                    key=CATALOGUE_PUBLIC_BUCKET_PREFIX + cat_path + ".jsonld",
                    file_body=ld_jsonld,
                    mime_type="application/ld+json",
                ),
            )

    def generate_dcat(self, stac: dict) -> Graph:
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

    # These are here because we have only a stub for Messager with no implemetations.
    # An intermediate subclass will implement these in a real version.
    def process_msg(self, msg) -> Sequence[Messager.Action]:
        return None

    def process_delete(
        self, bucket: str, key: str, id: str, source: str, target: str
    ) -> Sequence[Messager.Action]:
        return None
