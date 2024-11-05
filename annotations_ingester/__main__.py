import os

from annotations_ingester.annotations_generator import AnnotationsMessager
from annotations_ingester.messagers import CatalogueSTACChangeMessager, run


def main():
    if os.getenv("TOPIC"):
        identifier = "_" + os.getenv("TOPIC")
    else:
        identifier = ""

    annotations_messager = AnnotationsMessager('hc-test-bucket-can-be-deleted')
    datasets_messager = CatalogueSTACChangeMessager()

    run({"transformed-annotations": annotations_messager, f"harvested{identifier}": datasets_messager}, 'annotations-ingester')


if __name__ == '__main__':
    main()