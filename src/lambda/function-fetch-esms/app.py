# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json, os, copy
import boto3


lbd = boto3.client('lambda')
s3 = boto3.client('s3')

#env var load
S3_BUCKET = os.environ['S3_BUCKET']



def esms_fetch():
    response = lbd.list_event_source_mappings()
    response = response['EventSourceMappings']
    return response


def handler(event, context):
    
    esms = esms_fetch()
   
    key = event['FolderKey']
    esms_to_s3 = s3.put_object(Bucket=S3_BUCKET, Key=key+'/esms.json', Body=json.dumps(esms, default=str))
    
    
    return {
        "statusCode": 200,
        "FolderKey": key
    }