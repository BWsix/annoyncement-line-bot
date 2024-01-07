import os
import logging
import typing

import boto3
from boto3_type_annotations.s3 import ServiceResource, Client

logger = logging.getLogger()
logger.level = logging.INFO


def upload_to_s3(file_path: str):
    logger.info(f"upload_to_s3(file_path: {file_path})")

    bucket_name = os.getenv("S3_BUCKET_NAME") or ""
    s3 = typing.cast(ServiceResource, boto3.resource("s3"))
    s3Client = typing.cast(Client, boto3.client("s3"))
    bucket = s3.Bucket(bucket_name)

    file_name = os.path.basename(file_path)

    # TODO: using file name as key may introduce collision since they're the hash of the content
    bucket.upload_file(Filename=file_path, Key=file_name)
    signedUrl = typing.cast(str, s3Client.generate_presigned_url('get_object', {
        "Bucket": bucket.name,
        "Key": file_name,
    }))
    logger.info(f"Upload completed, url: {signedUrl}")

    return signedUrl
