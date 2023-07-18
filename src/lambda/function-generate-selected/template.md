# Serverless Operational Review

**AWS Account:** {{data.account}}

**Region:** {{data.region}}

---

## AWS Lambda Review

---

### <mark style="background-color: white; color: red;">Danger Zone - Risk Warnings</mark>

- Detailed resource configuration overview is present in the **List of Reviewed Functions - Configuration** section of this report.

<mark style="background-color: red; color: red;">-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------</mark>

- #### Multi-AZ Warnings
  
{% if data.warnings_vpc != [] %}
{% for warnings_vpc in data.warnings_vpc %}
| | |
|:---|:---|
|Function Name:|**{{warnings_vpc['FunctionName']}}**|
|Risk warning:|<mark style="color: red;">***{{warnings_vpc['Message']}}***</mark>|
|Attached subnets:|{% for sub in warnings_vpc['SubnetIds'] %}{{sub}}</br>{% endfor %}|

---

{% endfor %}

{% else %}

    - No isses reported for the reviewed function set.

{% endif %}

---

- #### Runtime Warnings

{% if data.warnings_runtime != [] %}

{% for warnings_runtime in data.warnings_runtime %}
| | |
|:---|:---|
|Function Name:|**{{warnings_runtime['FunctionName']}}**|
|Risk warning:|<mark style="color: orangered;">***{{warnings_runtime['Message']}}***</mark>|
|Current function runtime:|**{{warnings_runtime['Runtime']}}**|

---

{% endfor %}

{% else %}

    - No isses reported for the reviewed function set.

{% endif %}

---

{% if data.ta_enabled == 'true' %}

- #### Functions with high error rates

{% if data.warnings_ta_high_errors != [] %}

{% for warnings_ta_high_errors in data.warnings_ta_high_errors %}
| | |
|:---|:---|
|Function Name:|**{{warnings_ta_high_errors['FunctionArn']}}**|
|Status:|***{{warnings_ta_high_errors['Status']}}***|
|Average Daily Error %:|{{warnings_ta_high_errors['AverageDailyErrorRatePerc']}}|
|Max Daily Error %|{{warnings_ta_high_errors['MaxDailyErrorRatePerc']}}|
|Date of Max Error Rate:|{{warnings_ta_high_errors['DateOfMaxErrorRate']}}|

---

{% endfor %}

{% else %}

    - No isses reported for the reviewed function set.

{% endif %}

---

- #### Functions with excessive timeouts

{% if data.warnings_ta_excessive_timeout != [] %}

{% for warnings_ta_excessive_timeout in data.warnings_ta_excessive_timeout %}
| | |
|:---|:---|
|Function Name:|**{{warnings_ta_excessive_timeout['FunctionArn']}}**|
|Status:|***{{warnings_ta_excessive_timeout['Status']}}***|
|Average Daily Timeouts:|{{warnings_ta_excessive_timeout['AverageDailyTimeoutRatePerc']}}|
|Max Daily Timeouts %|{{warnings_ta_excessive_timeout['MaxDailyTimeoutRatePerc']}}|
|Date of Max Timeouts:|{{warnings_ta_excessive_timeout['DateOfMaxTimeoutRate']}}|
|Function Timeout Setting:|{{warnings_ta_excessive_timeout['FunctionTimeoutSettings']}}|

---

{% endfor %}

{% else %}

    - No isses reported for the reviewed function set.

{% endif %}

{% endif %}

<mark style="background-color: red; color: red;">-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------</mark>

<mark style="background-color: navy; color: navy;">-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------</mark>

### <mark style="background-color: white; color: navy;">Optimization Recommendations</mark>

---

{% if data.recfunctions != [] %}

