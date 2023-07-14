# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json, os, copy
import boto3
from jinja2 import Template

s3 = boto3.client('s3')
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

#env var load
S3_BUCKET = os.environ['S3_BUCKET']
AWS_REGION = os.environ['REGION']
AWS_ACCOUNT = os.environ['ACCOUNT']
ACT_RUNTIMES = os.environ['ACT_RUNTIMES']
STACK_NAME = os.environ['STACK_NAME']
        

###################################################################################################################################
#multi-az evaluation code functionality
###################################################################################################################################
def check_multi_az(fns):
    sub_check = fns        
    list_subs = []
    index_list = []
    index = 0
    
    for fn in sub_check:
        if not 'SubnetIds' in fn.keys():
            index_list.append(index)
        index += 1
        
    reverse_index_list = index_list[::-1]
        
    for i in reverse_index_list:
        del sub_check[i]
    
    for fn in sub_check:
        if 'SubnetIds' in fn:
            fn['SubnetsByAz'] = [] 
            list_subs.append(fn['SubnetIds'])
    
    list_subs = [item for sublist in list_subs for item in sublist]
        
    describe_subnets = ec2.describe_subnets(SubnetIds=list_subs)
     
    for sub in describe_subnets['Subnets']:
        for fn in sub_check:
            azs = []
            subs = []
            for subnet in fn['SubnetIds']:
                if subnet == sub['SubnetId']:
                    fn['SubnetsByAz'].append({'SubnetId': sub['SubnetId'], 'AvailabilityZone': sub['AvailabilityZone']})
            if len(fn['SubnetIds']) == 1:
                fn['Message'] = 'Function is not enabled for multiple AZs - single AZ'
            for s in fn['SubnetsByAz']:
                azs.append(s['AvailabilityZone'])
                subs.append(s['SubnetId'])
            if len(subs) != len(set(azs)):
                fn['Message'] = 'Function is not enabled for multiple AZs - some subnets are in the same AZ'
            if not 'Message' in fn.keys():
                fn['Message'] = 'Function is enabled for multiple AZs'
            
    return sub_check

###################################################################################################################################

###################################################################################################################################
#deprecated runtime evaluation code functionality
###################################################################################################################################
def check_deprecated_runtime(fns):
    run_check = fns
    act_runtimes = str.split(ACT_RUNTIMES, ',')
    
    for fn in run_check:
        match = False
        for run in act_runtimes:
            if run == fn['Runtime']:
                match = True
                break
        if match == False:
            fn['Message'] = 'Function is using older or deprecated runtime, consider updating'
        else:
            fn['Message'] = 'Function runtime is one of latest'
    
    return run_check

###################################################################################################################################

