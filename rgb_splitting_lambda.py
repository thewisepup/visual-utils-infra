import os
import boto3
import logging
from PIL import Image
from io import BytesIO
import numpy as np
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
S3_CLIENT = boto3.client("s3")
object_keys = []


def create_channel_images(original_image):
    """
    Creates separate red, green, and blue channel images.

    Args:
        original_image: PIL Image in RGB format

    Returns:
        tuple: (red_image, green_image, blue_image) as PIL Images
    """
    red_img_array = np.array(original_image)
    red_img_array[:, :, 1] = 0
    red_img_array[:, :, 2] = 0
    red_img = Image.fromarray(red_img_array)

    green_img_array = np.array(original_image)
    green_img_array[:, :, 0] = 0
    green_img_array[:, :, 2] = 0
    green_img = Image.fromarray(green_img_array)

    blue_img_array = np.array(original_image)
    blue_img_array[:, :, 0] = 0
    blue_img_array[:, :, 1] = 0
    blue_img = Image.fromarray(blue_img_array)

    return red_img, green_img, blue_img


def upload_processed_image(image, destination_key):
    """
    Uploads a processed PIL Image to an S3 bucket.

    Args:
        image (PIL.Image): The processed image to upload
        destination_key (str): The S3 key (path) where the image will be stored
    """
    try:
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        S3_CLIENT.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=destination_key,
            Body=buffer.getvalue(),
        )
        logger.info(
            f"Successfully uploaded {destination_key} to bucket {DESTINATION_BUCKET}"
        )
    except Exception as e:
        logger.error(f"Error uploading {destination_key} image: {str(e)}")
        raise


def process_record(record):
    s3_object = record["s3"]
    source_bucket = s3_object["bucket"]["name"]
    object_key = unquote_plus(s3_object["object"]["key"])
    object_keys.append(object_key)
    logger.info(f"Processing object {object_key} from bucket {source_bucket}")

    try:
        s3_response = S3_CLIENT.get_object(Bucket=source_bucket, Key=object_key)
        original_image = Image.open(BytesIO(s3_response["Body"].read())).convert("RGB")
        width, height = original_image.size
        logger.info(f"Successfully loaded image {object_key}: {width}x{height} pixels")

        red_img, green_img, blue_img = create_channel_images(original_image)
        logger.info(f"RGB Channel separation completed for {object_key}")

        for color, img in [("red", red_img), ("green", green_img), ("blue", blue_img)]:
            destination_key = f"{color}/{object_key}"
            upload_processed_image(img, destination_key)

    except Exception as e:
        logger.error(f"Error processing {object_key}: {str(e)}")
        raise


def lambda_handler(event, context):
    logger.info(f"Received event: {event}")

    try:
        for record in event["Records"]:
            process_record(record)

        result = f"Processed the following s3Objects: {', '.join(object_keys)}"
        logger.info(result)
        return {
            "statusCode": 200,
            "body": result,
        }
    except Exception as e:
        error_msg = f"Error in lambda_handler: {str(e)}"
        logger.error(error_msg)
        return {
            "statusCode": 500,
            "body": error_msg,
        }
