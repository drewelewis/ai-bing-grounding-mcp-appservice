#!/usr/bin/env python3
"""Create Bing connection using Azure AI SDK"""
import os
import sys

# Get environment values
subscription_id = "d201ebeb-c470-4a6f-82d5-c2f95bb0dc1e"
resource_group = "rg-bing-grounding-mcp-dev6"
foundry_name = "ai-foundry-vw5lt6yc7noze"
project_name = "ai-proj-vw5lt6yc7noze"
bing_resource_id = "/subscriptions/d201ebeb-c470-4a6f-82d5-c2f95bb0dc1e/resourceGroups/rg-bing-grounding-mcp-dev6/providers/Microsoft.Bing/accounts/bing-grounding-mcp"

print("Creating Bing Grounding connection...")
print(f"Project: {project_name}")
print(f"Bing Resource: {bing_resource_id}")
print()

# Try using azure-ai-ml package
try:
    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import WorkspaceConnection
    from azure.identity import DefaultAzureCredential
    
    credential = DefaultAzureCredential()
    
    # Create ML Client for the AI Hub (Foundry)
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=foundry_name
    )
    
    # Create Bing connection
    bing_connection = WorkspaceConnection(
        name="default-bing",
        type="bing_grounding",
        target="https://api.bing.microsoft.com/",
        credentials=None,  # No credentials needed for Bing in same RG
        metadata={
            "ApiType": "grounding",
            "BingResourceId": bing_resource_id
        }
    )
    
    print("Creating connection via ML Client...")
    created_conn = ml_client.connections.create_or_update(bing_connection)
    print(f"✅ Connection created: {created_conn.name}")
    print(f"   Type: {created_conn.type}")
    print(f"   Target: {created_conn.target}")
    
except Exception as e:
    print(f"❌ ML Client approach failed: {e}")
    print()
    print("Trying alternative approach...")
    
    # Try using REST API with correct format
    import subprocess
    import json
    
    # Use Azure CLI to get access token
    token_result = subprocess.run(
        ["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"],
        capture_output=True,
        text=True
    )
    
    if token_result.returncode == 0:
        token = token_result.stdout.strip()
        
        import requests
        
        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{foundry_name}/connections/default-bing?api-version=2024-04-01"
        
        payload = {
            "properties": {
                "category": "BingGrounding",
                "target": "https://api.bing.microsoft.com/",
                "authType": "None",
                "metadata": {
                    "ApiType": "grounding",
                    "BingResourceId": bing_resource_id
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"PUT {url}")
        response = requests.put(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"✅ Connection created successfully!")
            print(response.json())
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(response.text)
    else:
        print("Failed to get access token")
