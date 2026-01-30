"""Direct test of the models endpoint logic"""
import os
import re
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_REGION = "local"

if not PROJECT_ENDPOINT:
    result = {
        "total": 0,
        "region": AZURE_REGION,
        "foundry": None,
        "error": "AZURE_AI_PROJECT_ENDPOINT not configured",
        "models": []
    }
    print(result)
    exit(0)

# Extract foundry name from endpoint for display
foundry_name = None
match = re.search(r'https://([^.]+)\.', PROJECT_ENDPOINT)
if match:
    foundry_name = match.group(1)

models_list = []

try:
    client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=PROJECT_ENDPOINT
    )
    
    # List all model deployments using the same SDK as agents
    deployments = client.deployments.list()
    
    for deployment in deployments:
        # SKU is a dict like {'name': 'GlobalStandard', 'capacity': 251}
        sku_info = getattr(deployment, 'sku', {}) or {}
        
        models_list.append({
            "name": deployment.name,
            "model": deployment.model_name,
            "version": deployment.model_version,
            "publisher": deployment.model_publisher,
            "sku": sku_info.get('name', 'unknown'),
            "capacity": sku_info.get('capacity', 0),
            "type": getattr(deployment, 'type', 'unknown')
        })
except Exception as e:
    print(f"⚠️ Could not list models: {e}")
    result = {
        "total": 0,
        "region": AZURE_REGION,
        "foundry": foundry_name,
        "error": str(e),
        "models": []
    }
    print(result)
    exit(1)

result = {
    "total": len(models_list),
    "region": AZURE_REGION,
    "foundry": foundry_name,
    "models": models_list
}

import json
print(json.dumps(result, indent=2))
