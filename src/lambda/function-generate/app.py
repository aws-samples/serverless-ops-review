# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json, os, copy
import boto3
from jinja2 import Template

s3 = boto3.client('s3')
s3_r = boto3.resource('s3')
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
supp = boto3.client('support')

#env var load
S3_BUCKET = os.environ['S3_BUCKET']
AWS_REGION = os.environ['REGION']
AWS_ACCOUNT = os.environ['ACCOUNT']
ACT_RUNTIMES = os.environ['ACT_RUNTIMES']
STACK_NAME = os.environ['STACK_NAME']
TA_ENABLED = os.environ['TA_ENABLED']


###################################################################################################################################
#Deprecated runtime evaluation code functionality
###################################################################################################################################
def check_deprecated_runtime(fns):
    run_check = fns
    act_runtimes = str.split(ACT_RUNTIMES, ',')
    
    for fn in run_check:
        match = False
        if fn['PackageType'] == 'Image':
            fn['Runtime'] = 'Container'
        for run in act_runtimes:
            if run == fn['Runtime']:
                match = True
                break
        if match == False:
            fn['Message'] = 'Function is using older or deprecated runtime, consider updating.'
        else:
            fn['Message'] = 'Function runtime is one of latest.'
    
    return run_check

###################################################################################################################################

###################################################################################################################################
#TA - High Error Rates
###################################################################################################################################
def check_ta_high_errors(fns):
    ta_he = supp.describe_trusted_advisor_check_result(checkId='L4dfs2Q3C2')
    ta_he_flagged = ta_he['result']['flaggedResources']
    ta_he_flagged_list = []
    ta_he_flagged_dict = dict
    checked_fns = fns
    
    ### ADD cross check for functions
    
    #data cleanup
    for f in ta_he_flagged:
        f_arn = f['metadata'][2].removesuffix(f['metadata'][2].split(':')[-1])
        f_arn = f_arn.rstrip(f_arn[-1])
        
        for fn in checked_fns:
            if f_arn == fn['FunctionArn']:
                ta_he_flagged_dict = {
                    'Status': f['metadata'][0],
                    'Region': f['metadata'][1],
                    'FunctionArn': f['metadata'][2],
                    'MaxDailyErrorRatePerc': f['metadata'][3],
                    'DateOfMaxErrorRate': f['metadata'][4],
                    'AverageDailyErrorRatePerc': f['metadata'][5]            
                }
                ta_he_flagged_list.append(ta_he_flagged_dict)
                break
            
    return ta_he_flagged_list

###################################################################################################################################

###################################################################################################################################
#TA - Excessive Timeouts
###################################################################################################################################
def check_ta_excessive_timeout(fns):
    ta_et = supp.describe_trusted_advisor_check_result(checkId='L4dfs2Q3C3')
    ta_et_flagged = ta_et['result']['flaggedResources']
    ta_et_flagged_list = []
    ta_et_flagged_dict = dict
    checked_fns = fns
    
    ### ADD cross check for functions
    
    #data cleanup
    for f in ta_et_flagged:
        f_arn = f['metadata'][2].removesuffix(f['metadata'][2].split(':')[-1])
        f_arn = f_arn.rstrip(f_arn[-1])
        
        for fn in checked_fns:
            if f_arn == fn['FunctionArn']:
                ta_et_flagged_dict = {
                    'Status': f['metadata'][0],
                    'Region': f['metadata'][1],
                    'FunctionArn': f['metadata'][2],
                    'MaxDailyTimeoutRatePerc': f['metadata'][3],
                    'DateOfMaxTimeoutRate': f['metadata'][4],
                    'AverageDailyTimeoutRatePerc': f['metadata'][5],
                    'FunctionTimeoutSettings': f['metadata'][6]
                }
                ta_et_flagged_list.append(ta_et_flagged_dict)
                break
            
    return ta_et_flagged_list
###################################################################################################################################

###################################################################################################################################
#multi-az evaluation code functionality
###################################################################################################################################
def check_multi_az(fns):
    
    vpc_fns = []
    sublist = []
    
    for fn in fns:
        if 'SubnetIds' in fn.keys() and fn['SubnetIds'] != []:
            vpc_fns.append(fn)
            sublist.append(fn['SubnetIds'])
    sublist = [item for row in sublist for item in row]
    sublist = list(dict.fromkeys(sublist))
    subnets = ec2.describe_subnets(SubnetIds=sublist)['Subnets']
    sub_az_list = []
    for sub in sublist:
        for s in subnets:
            if sub == s['SubnetId']:
                subaz = {
                    'SubnetId':s['SubnetId'],
                    'AZ': s['AvailabilityZone']
                }
                sub_az_list.append(subaz)
    vpc_functions = []
    for fn in vpc_fns:
        s_list = []
        for s in fn['SubnetIds']:
            for saz in sub_az_list:
                if s == saz['SubnetId']:
                    s = {
                    'SubnetId':saz['SubnetId'],
                    'AZ': saz['AZ']
                }
            s_list.append(s)
        vpc_function = {
            'FunctionArn':fn['FunctionArn'],
            'Subnets':s_list
        }
        vpc_functions.append(vpc_function)
    
    non_multiaz_functions = []
    for f in vpc_functions:
        f_azs = []
        for az in f['Subnets']:
            f_azs.append(az['AZ'])
        if len(f_azs) != len(set(f_azs)) or len(f_azs) == 1:
            non_multiaz_functions.append(f)
    return non_multiaz_functions

###################################################################################################################################

