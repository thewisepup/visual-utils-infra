import pulumi
from pulumi_aws import s3, iam, lambda_

stack = pulumi.get_stack()

# Create S3 bucket for deployable Lambda code
lambda_deployment_bucket = s3.BucketV2(
    f"lambda-deployment-{stack}",
)

# Create S3 bucket for RGB Splitting user uploads
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

# Create S3 bucket for processed RGB Splitting uploads
rgb_splitting_processed_bucket = s3.BucketV2(
    f"rgb-splitting-processed-{stack}",
)
s3.BucketLifecycleConfigurationV2(
    f"rgb-splitting-processed-lifecycle-{stack}",
    bucket=rgb_splitting_processed_bucket.id,
    rules=[
        {"status": "Enabled", "id": "delete-after-1-day", "expiration": {"days": 1}}
    ],
)
s3.BucketCorsConfigurationV2(
    f"rgb-splitting-processed-cors-{stack}",
    bucket=rgb_splitting_processed_bucket.id,
    cors_rules=[
        {
            "allowed_headers": ["*"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
            "allowed_origins": allowed_origins,
            "expose_headers": ["ETag"],
        }
    ],
)

# Create RGB Splitting Lambda
lambda_assume_role_policy = iam.get_policy_document(
    statements=[
        {
            "effect": "Allow",
            "principals": [
                {
                    "type": "Service",
                    "identifiers": ["lambda.amazonaws.com"],
                }
            ],
            "actions": ["sts:AssumeRole"],
        }
    ]
)

rgb_splitting_lambda_role = iam.Role(
    "rgb_splitting_lambda_role",
    name="rgb_splitting_lambda_role",
    assume_role_policy=lambda_assume_role_policy.json,
)

# Add S3 permissions for rgb_splitting_lambda_role
rgb_splitting_lambda_s3_policy = iam.Policy(
    "rgb_splitting_lambda_s3_policy",
    policy=pulumi.Output.all(
        rgb_splitting_user_upload_bucket.arn, rgb_splitting_processed_bucket.arn
    ).apply(
        lambda args: {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": [args[0], f"{args[0]}/*"],
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:PutObject"],
                    "Resource": [f"{args[1]}/*"],
                },
            ],
        }
    ),
)
iam.RolePolicyAttachment(
    "rgb_splitting_lambda_s3_policy_attachment",
    role=rgb_splitting_lambda_role.name,
    policy_arn=rgb_splitting_lambda_s3_policy.arn,
)

iam.RolePolicyAttachment(
    "rgb_splitting_lambda_logging_policy",
    role=rgb_splitting_lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

rgb_splitting_lambda = lambda_.Function(
    f"rgb_splitting_lambda-{stack}",
    s3_bucket=lambda_deployment_bucket.bucket,
    s3_key="rgb_splitting_lambda.zip",
    name=f"rgb_splitting_lambda-{stack}",
    role=rgb_splitting_lambda_role.arn,
    handler="rgb_splitting_lambda.lambda_handler",
    runtime="python3.11",
    environment={
        "variables": {"DESTINATION_BUCKET": rgb_splitting_processed_bucket.bucket}
    },
    timeout=60,
)
lambda_.Permission(
    "allow_rgb_splitting_lambda_execution_from_s3_bucket",
    statement_id="AllowExecutionFromS3Bucket",
    action="lambda:InvokeFunction",
    function=rgb_splitting_lambda.arn,
    principal="s3.amazonaws.com",
    source_arn=rgb_splitting_user_upload_bucket.arn,
)

s3.BucketNotification(
    "bucket_notification",
    bucket=rgb_splitting_user_upload_bucket.id,
    lambda_functions=[
        {
            "lambda_function_arn": rgb_splitting_lambda.arn,
            "events": ["s3:ObjectCreated:*"],
        }
    ],
)

# Create IAM user for Next.js app
nextjs_app_iam_user = iam.User(
    f"nextjs-app-user-{stack}",
)

rgb_splitting_user_upload_read_write_policy = iam.Policy(
    f"rgb_splitting_user_upload_read_write_policy-{stack}",
    policy=pulumi.Output.all(
        rgb_splitting_user_upload_bucket.arn, rgb_splitting_processed_bucket.arn
    ).apply(
        lambda arns: {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:PutObject", "s3:GetObject", "s3:HeadObject"],
                    "Resource": [f"{arns[0]}/*"],
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:HeadObject"],
                    "Resource": [f"{arns[1]}/*"],
                },
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
