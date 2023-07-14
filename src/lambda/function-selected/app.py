# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
import json

STATE_MACHINE = os.environ['SFN_SELECTED']
sfn = boto3.client('stepfunctions')
cfn = boto3.client('cloudformation')

def handler(event, context):
    # Fetch stack name from event:
    stack_name = event['resources'] 
    
    #Fetch stack parameters:
    functions = cfn.describe_stacks(
        StackName=stack_name[0]
    )    
    functions = functions['Stacks'][0]['Parameters'][0]['ParameterValue'].split(',')
    
    #Start state machine execution:
    sfn_input = json.dumps({"Functions": functions})
        
    sfn_selected = sfn.start_execution(
        stateMachineArn=STATE_MACHINE,
        input=sfn_input    
    )