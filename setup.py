import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="twitch_aws_image_rekognition",
    version="0.0.1",

    description="An empty CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "twitch_aws_image_rekognition"},
    packages=setuptools.find_packages(where="twitch_aws_image_rekognition"),

    install_requires=[
        "aws-cdk.core==1.92.0",
        "aws-cdk.aws_iam==1.92.0",
        "aws-cdk.aws_sqs==1.92.0",
        "aws-cdk.aws_sns==1.92.0",
        "aws-cdk.aws_sns_subscriptions==1.92.0",
        "aws-cdk.aws_s3==1.92.0",
        "aws-cdk.aws_events==1.92.0",
        "aws-cdk.aws_events_targets==1.92.0",
        "aws-cdk.aws_dynamodb==1.92.0",
        "aws-cdk.aws_apigateway==1.92.0",
        "cdk-spa-deploy==1.92.0",
        "botocore",
        "boto3",
        "aws-cdk.aws-lambda==1.92.0",
        "aws-cdk.aws-lambda-event-sources==1.92.0",
        "aws_cdk.aws_s3_deployment==1.92.0",
        "aws_cdk.aws_apigateway==1.92.0",
        "aws_cdk.aws_cognito==1.92.0",
        "aws_cdk.aws_s3_notifications==1.92.0",

    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
