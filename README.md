
# Welcome to AWS Image Object Detection Python project!

What is this project all about? and how can you also implement the same? Please read this blog to understand it in more detail.

In a nutshell this project is "Image Object Detection on AWS". Also, I am from DevOps and cloud Engineering background so, I will be explaining backend infrastructure development part, but you can even utilize the same backend code and connect it with front-end to have a great full stack application experience.

This project originally created in "typescript" language but due to popularity of python, I created the same in python.

Concepts that you are going to leverage are, "AWS + python + IAC".

typescript Backend code: https://github.com/aws-samples/aws-dev-hour-backend
JS Frontend code: https://github.com/aws-samples/aws-dev-hour-frontend

Note: python backend code and typescript backend code is same in-terms of functionality.

So what are we going to build using AWS CDK: Below is the architecture.

1. Three S3 buckets for different purposes

image_bucket - where user will upload photos
resized_bucket - where each user uploaded image get stored in compressed form to enhance system performance.
website_bucket - to host our front-end website

2. API Gateway and Cognito
AWS Cognito gives user registration and sign-in functionality
User connects to website application using API gateway
API Gateway connects to lambda function and gives functionality to upload, delete and fetch images as per user request

3. DynamoDB table
AWS rekognition service will provide labels to images and that labels will be stored in DynamoDB table.

4. SQS
This was added in the application to make application more robust and scalable.
It allows multiple users to use application at the same time. Images wouldn't get drop because SQS can buffer it until application wouldn't process them.

5. Two Lambda functions
rekognitionLambda - this function fetch user uploaded images and connects to AWS Rekognition service to perform object detection task.
servicelambda - this function allows users to fetch those keywords detected in an image and user can even delete an image

## Below are few useful details from AWS CDK 

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
