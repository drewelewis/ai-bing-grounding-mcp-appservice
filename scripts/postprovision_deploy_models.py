#!/usr/bin/env python3
"""
Deploy AI Foundry model deployments that may have been skipped during Bicep deployment.
This script ensures model deployments exist as needed by the agents.
"""
import os
import sys
import subprocess
import json
from pathlib import Path

def get_env_value(key: str) -> str:
    """Get environment variable from .azure/{env}/.env"""
    import json
    config_file = Path(".azure/config.json")
    env_name = "prod"
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                env_name = config.get("defaultEnvironment", "prod")
        except Exception:
            pass
    
    env_file = Path(f".azure/{env_name}/.env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        if k.strip() == key:
                            return v.strip().strip('"')
    return ""

def run_command(cmd, check=True):
    """Run a command and return success, stdout, stderr."""
    try:
        result = subprocess.run(
            ' '.join(cmd) if isinstance(cmd, list) else cmd,
            shell=True,  # Required for Windows to find az command in PATH
            capture_output=True,
            text=True,
            check=check
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def main():
    print("=" * 80)
    print("Deploying AI Foundry Model Deployments")
    print("=" * 80)
    print()
    
    # Get configuration
    foundry_name = get_env_value("AZURE_FOUNDRY_NAME")
    resource_group = get_env_value("AZURE_RESOURCE_GROUP")
    
    if not foundry_name or not resource_group:
        print("[ERROR] Missing configuration. Run 'azd up' first.")
        return 1
    
    print(f"[INFO] Foundry: {foundry_name}")
    print(f"[INFO] Resource Group: {resource_group}")
    print()
    
    # Model configurations (only models that support Bing grounding)
    # ONLY officially supported models: GPT-4o, GPT-4, GPT-3.5-Turbo
    # GPT-4.1 and GPT-5 series REMOVED - not real models or don't support Bing grounding
    models = [
        {
            "env_var": "agentPoolSizeGpt4o",
            "name": "gpt-4o",
            "model_name": "gpt-4o",
            "version": "2024-08-06",
            "sku": "GlobalStandard",
            "capacity": 10
        },
        {
            "env_var": "agentPoolSizeGpt4",
            "name": "gpt-4",
            "model_name": "gpt-4",
            "version": "turbo-2024-04-09",
            "sku": "Standard",
            "capacity": 10
        },
        {
            "env_var": "agentPoolSizeGpt4Turbo",
            "name": "gpt-4-turbo",
            "model_name": "gpt-4-turbo",
            "version": "2024-04-09",
            "sku": "Standard",
            "capacity": 10
        },
        {
            "env_var": "agentPoolSizeGpt35Turbo",
            "name": "gpt-35-turbo",
            "model_name": "gpt-35-turbo",
            "version": "0125",
            "sku": "Standard",
            "capacity": 10
        },
    ]
    
    # Check existing deployments
    print("[INFO] Checking existing deployments...")
    success, stdout, stderr = run_command([
        "az", "cognitiveservices", "account", "deployment", "list",
        "--name", foundry_name,
        "--resource-group", resource_group,
        "-o", "json"
    ])
    
    existing_deployments = set()
    if success and stdout.strip():
        try:
            deployments = json.loads(stdout)
            existing_deployments = {d["name"] for d in deployments}
            if existing_deployments:
                print(f"   Found: {', '.join(existing_deployments)}")
            else:
                print("   None found")
        except:
            print("   Could not parse existing deployments")
    print()
    
    # Deploy missing models
    deployed_count = 0
    skipped_count = 0
    
    for model in models:
        pool_size = get_env_value(model["env_var"])
        try:
            pool_size = int(pool_size) if pool_size else 0
        except:
            pool_size = 0
        
        if pool_size == 0:
            print(f"[SKIP] {model['name']} (pool size = 0)")
            skipped_count += 1
            continue
        
        if model["name"] in existing_deployments:
            print(f"[OK] {model['name']} already deployed")
            continue
        
        print(f"[DEPLOY] {model['name']}...", end=" ")
        
        success, stdout, stderr = run_command([
            "az", "cognitiveservices", "account", "deployment", "create",
            "--name", foundry_name,
            "--resource-group", resource_group,
            "--deployment-name", model["name"],
            "--model-name", model["model_name"],
            "--model-version", model["version"],
            "--model-format", "OpenAI",
            "--sku-capacity", str(model["capacity"]),
            "--sku-name", model["sku"]
        ], check=False)
        
        if success:
            print("SUCCESS")
            deployed_count += 1
            # Show output for debugging
            if stdout:
                print(f"   Output: {stdout[:300]}")
        else:
            print("FAILED")
            if stderr:
                print(f"   Error: {stderr[:500]}")
            if stdout:
                print(f"   Output: {stdout[:300]}")
    
    print()
    print(f"[SUCCESS] Deployment complete: {deployed_count} deployed, {skipped_count} skipped")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
