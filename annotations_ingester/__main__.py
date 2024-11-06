import os

from eodhp_utils.messagers import CatalogueSTACChangeMessager
from eodhp_utils.runner import run

from annotations_ingester.annotations_generator import AnnotationsMessager


def main():
    if os.getenv("TOPIC"):
        identifier = "_" + os.getenv("TOPIC")
    else:
        identifier = ""

    annotations_messager = AnnotationsMessager("hc-test-bucket-can-be-deleted")
    datasets_messager = CatalogueSTACChangeMessager()

    run(
        {
            "transformed-annotations": annotations_messager,
            f"harvested{identifier}": datasets_messager,
        },
        "annotations-ingester",
    )


if __name__ == "__main__":
    main()
