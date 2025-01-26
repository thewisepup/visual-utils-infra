import pulumi
from pulumi_aws import s3

stack = pulumi.get_stack()

rgb_splitting_user_upload_bucket = s3.BucketV2(
    f"rgb-splitting-user-upload-{stack}",
)
s3.BucketLifecycleConfigurationV2(
    f"rgb-splitting-user-upload-lifecycle-{stack}",
    bucket=rgb_splitting_user_upload_bucket.id,
    rules=[
        {"status": "Enabled", "id": "delete-after-1-day", "expiration": {"days": 1}}
    ],
)

pulumi.export("rgb_splitting_user_upload_bucket", rgb_splitting_user_upload_bucket.id)