def handler(event, context):
    
    #S3 prefix from event:
    s3_prefix = event['Prefix']
    s3_functions_name = event['FunctionsObject']
    
    #get recommendations.json, function configuration and event source mappings list from S3
    s3_recommendations = s3.get_object(Bucket=S3_BUCKET, Key=s3_prefix+'/recommendations.json')
    s3_functions = s3.get_object(Bucket=S3_BUCKET, Key=s3_prefix+'/'+s3_functions_name)
    s3_event_source_mappings = s3.get_object(Bucket=S3_BUCKET, Key=s3_prefix+'/esms.json')
    
    #convert json to python dict
    recommendations = json.loads(s3_recommendations['Body'].read())
    recommendations = recommendations['Recommendations']['LambdaFunctionRecommendations']
    functions = json.loads(s3_functions['Body'].read())
    esms = json.loads(s3_event_source_mappings['Body'].read())
    
    #remove review functions from list
    for function in functions:
        if function['FunctionName'].startswith(STACK_NAME):
            functions.remove(function)
    
    
    #################################################################################           
    #recommendations evaluations:   
    #################################################################################
    #match recommendations to functions
    not_optimized_functions = []
    unavailable_functions = []
    savings_not_present = {"EstimatedMonthlySavings":{"Currency": "USD","Value": "N/A"},"SavingsOpportunityPercentage": "N/A"}
    for recommendation in recommendations:
        rec_function_arn = recommendation['FunctionArn'].removesuffix(recommendation['FunctionArn'].split(':')[-1])
        rec_function_arn = rec_function_arn.rstrip(rec_function_arn[-1])
        rec_function_name = recommendation['FunctionArn'].split(':')
        rec_function_name = rec_function_name[6]+':'+rec_function_name[7]
        

        for function in functions:
            if rec_function_arn == function['FunctionArn']:
                recommendation['FunctionName'] = rec_function_name
                if recommendation['Finding'] == 'NotOptimized':                    
                    if not 'SavingsOpportunity' in recommendation['MemorySizeRecommendationOptions'][0]:
                        recommendation['MemorySizeRecommendationOptions'][0]['SavingsOpportunity'] = savings_not_present
                    not_optimized_functions.append(recommendation)
                    
                    
                else:
                    unavailable_functions.append(recommendation)
                    
    #check function with x86 architecture
    old_arch_fns = []
    for function in functions:
        if 'x86_64' in function['Architectures']:
            old_arch_fns.append(function['FunctionName'])
                    
    #################################################################################           
    #warnings evaluations:   
    #################################################################################
    #mutli-az evaluation
    vpc_fns = copy.deepcopy(functions)   
    warnings_vpc_functions = check_multi_az(vpc_fns)    
    warnings_vpc = []
    for vpc_warning in warnings_vpc_functions:
        if vpc_warning['Message'] != 'Function is enabled for multiple AZs':
            warnings_vpc.append(vpc_warning)
            
    #deprecated runtime evaluation
    run_fns = copy.deepcopy(functions)  
    warnings_dep_runtime = check_deprecated_runtime(run_fns)
    warnings_run = []
    for run_warning in warnings_dep_runtime:
        if run_warning['Message'] != 'Function runtime is one of latest':
            warnings_run.append(run_warning)
    
        
    #################################################################################           
    #functions configuration compilation:   
    #################################################################################
    
    #cleanup event source mappings
    
    filtered_esms = []
    for esm in esms['EventSourceMappings']['EventSourceMappings']:
        
        temp_esm = {
            "BatchSize": esm['BatchSize'],
            "EventSourceArn": esm['EventSourceArn'],
            "FunctionArn": esm['FunctionArn'],
            "State": esm['State'],
            "LastModified": esm['LastModified'],
            "StateTransitionReason": esm['StateTransitionReason'],
            "MaximumBatchingWindowInSeconds": esm['MaximumBatchingWindowInSeconds'],
        }        
        filtered_esms.append(temp_esm)
    
    for fn in functions:
        fn['EventSourceMappings'] = []
        for esm in filtered_esms:
            if esm['FunctionArn'] == fn['FunctionArn']:
                fn['EventSourceMappings'].append(esm)
    
    
    #################################################################################
    
    #create a dict wilh all data that will populate the template
    data = {}
    data['account'] = AWS_ACCOUNT
    data['region'] = AWS_REGION
    data['recfunctions'] = not_optimized_functions
    data['warnings_vpc'] = warnings_vpc
    data['warnings_runtime'] = warnings_run
    data['recarch'] = old_arch_fns
    #data['codesizeMessage'] = notification_codesize
    data['esms'] = filtered_esms
    data['reviewed_functions'] = functions
    
    #render the template
    with open('template.md', 'r') as file:
        template = Template(file.read(),trim_blocks=True)
    rendered_file = template.render(data=data)
    
    index = open("index.html").read().format(markdown_pointer=rendered_file)
    
    #upload the index.html file to S3
    status_code = 200
    response = ''
    rerun = False
        
    try:
        #upload the index.html file to S3
        s3.put_object(Body=index, Bucket=S3_BUCKET, Key=s3_prefix+'/index.html')
        #s3 create signed url for the index.html file
        response = s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET, 'Key': s3_prefix+'/index.html'}, ExpiresIn=3600) 
    except Exception as e:
        status_code = 500
        response = json.loads(e)
    
    return {
        "statusCode": status_code,
        "body": json.dumps(response)
    }
    


