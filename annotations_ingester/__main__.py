import os

from annotations_ingester.dataset_dcat_generator import DatasetDCATMessager
from eodhp_utils.messagers import CatalogueSTACChangeMessager
from eodhp_utils.runner import run

from annotations_ingester.annotations_generator import AnnotationsMessager


def main():
    if os.getenv("TOPIC"):
        identifier = "_" + os.getenv("TOPIC")
    else:
        identifier = ""

    destination_bucket = os.environ.get('S3_BUCKET')
    annotations_messager = AnnotationsMessager(destination_bucket)
    datasets_messager = DatasetDCATMessager(destination_bucket)

    run(
        {
            "transformed-annotations": annotations_messager,
            f"harvested{identifier}": datasets_messager,
        },
        "annotations-ingester",
    )


if __name__ == "__main__":
    main()