def handler(event, context):
    #List function config objects from S3:
    obj_functions = []
    s3_prefix = event['FolderKey']
    s3_f_folder = event['FolderKey'] + '/functions/'
    bucket = s3_r.Bucket(S3_BUCKET)
    for objects in bucket.objects.filter(Prefix=s3_f_folder):
        obj_functions.append(objects.key)
        
    #Fetch function config objects from S3:
    functions = []
    count = 0
    for obj in obj_functions:
        s3_function_set = s3.get_object(Bucket=S3_BUCKET, Key=obj)
        s3_function_set = json.loads(s3_function_set['Body'].read())
        functions.extend(s3_function_set)
        count = count + len(s3_function_set)
        
    #Remove review functions from list:
    for function in functions:
        if function['FunctionName'].startswith(STACK_NAME):
            functions.remove(function)
    #Set versions:
    for function in functions:
        function['Version'] = function['FunctionArn'].split(':')[-1]
    
    #get recommendations.json and event source mappings list from S3
    s3_recommendations = s3.get_object(Bucket=S3_BUCKET, Key=s3_prefix+'/recommendations.json')
    s3_event_source_mappings = s3.get_object(Bucket=S3_BUCKET, Key=s3_prefix+'/esms.json')
    
    #convert json to python dict
    recommendations = json.loads(s3_recommendations['Body'].read())
    #recommendations = recommendations['Recommendations']['LambdaFunctionRecommendations']
    esms = json.loads(s3_event_source_mappings['Body'].read())
    
    
    
    #################################################################################           
    #Deprecated runtime evaluation method pointer:
    #################################################################################           
    run_fns = copy.deepcopy(functions)  
    warnings_dep_runtime = check_deprecated_runtime(run_fns)
    py_dep_run = []
    no_dep_run = []
    ja_dep_run = []
    do_dep_run = []
    ru_dep_run = []
    go_dep_run = []
    cu_dep_run = []
    for run_warning in warnings_dep_runtime:
        if run_warning['Message'] != 'Function runtime is one of latest.':
            if run_warning['Runtime'].startswith('python'):
                py_dep_run.append(run_warning)
            elif run_warning['Runtime'].startswith('nodejs'):
                no_dep_run.append(run_warning)
            elif run_warning['Runtime'].startswith('java'):
                ja_dep_run.append(run_warning)
            elif run_warning['Runtime'].startswith('dotnet'):
                do_dep_run.append(run_warning)
            elif run_warning['Runtime'].startswith('ruby'):
                ru_dep_run.append(run_warning)
            elif run_warning['Runtime'].startswith('golang'):
                go_dep_run.append(run_warning)
            elif run_warning['Runtime'].startswith('provided'):
                cu_dep_run.append(run_warning)
    
    #################################################################################           
    #Trusted Advisor evaluations
    #################################################################################           
    if TA_ENABLED == 'true':                
        ta_fns = copy.deepcopy(functions)
        # Get HighErrorRate Check result
        warnings_ta_high_errors = check_ta_high_errors(ta_fns)
                
        #Get ExcessiveTimeout Check result
        warnings_ta_excessive_timeout = check_ta_excessive_timeout(ta_fns)
    
    
    #################################################################################           
    #Mutli-az evaluation:   
    #################################################################################
    
    vpc_fns = copy.deepcopy(functions)
    
    warnings_vpc_functions = check_multi_az(vpc_fns)    
    
    #################################################################################
    
    #################################################################################           
    #Recommendations evaluations:   
    #################################################################################
    #Match Compute Optimizer  recommendations to functions
    
    not_optimized_functions = []
    unavailable_functions = []
    savings_not_present = {"EstimatedMonthlySavings":{"Currency": "USD","Value": "N/A"},"SavingsOpportunityPercentage": "N/A"}
    for recommendation in recommendations:
        rec_function_arn = recommendation['FunctionArn']
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
                    
    #Check functions with x86 architecture
    
    old_arch_fns = []
    for function in functions:
        if 'x86_64' in function['Architectures']:
            old_arch_fns.append(function['FunctionArn'])
    
    #################################################################################
    
   
    
    #################################################################################
    #Create a dict wilh all data that will populate the template
    #################################################################################
    data = {}
    data['account'] = AWS_ACCOUNT
    data['region'] = AWS_REGION
    data['reviewed_functions'] = functions
    data['dep_python_functions'] = py_dep_run
    data['dep_nodejs_functions'] = no_dep_run
    data['dep_java_functions'] = ja_dep_run
    data['dep_dotnet_functions'] = do_dep_run
    data['dep_ruby_functions'] = ru_dep_run
    data['dep_golang_functions'] = go_dep_run
    data['dep_custom_functions'] = cu_dep_run
    if TA_ENABLED == 'true':
        data['warnings_ta_high_errors'] = warnings_ta_high_errors
        data['warnings_ta_excessive_timeouts'] = warnings_ta_excessive_timeout
    data['warnings_vpc'] = warnings_vpc_functions
    data['recfunctions'] = not_optimized_functions
    data['recarch'] = old_arch_fns
    data['esms'] = esms
    
    
    #render the template
    with open('template.html', 'r') as file:
        template = Template(file.read(),trim_blocks=True)
    rendered_file = template.render(data=data)
    
    s3.put_object(Body=rendered_file, Bucket=S3_BUCKET, Key=s3_prefix+'/report.html')
    
    presign = s3.generate_presigned_url(ClientMethod='get_object',Params={'Bucket': S3_BUCKET,'Key': s3_prefix+'/report.html'}, ExpiresIn=3600)
    
    return {
        "statusCode": 200,
        "ReportUrl": presign
    }
    


