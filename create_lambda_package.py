import shutil
import subprocess
import os
import argparse

YELLOW = "\033[33m"
END_COLOR = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"

ENV_CONFIGS = {
    "dev": {
        "bucket": "lambda-deployment-dev-4ce10b1",
        "profile": "visual-utils-dev",
        "function_name": "rgb_splitting_lambda-dev",
    },
    "prod": {
        "bucket": "lambda-deployment-prod-4ce27e9",
        "profile": "visual-utils-prod",
        "function_name": "rgb_splitting_lambda-prod",
    },
}


def create_lambda_package(environment="dev"):
    if environment not in ENV_CONFIGS:
        print(f"{RED}Invalid environment. Please choose 'dev' or 'prod'{END_COLOR}")
        return

    CONFIG = ENV_CONFIGS[environment]

    os.environ["AWS_PROFILE"] = CONFIG["profile"]

    # Verify AWS Profile is set correctly
    aws_profile = os.environ.get("AWS_PROFILE")
    if aws_profile != CONFIG["profile"]:
        print(
            f"{RED}Error: AWS_PROFILE should be set to '{CONFIG['profile']}' for {environment} environment{END_COLOR}"
        )
        print(f"{YELLOW}Please run: export AWS_PROFILE={CONFIG['profile']}{END_COLOR}")
        return
    print(
        f"{YELLOW}Using {environment} environment with AWS Profile: {aws_profile}{END_COLOR}"
    )

    print(
        f"{YELLOW}Creating lambda package for {environment} environment...{END_COLOR}"
    )
    # Create a temporary directory for packaging
    if os.path.exists("package"):
        shutil.rmtree("package")
    os.makedirs("package")

    # Copy the lambda function file
    print(f"{YELLOW}Copying lambda function file...{END_COLOR}")

    shutil.copy2("rgb_splitting_lambda.py", "package/rgb_splitting_lambda.py")

    # Install dependencies into the package directory
    print(f"{YELLOW}Installing dependencies...{END_COLOR}")

    subprocess.check_call(
        [
            "pip3",
            "install",
            "--platform",
            "manylinux2014_x86_64",
            "--target",
            "package",
            "--implementation",
            "cp",
            "--python-version",
            "3.11",
            "--only-binary=:all:",
            "-r",
            "requirements.txt",
        ]
    )

    # Create the ZIP file
    print(f"{YELLOW}Creating ZIP file...{END_COLOR}")
    if os.path.exists("rgb_splitting_lambda.zip"):
        os.remove("rgb_splitting_lambda.zip")

    shutil.make_archive("rgb_splitting_lambda", "zip", "package")

    # Upload the ZIP file to S3
    print(f"{YELLOW}Uploading package to S3...{END_COLOR}")
    subprocess.check_call(
        [
            "aws",
            "s3",
            "cp",
            "rgb_splitting_lambda.zip",
            f"s3://{CONFIG['bucket']}",
        ]
    )

    # Update Lambda function code
    print(f"{YELLOW}Updating Lambda function code...{END_COLOR}")
    subprocess.check_call(
        [
            "aws",
            "lambda",
            "update-function-code",
            "--function-name",
            CONFIG["function_name"],
            "--s3-bucket",
            CONFIG["bucket"],
            "--s3-key",
            "rgb_splitting_lambda.zip",
        ]
    )

    # Clean up the temporary directory
    print(f"{YELLOW}Cleaning up temporary directory...{END_COLOR}")
    shutil.rmtree("package")
    os.remove("rgb_splitting_lambda.zip")

    print(f"{GREEN}Lambda package created and updated successfully.{END_COLOR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create and deploy Lambda package")
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="dev",
        help="Environment to deploy to (dev or prod)",
    )
    args = parser.parse_args()
    create_lambda_package(args.env)
