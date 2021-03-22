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
WEBSITE_BUCKET_NAME = "cdk-rekn-publicbucket"


class BackendStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ## =====================================================================================
        ## Image Bucket
        ## =====================================================================================
        # below line creates the S3 bucket
        image_bucket = s3.Bucket(self, IMG_BUCKET_NAME , bucket_name=IMG_BUCKET_NAME, removal_policy=cdk.RemovalPolicy.DESTROY)
        # below line brings the output back to cloudformation and to log files, basically bucket name
        cdk.CfnOutput(self, "imageBucket", value=image_bucket.bucket_name)
        
        image_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
            allowed_origins=["*"],
            allowed_headers=["*"],
            max_age=3000,
        )
        
        ## =====================================================================================
        ## Thumbnail Bucket
        ## =====================================================================================
        resized_image_bucket = s3.Bucket(
            self, RESIZED_IMG_BUCKET_NAME, bucket_name=RESIZED_IMG_BUCKET_NAME, removal_policy=cdk.RemovalPolicy.DESTROY
        )
        cdk.CfnOutput(self, "resizedBucket", value=resized_image_bucket.bucket_name)

        resized_image_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
            allowed_origins=["*"],
            allowed_headers=["*"],
            max_age=3000,
        )
        
        ## =====================================================================================
        ## Construct to create our Amazon S3 Bucket to host our website
        ## =====================================================================================
        
        web_bucket = s3.Bucket(
            self,
            WEBSITE_BUCKET_NAME,
            bucket_name=WEBSITE_BUCKET_NAME,
            website_index_document="index.html",
            website_error_document="index.html",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            # uncomment this and delete the policy statement below to allow public access to our
            # static website
            public_read_access=True,
        )

        # web_policy_statement = iam.PolicyStatement(
        #     actions=["s3:GetObject"],
        #     resources=[web_bucket.arn_for_objects("*")],
        #     principals=[iam.AnyPrincipal()],
        #     conditions={"IpAddress": {"aws:SourceIp": ["172.31.16.57"]}}, 
        # )

        #web_bucket.add_to_resource_policy(web_policy_statement)

        cdk.CfnOutput(self, "bucketURL", value=web_bucket.bucket_website_domain_name)
        
        ## =====================================================================================
        ## Deploy site contents to S3 Bucket
        ## =====================================================================================
        
        s3_dep.BucketDeployment(
            self,
            "DeployWebsite",
            sources=[s3_dep.Source.asset("./public")],
            destination_bucket=web_bucket,
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
        ## Building our AWS Lambda Function; compute for our serverless microservice - Episode 1
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
                "RESIZEDBUCKET": resized_image_bucket.bucket_name,
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
        
        ## This line added only for testing purposes. Commented out as now, we are retrieving images from SQS
        ## rek_fn.add_event_source(event_sources.S3EventSource(bucket=image_bucket, events=[s3.EventType.OBJECT_CREATED]))
        
        ## =====================================================================================
        ## Lambda for Synchronous Front End that connects to API Gateway - Episode 3
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
        
        ## =====================================================================================
        ## Creating the API Gateway resource and connecting to lambda function - Episode 3
        ## =====================================================================================
        
        cors_options = apigw.CorsOptions(
            allow_origins=apigw.Cors.ALL_ORIGINS, 
            allow_methods=apigw.Cors.ALL_METHODS
        )
        
        ## This creates an API Gateway integration with Lambda function
        
        api = apigw.LambdaRestApi(
            self,
            "imageAPI",
            default_cors_preflight_options=cors_options,
            handler=serviceFn,
            proxy=False, ## here API gateway is responsible for all the reponse for any request that comes to it
            
        )
        
        
        ## =====================================================================================
        ## This construct connects Amazon API Gateway with AWS Lambda Integration - Episode 3
        ## =====================================================================================
        # New Amazon API Gateway with AWS Lambda Integration
        success_response = apigw.IntegrationResponse(
            status_code="200",
            response_parameters={"method.response.header.Access-Control-Allow-Origin": "'*'"},
        )
        error_response = apigw.IntegrationResponse(
            selection_pattern="(\n|.)+",
            status_code="500",
            response_parameters={"method.response.header.Access-Control-Allow-Origin": "'*'"},
        )

        request_template = json.dumps(
            {
                "action": "$util.escapeJavaScript($input.params('action'))",
                "key": "$util.escapeJavaScript($input.params('key'))",
            }
        )

        lambda_integration = apigw.LambdaIntegration(
            serviceFn,
            proxy=False,
            request_parameters={
                "integration.request.querystring.action": "method.request.querystring.action",
                "integration.request.querystring.key": "method.request.querystring.key",
            },
            request_templates={"application/json": request_template},
            passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_TEMPLATES,
            integration_responses=[success_response, error_response],
        )
        

        ## =====================================================================================
        ## Create Cognito User Pool Authentication - Episode 4
        ## =====================================================================================
        
        auto_verified_attrs = cognito.AutoVerifiedAttrs(email=True)
        sign_in_aliases = cognito.SignInAliases(email=True, username=True)
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            self_sign_up_enabled=True, ##  Allow users to sign up
            auto_verify=auto_verified_attrs, ## Verify email addresses by sending a verification code
            sign_in_aliases=sign_in_aliases, ## Set email as an alias
        )

        user_pool_client = cognito.UserPoolClient(
            self, "UserPoolClient", 
            user_pool=user_pool, 
            generate_secret=False ## Don't need to generate secret for web app running on browsers
        )

        identity_pool = cognito.CfnIdentityPool(
            self,
            "ImageRekognitionIdentityPool",
            allow_unauthenticated_identities=False, ## Don't allow unathenticated users
            cognito_identity_providers=[
                {
                    "clientId": user_pool_client.user_pool_client_id,
                    "providerName": user_pool.user_pool_provider_name,
                }
            ],
        )
        
        
        ## =====================================================================================
        ## Connecting API Gateway with Cognito - Episode 4
        ## =====================================================================================
        
        auth = apigw.CfnAuthorizer(
            self,
            "ApiGatewayAuthorizer",
            name="customer-authorizer",
            identity_source="method.request.header.Authorization",
            provider_arns=[user_pool.user_pool_arn],
            rest_api_id=api.rest_api_id,
            type="COGNITO_USER_POOLS",
        )
        
        ## =====================================================================================
        ## Creating IAM role that provides necessary permissions to cognito - Episode 4
        ## =====================================================================================

        assumed_by = iam.FederatedPrincipal(
            "cognito-identity.amazon.com",
            conditions={
                "StringEquals": {"cognito-identity.amazonaws.com:aud": identity_pool.ref},
                "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"},
            },
            assume_role_action="sts:AssumeRoleWithWebIdentity",
        )
        
        # here we are creating role and attached assumed_by statement
        
        authenticated_role = iam.Role(
            self,
            "ImageRekognitionAuthenticatedRole",
            assumed_by=assumed_by,
        )
        
        ## =====================================================================================
        ## IAM Policy Statements - Episode 4
        ## =====================================================================================
        
        # IAM policy granting users permission to upload, download and delete their own pictures
        policy_statement = iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject"],
            effect=iam.Effect.ALLOW,
            resources=[
                image_bucket.bucket_arn + "/private/${cognito-identity.amazonaws.com:sub}/*",
                image_bucket.bucket_arn + "/private/${cognito-identity.amazonaws.com:sub}/",
                resized_image_bucket.bucket_arn
                + "/private/${cognito-identity.amazonaws.com:sub}/*",
                resized_image_bucket.bucket_arn + "/private/${cognito-identity.amazonaws.com:sub}/",
            ],
        )
        
        authenticated_role.add_to_policy(policy_statement)
        
        # IAM policy granting users permission to list their pictures
        list_policy_statement = iam.PolicyStatement(
            actions=["s3:ListBucket"],
            effect=iam.Effect.ALLOW,
            resources=[image_bucket.bucket_arn, resized_image_bucket.bucket_arn],
            conditions={
                "StringLike": {"s3:prefix": ["private/${cognito-identity.amazonaws.com:sub}/*"]}
            },
        )

        authenticated_role.add_to_policy(list_policy_statement)

        
        ## =====================================================================================
        ## # Attach role to our Identity Pool - Episode 4
        ## =====================================================================================
        
        cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoleAttachment",
            identity_pool_id=identity_pool.ref,
            roles={"authenticated": authenticated_role.role_arn},
        )

        # export values of Cognito for easier access at cloudformation output
        
        cdk.CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        cdk.CfnOutput(self, "AppClientId", value=user_pool_client.user_pool_client_id)
        cdk.CfnOutput(self, "IdentityPoolId", value=identity_pool.ref)
        
        
        
        
        ## =====================================================================================
        ## API Gateway - adding resource and request methods - Episode 3
        ## =====================================================================================
        
        ## Here we are using our earlier created "API gateway" and adding a resource to it
        imageAPI = api.root.add_resource("images")
        
        success_resp = apigw.MethodResponse(
            status_code="200",
            response_parameters={"method.response.header.Access-Control-Allow-Origin": True},
        )
        error_resp = apigw.MethodResponse(
            status_code="500",
            response_parameters={"method.response.header.Access-Control-Allow-Origin": True},
        )

        # this is GET method for /images resource
        get_method = imageAPI.add_method(
            "GET",
            lambda_integration,
            #authorization_type=apigw.AuthorizationType.COGNITO,
            request_parameters={
                "method.request.querystring.action": True,
                "method.request.querystring.key": True,
            },
            method_responses=[success_resp, error_resp],
        )
        # this is DELETE method for /images resource
        delete_method = imageAPI.add_method(
            "DELETE",
            lambda_integration,
            #authorization_type=apigw.AuthorizationType.COGNITO,
            request_parameters={
                "method.request.querystring.action": True,
                "method.request.querystring.key": True,
            },
            method_responses=[success_resp, error_resp],
        )
        
        # Override the authorizer id because it doesn't work when defininting it as a param
        # in above add_method
        get_method_resource = get_method.node.find_child("Resource")
        get_method_resource.add_property_override("AuthorizerId", auth.ref)
        delete_method_resource = delete_method.node.find_child("Resource")
        delete_method_resource.add_property_override("AuthorizerId", auth.ref)
        
        
        ## =====================================================================================
        ## Building SQS queue and DeadLetter Queue - Episode 6
        ## =====================================================================================
        

        dl_queue = sqs.Queue(
            self,
            "ImageDLQueue",
            queue_name="ImageDLQueue",
        )

        dl_queue_opts = sqs.DeadLetterQueue(max_receive_count=2, queue=dl_queue)

        queue = sqs.Queue(
            self,
            "ImageQueue",
            queue_name="ImageQueue",
            visibility_timeout=cdk.Duration.seconds(30),
            receive_message_wait_time=cdk.Duration.seconds(20),
            dead_letter_queue=dl_queue_opts,
        )
        
        ## =====================================================================================
        ## S3 Bucket Create Notification to SQS - Episode 6
        ## Whenever an image is uploaded add it to the queue
        ## =====================================================================================

        image_bucket.add_object_created_notification(
            s3n.SqsDestination(queue), s3.NotificationKeyFilter(prefix="private/")
        )
        
        ## =====================================================================================
        ## Allow Lambda(Rekognition) to consume messages from SQS
        ## =====================================================================================
        rek_fn.add_event_source(event_sources.SqsEventSource(queue=queue))
        