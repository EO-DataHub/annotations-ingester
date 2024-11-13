import logging
import os

import boto3
from eodhp_utils.runner import run

from annotations_ingester.annotations_generator import AnnotationsMessager
from annotations_ingester.dataset_dcat_generator import DatasetDCATMessager


def main():
    if os.getenv("TOPIC"):
        identifier = "_" + os.getenv("TOPIC")
    else:
        identifier = ""

    session = boto3.session.Session(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    s3_client = session.client("s3")

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    destination_bucket = os.environ.get("S3_BUCKET")

    annotations_messager = AnnotationsMessager(
        s3_client=s3_client, output_bucket=destination_bucket
    )
    datasets_messager = DatasetDCATMessager(s3_client=s3_client, output_bucket=destination_bucket)

    run(
        {
            "transformed-annotations": annotations_messager,
            f"transformed{identifier}": datasets_messager,
        },
        "annotations-ingester",
    )


if __name__ == "__main__":
    main()
