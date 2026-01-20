#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Bing Grounding connection in AI Foundry via Bicep deployment.

This script deploys the bing-connection.bicep module to create the
required connection between AI Foundry and the Bing Grounding resource.

Usage:
    python scripts/postprovision_deploy_bing_connection.py
"""
import os
import sys
import json
import subprocess
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def run_command(cmd: list[str]) -> tuple[bool, str, str]:
    """
    Run a command and return (success, stdout, stderr).
    """
    try:
        # On Windows, use shell=True to find az.cmd in PATH
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def get_env_value(key: str) -> str:
    """Get environment variable from .azure/{env}/.env"""
    import json
    config_file = Path(".azure/config.json")
    env_name = "prod"
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            env_name = config.get("defaultEnvironment", "prod")
    
    env_dir = Path(f".azure/{env_name}")
    env_file = env_dir / ".env"
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    value = line.split("=", 1)[1]
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    return value
    
    # Fallback to environment variable
    return os.environ.get(key, "")

def main():
    print("=" * 80)
    print("Create Bing Grounding Connection via Bicep Deployment")
    print("=" * 80)
    print()
    
    # Get environment variables
    subscription_id = get_env_value("AZURE_SUBSCRIPTION_ID")
    resource_group = get_env_value("AZURE_RESOURCE_GROUP")
    foundry_name = get_env_value("AZURE_FOUNDRY_NAME")
    bing_resource_id = get_env_value("BING_GROUNDING_RESOURCE_ID")
    bing_resource_group = get_env_value("BING_GROUNDING_RESOURCE_GROUP")
    bing_resource_name = get_env_value("BING_GROUNDING_RESOURCE_NAME")
    
    if not all([subscription_id, resource_group, foundry_name, bing_resource_id, bing_resource_group, bing_resource_name]):
        print("❌ ERROR: Missing required environment variables")
        print(f"   AZURE_SUBSCRIPTION_ID: {subscription_id}")
        print(f"   AZURE_RESOURCE_GROUP: {resource_group}")
        print(f"   AZURE_FOUNDRY_NAME: {foundry_name}")
        print(f"   BING_GROUNDING_RESOURCE_ID: {bing_resource_id}")
        print(f"   BING_GROUNDING_RESOURCE_GROUP: {bing_resource_group}")
        print(f"   BING_GROUNDING_RESOURCE_NAME: {bing_resource_name}")
        return 1
    
    print(f"📋 Deployment Details:")
    print(f"   Subscription: {subscription_id}")
    print(f"   Resource Group: {resource_group}")
    print(f"   AI Foundry: {foundry_name}")
    print(f"   Bing Resource ID: {bing_resource_id}")
    print(f"   Bing Resource Name: {bing_resource_name}")
    print(f"   Bing Resource Group: {bing_resource_group}")
    print()
    
    # Deploy Bicep template
    print("🚀 Deploying Bing connection via Bicep...")
    deployment_name = f"bing-connection-{os.urandom(4).hex()}"
    
    cmd = [
        "az", "deployment", "group", "create",
        "--subscription", subscription_id,
        "--resource-group", resource_group,
        "--name", deployment_name,
        "--template-file", "infra/bing-connection.bicep",
        "--parameters",
        f"foundryName={foundry_name}",
        f"bingResourceId={bing_resource_id}",
        f"bingResourceName={bing_resource_name}",
        f"bingResourceGroup={bing_resource_group}"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        print(f"❌ ERROR: Bicep deployment failed")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Error: {stderr}")
        return 1
    
    try:
        deployment_output = json.loads(stdout)
        if "properties" in deployment_output and "outputs" in deployment_output["properties"]:
            outputs = deployment_output["properties"]["outputs"]
            connection_id = outputs.get("connectionId", {}).get("value")
            connection_name = outputs.get("connectionName", {}).get("value")
            
            print()
            print("✅ SUCCESS: Bing connection created")
            print(f"   Connection Name: {connection_name}")
            print(f"   Connection ID: {connection_id}")
            print()
    except json.JSONDecodeError:
        print("✅ Deployment completed (output parsing skipped)")
        print()
    
    # Verify connection exists
    print("🔍 Verifying connection...")
    cmd = [
        "az", "rest",
        "--method", "GET",
        "--url", f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{foundry_name}/connections/default-bing?api-version=2025-06-01"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        try:
            connection = json.loads(stdout)
            print("✅ Connection verified:")
            print(f"   Name: {connection.get('name')}")
            print(f"   Category: {connection.get('properties', {}).get('category')}")
            print(f"   Auth Type: {connection.get('properties', {}).get('authType')}")
        except:
            print("✅ Connection exists (details unavailable)")
    else:
        print("⚠️  Could not verify connection (may still be provisioning)")
    
    print()
    print("=" * 80)
    print("Bing Connection Deployment Complete")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
