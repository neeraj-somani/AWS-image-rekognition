import json
from aws_cdk import core as cdk
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_dep
import aws_cdk.aws_lambda as lb
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda_event_sources as event_sources
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_cognito as cognito
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_s3_notifications as s3n

# S3 bucket name for image storages
IMG_BUCKET_NAME = "twitch-rekn-imagebucket"
RESIZED_IMG_BUCKET_NAME = f"{IMG_BUCKET_NAME}-resized"

class BackendStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ## =====================================================================================
        ## Image Bucket
        ## =====================================================================================
        # below line creates the S3 bucket
        image_bucket = s3.Bucket(self, IMG_BUCKET_NAME, removal_policy=cdk.RemovalPolicy.DESTROY)
        # below line brings the output back to cloudformation and to log files, basically bucket name
        cdk.CfnOutput(self, "imageBucket", value=image_bucket.bucket_name)
        
        ## =====================================================================================
        ## Thumbnail Bucket
        ## =====================================================================================
        resized_image_bucket = s3.Bucket(
            self, RESIZED_IMG_BUCKET_NAME, removal_policy=cdk.RemovalPolicy.DESTROY
        )
        cdk.CfnOutput(self, "resizedBucket", value=resized_image_bucket.bucket_name)

        resized_image_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
            allowed_origins=["*"],
            allowed_headers=["*"],
            max_age=3000,
        )
        
        
        
        
        ## =====================================================================================
        ## Amazon DynamoDB table for storing image labels
        ## =====================================================================================
        
        # creating partition key for dynamodb table
        partition_key = dynamodb.Attribute(name="image", type=dynamodb.AttributeType.STRING)
        # creating dynamodb table 
        table = dynamodb.Table(
            self,
            "ImageLabels",
            partition_key=partition_key,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        # below line brings the output back to cloudformation and to log files, basically dynamodb table name
        cdk.CfnOutput(self, "ddbTable", value=table.table_name)
        
        ## =====================================================================================
        ## Building A layer to enable the PIL library in our Rekognition Lambda function
        ## =====================================================================================
        layer = lb.LayerVersion(
            self,
            "pil",
            code=lb.Code.from_asset("reklayer"),
            compatible_runtimes=[lb.Runtime.PYTHON_3_7],
            license="Apache-2.0",
            description="A layer to enable the PIL library in our Rekognition Lambda",
        )
        
        ## =====================================================================================
        ## Building our AWS Lambda Function; compute for our serverless microservice
        ## =====================================================================================
        
        # below lines create Lambda function
        rek_fn = lb.Function(
            self,
            "rekognitionFunction",
            code=lb.Code.from_asset("rekognitionLambda"), ## here, "rekognitionLambda" is the folder path in your project directory where you have defined lambda function, CDK creates a zip file of our code and run it in the runtime env
            runtime=lb.Runtime.PYTHON_3_7,
            handler="index.handler",
            timeout=cdk.Duration.seconds(30),
            memory_size=1024,
            layers=[layer],
            environment={
                "TABLE": table.table_name,
                "BUCKET": image_bucket.bucket_name,
                "THUMBBUCKET": resized_image_bucket.bucket_name,
            },
        )
        
        '''
        few lambda job definitions
        1. pull the image from s3 bucket
        2. send it to amazon rekognition service for image detection
        3. hence, lambda need some permissions to perform these tasks
        '''
        # below line gives read permission to lambda function to read images from S3 bucket
        image_bucket.grant_read(rek_fn)
        
        # below line gives write permission to lambda function to write resized images to resized S3 bucket
        resized_image_bucket.grant_write(rek_fn)
        
        # below line gives write permission to lambda function to write images details to dynamodb table
        table.grant_write_data(rek_fn)
        
        ## below line defines IAM role policy for lambda function to perform "detectLabels" task on reKognition service 
        rek_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW, actions=["rekognition:DetectLabels"], resources=["*"]
            )
        )
        
        ## Need to test below line that allow S3 to trigger lambda function as soon as object gets created
        rek_fn.add_event_source(event_sources.S3EventSource(bucket=image_bucket, events=[s3.EventType.OBJECT_CREATED]))
        
        ## =====================================================================================
        ## Lambda for Synchronous Front End
        ## =====================================================================================
        
        serviceFn = lb.Function(
            self,
            "serviceFunction",
            code=lb.Code.from_asset("servicelambda"), ## folder name
            runtime=lb.Runtime.PYTHON_3_7,
            handler="index.handler",  ## file name and function name
            environment={
                "TABLE": table.table_name,
                "BUCKET": image_bucket.bucket_name,
                "RESIZEDBUCKET": resized_image_bucket.bucket_name,
            },
        )

        image_bucket.grant_write(serviceFn)
        resized_image_bucket.grant_write(serviceFn)
        table.grant_read_write_data(serviceFn)
        
        
        
