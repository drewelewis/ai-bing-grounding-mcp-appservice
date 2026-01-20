#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Bing Grounding resource is correctly configured.

Per Microsoft documentation, the Bing Grounding resource MUST be in the
SAME resource group as the AI Foundry project. This script verifies that
requirement is met. No explicit connection creation is needed - the 
connection is automatic when both resources are in the same resource group.

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding

Usage:
    python scripts/postprovision_create_bing_connection.py
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

def main():
    print()
    print("=" * 80)
    print("Verifying Bing Grounding Configuration")
    print("=" * 80)
    print()
    
    # Get environment values
    subscription_id = get_env_value("AZURE_SUBSCRIPTION_ID")
    resource_group = get_env_value("AZURE_RESOURCE_GROUP")
    project_name = get_env_value("AZURE_AI_PROJECT_NAME")
    bing_resource_id = get_env_value("BING_GROUNDING_RESOURCE_ID")
    bing_resource_name = get_env_value("BING_GROUNDING_RESOURCE_NAME")
    bing_resource_group = get_env_value("BING_GROUNDING_RESOURCE_GROUP")
    
    if not all([subscription_id, resource_group, project_name, bing_resource_id, bing_resource_group]):
        print("[ERROR] Missing required environment variables!")
        print(f"  AZURE_SUBSCRIPTION_ID: {subscription_id}")
        print(f"  AZURE_RESOURCE_GROUP: {resource_group}")
        print(f"  AZURE_AI_PROJECT_NAME: {project_name}")
        print(f"  BING_GROUNDING_RESOURCE_ID: {bing_resource_id}")
        print(f"  BING_GROUNDING_RESOURCE_GROUP: {bing_resource_group}")
        return 1
    
    print(f"[INFO] AI Project Resource Group: {resource_group}")
    print(f"[INFO] Bing Resource Group: {bing_resource_group}")
    print(f"[INFO] Bing Resource Name: {bing_resource_name}")
    print()
    
    # Verify same resource group
    if bing_resource_group != resource_group:
        print("=" * 80)
        print("❌ ERROR: RESOURCE GROUP MISMATCH")
        print("=" * 80)
        print()
        print("Per Microsoft documentation, the Bing Grounding resource MUST be")
        print("in the SAME resource group as your AI Foundry project.")
        print()
        print(f"  AI Project RG: {resource_group}")
        print(f"  Bing Resource RG: {bing_resource_group}")
        print()
        print("The connection will NOT work with this configuration!")
        print()
        print("To fix:")
        print(f"1. Create a new Bing resource in resource group: {resource_group}")
        print("2. Run: azd env select")
        print("3. Delete the current environment variables related to Bing")
        print("4. Run: azd up (and select the new Bing resource)")
        print()
        print("Reference:")
        print("https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding")
        print("=" * 80)
        return 1
    
    print("=" * 80)
    print("✅ VERIFICATION PASSED")
    print("=" * 80)
    print()
    print("Bing Grounding resource is correctly configured:")
    print(f"  • Bing resource '{bing_resource_name}' is in the same resource group")
    print(f"  • Resource group: {resource_group}")
    print(f"  • Connection will be automatic (no explicit connection needed)")
    print()
    print("Per Microsoft documentation:")
    print('  "Make sure you create this Grounding with Bing Search resource in the')
    print('   same resource group as your Azure AI Agent, AI Project, and other resources"')
    print()
    print("Reference:")
    print("https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding")
    print()
    print("Agents will automatically use this Bing resource for grounding.")
    print("=" * 80)
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
