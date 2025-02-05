import pulumi
from pulumi_aws import s3, iam

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

allowed_origins = (
    ["http://localhost:3000"]
    if stack == "dev"
    else [
        "https://*.vercel.app",
    ]
)

s3.BucketCorsConfigurationV2(
    f"rgb-splitting-user-upload-cors-{stack}",
    bucket=rgb_splitting_user_upload_bucket.id,
    cors_rules=[
        {
            "allowed_headers": ["*"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
            "allowed_origins": allowed_origins,
            "expose_headers": ["ETag"],
        }
    ],
)

nextjs_app_iam_user = iam.User(
    f"nextjs-app-user-{stack}",
)

rgb_splitting_user_upload_read_write_policy = iam.Policy(
    f"rgb_splitting_user_upload_read_write_policy-{stack}",
    policy=rgb_splitting_user_upload_bucket.arn.apply(
        lambda arn: {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:PutObject", "s3:GetObject"],
                    "Resource": [f"{arn}/*"],
                }
            ],
        }
    ),
)

nextjs_app_policy_attachment = iam.UserPolicyAttachment(
    f"nextjs-app-policy-attachment-{stack}",
    user=nextjs_app_iam_user.name,
    policy_arn=rgb_splitting_user_upload_read_write_policy.arn,
)

nextjs_app_iam_user_access_key = iam.AccessKey(
    f"nextjs-app-access-key-{stack}",
    user=nextjs_app_iam_user.name,
)

pulumi.export("nextjs_app_iam_user_access_key_id", nextjs_app_iam_user_access_key.id)
pulumi.export(
    "nextjs_app_iam_user_secret_access_key", nextjs_app_iam_user_access_key.secret
)
