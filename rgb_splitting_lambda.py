def lambda_handler(event, context):
    print(f"Received event: {event}")
    object_keys = []
    for record in event["Records"]:
        s3_object = record["s3"]
        bucket = s3_object["bucket"]["name"]
        object_key = s3_object["object"]["key"]
        print(f"Processing s3 Object {object_key} from bucket {bucket}")
    return {
        "statusCode": 200,
        "body": f"Processed the following s3Objects: {', '.join(object_keys)}",
    }
