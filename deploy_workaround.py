#!/usr/bin/env python3
import json
import sys
import subprocess
import requests

# Get access token
token_result = subprocess.run(
    ['az', 'account', 'get-access-token', '--query', 'accessToken', '-o', 'tsv'],
    capture_output=True, text=True, check=True
)
access_token = token_result.stdout.strip()

# Get subscription ID
sub_result = subprocess.run(
    ['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
    capture_output=True, text=True, check=True
)
subscription_id = sub_result.stdout.strip()

# Load the template
with open('src/infra/DeployAzureResources.json', 'r') as f:
    template = json.load(f)

# Prepare deployment
resource_group = 'techworkshop-l300-ai-agents2'
deployment_name = 'bicep-deployment-' + subprocess.run(['date', '+%Y%m%d-%H%M%S'], capture_output=True, text=True).stdout.strip()

# Create deployment payload
deployment_payload = {
    'properties': {
        'mode': 'Incremental',
        'template': template
    }
}

# Deploy using REST API
url = f'https://management.azure.com/subscriptions/{subscription_id}/resourcegroups/{resource_group}/providers/Microsoft.Resources/deployments/{deployment_name}'
api_version = '2021-04-01'

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

print(f"Starting deployment: {deployment_name}")
print(f"Resource Group: {resource_group}")
print(f"URL: {url}?api-version={api_version}")

response = requests.put(
    f'{url}?api-version={api_version}',
    headers=headers,
    json=deployment_payload,
    timeout=600
)

if response.status_code in [200, 201]:
    print("\n✓ Deployment started successfully!")
    deployment_data = response.json()
    print(f"\nDeployment ID: {deployment_data.get('id', 'N/A')}")
    print(f"Provisioning State: {deployment_data.get('properties', {}).get('provisioningState', 'N/A')}")
    
    # Monitor deployment
    print("\nMonitoring deployment (this may take several minutes)...")
    while True:
        import time
        time.sleep(15)
        
        check_response = requests.get(
            f'{url}?api-version={api_version}',
            headers=headers
        )
        
        if check_response.status_code == 200:
            status = check_response.json()
            state = status.get('properties', {}).get('provisioningState', 'Unknown')
            print(f"Status: {state}")
            
            if state in ['Succeeded', 'Failed', 'Canceled']:
                if state == 'Succeeded':
                    print("\n✓ Deployment completed successfully!")
                    outputs = status.get('properties', {}).get('outputs', {})
                    if outputs:
                        print("\nOutputs:")
                        for key, value in outputs.items():
                            print(f"  {key}: {value.get('value', 'N/A')}")
                else:
                    print(f"\n✗ Deployment {state}")
                    error = status.get('properties', {}).get('error', {})
                    if error:
                        print(f"Error: {json.dumps(error, indent=2)}")
                break
        else:
            print(f"Error checking status: {check_response.status_code}")
            break
else:
    print(f"\n✗ Deployment failed to start!")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    sys.exit(1)
