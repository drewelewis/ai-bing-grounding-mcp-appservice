#!/usr/bin/env python3
"""List all model deployments and agents in the AI Foundry."""
import os
from pathlib import Path

# Get environment configuration
def get_env_value(key: str) -> str:
    """Get environment variable from .azure/prod/.env"""
    env_file = Path(".azure/prod/.env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        if k.strip() == key:
                            return v.strip().strip('"')
    return ""

try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["pip", "install", "-q", "azure-ai-projects", "azure-identity"])
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

def main():
    print("=" * 80)
    print("AI Foundry Models and Agents")
    print("=" * 80)
    print()
    
    # Get configuration
    foundry_name = get_env_value("AZURE_FOUNDRY_NAME")
    project_name = get_env_value("AZURE_AI_PROJECT_NAME")
    resource_group = get_env_value("AZURE_RESOURCE_GROUP")
    
    if not foundry_name or not project_name:
        print("❌ Could not find foundry/project configuration")
        print("   Run 'azd up' first to deploy the infrastructure")
        return
    
    project_endpoint = f"https://{foundry_name}.services.ai.azure.com/api/projects/{project_name}"
    
    print(f"📍 Foundry: {foundry_name}")
    print(f"📍 Project: {project_name}")
    print(f"📍 Endpoint: {project_endpoint}")
    print()
    
    # List model deployments first
    print("📦 Model Deployments:")
    print("-" * 80)
    try:
        import subprocess
        result = subprocess.run(
            f"az cognitiveservices account deployment list --name {foundry_name} --resource-group {resource_group} -o json",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            deployments = json.loads(result.stdout)
            if deployments:
                for dep in deployments:
                    model_name = dep.get("properties", {}).get("model", {}).get("name", "unknown")
                    version = dep.get("properties", {}).get("model", {}).get("version", "unknown")
                    sku = dep.get("sku", {}).get("name", "unknown")
                    capacity = dep.get("sku", {}).get("capacity", 0)
                    state = dep.get("properties", {}).get("provisioningState", "unknown")
                    print(f"  • {model_name} (v{version})")
                    print(f"    SKU: {sku}, Capacity: {capacity}, State: {state}")
                print()
                print(f"  Total: {len(deployments)} model deployments")
            else:
                print("  ❌ No model deployments found!")
                print("  Run 'python scripts/postprovision_deploy_models.py' to deploy models")
        else:
            print("  ⚠️  Could not retrieve deployments")
    except Exception as e:
        print(f"  ⚠️  Error checking deployments: {e}")
    print()
    
    try:
        # Initialize client
        credential = DefaultAzureCredential()
        project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=credential
        )
        
        # List agents
        print("🤖 Agents:")
        print("-" * 80)
        agents = list(project_client.agents.list_agents())
        
        if agents:
            # Group by model
            by_model = {}
            for agent in agents:
                model = agent.model
                if model not in by_model:
                    by_model[model] = []
                by_model[model].append(agent)
            
            for model, model_agents in sorted(by_model.items()):
                print(f"\n  {model} ({len(model_agents)} agents):")
                for agent in sorted(model_agents, key=lambda a: a.name):
                    print(f"    • {agent.name} (ID: {agent.id})")
            
            print()
            print(f"  Total: {len(agents)} agents across {len(by_model)} models")
        else:
            print("  No agents found")
        
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
