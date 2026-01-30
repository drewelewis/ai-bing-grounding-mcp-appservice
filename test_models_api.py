"""Test the /models endpoint locally to debug deployment attributes"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

if not endpoint:
    print("❌ AZURE_AI_PROJECT_ENDPOINT not set")
    exit(1)

print(f"Testing with endpoint: {endpoint}")

try:
    client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=endpoint
    )
    
    deployments = client.deployments.list()
    
    for deployment in deployments:
        print(f"\n{'='*60}")
        print(f"Deployment: {deployment.name if hasattr(deployment, 'name') else 'NO NAME'}")
        print(f"Type: {type(deployment)}")
        print(f"\nAll attributes:")
        for attr in dir(deployment):
            if not attr.startswith('_'):
                try:
                    value = getattr(deployment, attr)
                    if not callable(value):
                        print(f"  {attr}: {value}")
                except Exception as e:
                    print(f"  {attr}: <error: {e}>")
        
        # Try to build the response
        print(f"\nBuilding response:")
        model_info = {
            "name": getattr(deployment, 'name', 'unknown'),
            "model": getattr(deployment, 'model_name', getattr(deployment, 'model', 'unknown')),
            "version": getattr(deployment, 'model_version', getattr(deployment, 'version', 'unknown')),
            "format": getattr(deployment, 'model_publisher', 'unknown'),
            "sku": getattr(deployment, 'sku', {}).get('name', 'unknown') if hasattr(deployment, 'sku') else 'unknown',
            "capacity": getattr(deployment, 'sku', {}).get('capacity', 0) if hasattr(deployment, 'sku') else 0,
            "status": getattr(deployment, 'provisioning_state', 'unknown')
        }
        print(f"  Result: {model_info}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
