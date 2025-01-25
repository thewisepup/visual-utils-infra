"""An AWS Python Pulumi program"""

import pulumi
from pulumi_aws import s3

stack = pulumi.get_stack()

rgb_splitting_user_upload_bucket = s3.BucketV2(
    f"rgb-splitting-user-upload-{stack}",
    lifecycle_rules=[
        {"enabled": True, "id": "delete-after-1-day", "expirations": [{"days": 1}]}
    ],
)

# Export the name of the bucket
pulumi.export("bucket_name", rgb_splitting_user_upload_bucket.id)
