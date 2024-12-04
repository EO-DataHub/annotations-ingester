import os

import click
from eodhp_utils.runner import (
    get_boto3_session,
    log_component_version,
    run,
    setup_logging,
)

from annotations_ingester.annotations_generator import AnnotationsMessager
from annotations_ingester.dataset_dcat_generator import DatasetDCATMessager


@click.command
@click.option("--takeover", "-t", is_flag=True, default=False, help="Run in takeover mode.")
@click.option("-v", "--verbose", count=True)
@click.option("--pulsar-url")
def cli(takeover: bool, verbose: int, pulsar_url=None):
    setup_logging(verbosity=verbose)
    log_component_version("annotations_ingester")

    if os.getenv("TOPIC"):
        identifier = "_" + os.getenv("TOPIC")
    else:
        identifier = ""

    session = get_boto3_session()
    s3_client = session.client("s3")

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
        takeover_mode=takeover,
        pulsar_url=pulsar_url,
    )


if __name__ == "__main__":
    cli()
