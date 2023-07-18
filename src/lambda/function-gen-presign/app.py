# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json, os, copy
import boto3

s3 = boto3.client('s3')

#env var load
S3_BUCKET = os.environ['S3_BUCKET']

def handler(event, context):
    report_urls = event['body']
    report_urls = report_urls.replace('"', '')
    report_urls = report_urls.split(',')
    presign_urls = []
    response = ''
    try: 
        for url in report_urls:
            
            if url != 'None':
                presign = s3.generate_presigned_url(ClientMethod='get_object',Params={'Bucket': S3_BUCKET,'Key': url}, ExpiresIn=3600)
                presign_urls.append(presign)
                
        status_code = 200
        response = presign_urls
    except Exception as e:
        response = str(e)
        status_code = 500
    
    return {
        'statusCode': status_code,
        'body': response
    }