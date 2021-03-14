#!/usr/bin/env python3

from aws_cdk import core as cdk

from twitch_aws_image_rekognition.backend_stack import BackendStack


app = cdk.App()
BackendStack(app, "twitch-aws-image-rekognition", env={'region': 'us-west-2'})

app.synth()
