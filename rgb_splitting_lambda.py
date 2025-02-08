import os
import boto3

DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
S3_CLIENT = boto3.client("s3")
object_keys = []


def process_record(record):
    s3_object = record["s3"]
    source_bucket = s3_object["bucket"]["name"]
    object_key = s3_object["object"]["key"]
    object_keys.append(object_key)

    response = S3_CLIENT.get_object(Bucket=source_bucket, Key=object_key)
    file_data = response["Body"].read()

    # TODO perform RGB splitting

    for color in ["red", "green", "blue"]:
        S3_CLIENT.put_object(
            Bucket=DESTINATION_BUCKET, Key=f"{color}/{object_key}", Body=file_data
        )
        print(f"Uploaded {color}/{object_key} to bucket {DESTINATION_BUCKET}")


def lambda_handler(event):
    print(f"Received event: {event}")

    for record in event["Records"]:
        process_record(record)

    return {
        "statusCode": 200,
        "body": f"Processed the following s3Objects: {', '.join(object_keys)}",
    }