{% for recfunction in data.recfunctions %}
| | |
|:---|:---|
|**Function Name:**|**{{recfunction['FunctionName']}}**|
|Optimization finding:|{{recfunction['FindingReasonCodes'][0]}}|
|Risk level:|{{recfunction['CurrentPerformanceRisk']}}|
|Look back period (Days):|{{recfunction['LookbackPeriodInDays']}}|
|Number of invocations:|{{recfunction['NumberOfInvocations']}}|
|Current Memory Size:|{{recfunction['CurrentMemorySize']}}|
|**Recommended Memory Size:**|**{{recfunction['MemorySizeRecommendationOptions'][0]['MemorySize']}}**|
|Estimated monthly saving (USD):|{{recfunction['MemorySizeRecommendationOptions'][0]['SavingsOpportunity']['EstimatedMonthlySavings']['Value']}}|
|Estimated monthly saving (%):|{{recfunction['MemorySizeRecommendationOptions'][0]['SavingsOpportunity']['SavingsOpportunityPercentage']}}|
|Duration avg - current (ms):|{{recfunction['UtilizationMetrics'][0]['Value']}}|
|**Duration avg - projected (ms):**|**{{recfunction['MemorySizeRecommendationOptions'][0]['ProjectedUtilizationMetrics'][1]['Value']}}**|
---
{% endfor %}

{% else %}

    - No recommendations reported for the reviewed function set.

{% endif %}

- The above recommendations were sourced from [AWS Compute Optimizer](https://console.aws.amazon.com/compute-optimizer/).
- To get a graphical representation of optimal **memory** compared to **cost** and **performance**, you can deploy and run [Lambda Power Tuning tool](https://docs.aws.amazon.com/lambda/latest/operatorguide/profile-functions.html).

---

- #### Functions using x86 architecture type

    - <mark style="background-color: powderblue; color: black;">***These functions may benefit from converting to Graviton 2 architecture (arm64) for improvements in cost and performance.***</mark>
    - More information can be found in [AWS Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/foundation-arch.html)

|Names of Functions deployed with x86 architecture:|
|:---|
{% for fn in data.recarch %}
|{{fn}}|
{% endfor %}

<mark style="background-color: navy; color: navy;">-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------</mark>

### List of Reviewed Functions - Configurations

---

{% for reviewed_function in data.reviewed_functions %}
| | |
|:---|:---|
|**Function Name:**|**{{reviewed_function['FunctionName']}}**|
|Memory:|{{reviewed_function['MemorySize']}}|
|Timeout:|{{reviewed_function['Timeout']}}|
|Runtime Version:|{{reviewed_function['Runtime']}}|
|Architecture:| {{reviewed_function['Architectures']}}|
|Package Type:|{{reviewed_function['PackageType']}}|
|Reserved Concurrency:|{{reviewed_function.ReservedConcurrency.ReservedConcurrentExecutions}}|
|Provisioned Concurrency Configuration:|{% if reviewed_function['ProvisionedConcurrencyConfigs'] != [] %} {% for conf in reviewed_function['ProvisionedConcurrencyConfigs'] %} *ARN:* {{conf['FunctionArn']}}</br>*Requested:* {{conf['RequestedProvisionedConcurrentExecutions']}} </br>  {% endfor %}    {% endif %}|
|Execution Role:|{{reviewed_function['Role']}}|
|Code Size (bytes):|{{reviewed_function['CodeSize']}}|
|Function Storage - /tmp(MB):|{{reviewed_function['EphemeralStorage']}}|
|X-Ray tracing:|{{reviewed_function['TracingConfig']}}
|SnapStart Status (Java only):|{{reviewed_function['SnapStartOptimizationStatus']}}|
{% if reviewed_function['EventSourceMappings'] != [] %}
</br>
|**Event Source Mappings:**||
{% for esm in data.esms %}
{% if esm['FunctionArn'] == reviewed_function['FunctionArn'] %}
|Event Source ARN:|{{esm['EventSourceArn']}}|
|State:|{{esm['State']}}|
|Last Modified:|{{esm['LastModified']}}|
|State Transition Reason:|{{esm['StateTransitionReason']}}|
|Batch Size:|{{esm['BatchSize']}}|
|Max Batching Windows (s):|{{esm['MaximumBatchingWindowInSeconds']}}|
</br>
{% endif %}
{% endfor %}
{% endif %}

---
{% endfor %}

---

## End of Generated report