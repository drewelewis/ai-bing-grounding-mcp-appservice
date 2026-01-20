#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Select an existing Bing Grounding resource before deployment.

This script lists available Bing Grounding resources in the subscription
and allows the user to select one. If none exist, provides instructions
to create one via the Portal.

The selected resource ID is saved to .env for use during agent creation.

Usage:
    python scripts/preprovision_select_bing_resource.py
"""
import os
import sys
import json
import subprocess
from pathlib import Path

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

def set_env_value(key: str, value: str):
    """Set environment variable in .azure/{env}/.env"""
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
    env_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing content
    lines = []
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Update or add the key
    found = False
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('#'):
            if '=' in line:
                k, _ = line.split('=', 1)
                if k.strip() == key:
                    lines[i] = f"{key}=\"{value}\"\n"
                    found = True
                    break
    
    if not found:
        lines.append(f"{key}=\"{value}\"\n")
    
    # Write back
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def list_bing_resources(subscription_id: str, target_resource_group: str = None) -> list[dict]:
    """
    List all Bing Grounding resources in the subscription.
    If target_resource_group is provided, filters to only resources in that group.
    Returns list of dicts with 'name', 'resourceGroup', 'id', 'location'.
    """
    cmd = [
        "az", "resource", "list",
        "--subscription", subscription_id,
        "--resource-type", "Microsoft.Bing/accounts",
        "--query", "[?kind=='Bing.Grounding'].{name:name, resourceGroup:resourceGroup, id:id, location:location}",
        "--output", "json"
    ]
    
    success, output, stderr = run_command(cmd)
    
    if not success:
        print(f"[ERROR] Failed to list Bing resources: {stderr}")
        return []
    
    try:
        resources = json.loads(output)
        all_resources = resources if resources else []
        
        # Filter to target resource group if specified
        if target_resource_group and all_resources:
            filtered = [r for r in all_resources if r.get('resourceGroup') == target_resource_group]
            return filtered
        
        return all_resources
    except json.JSONDecodeError:
        return []

def main():
    print()
    print("=" * 80)
    print("Bing Grounding Resource Selection")
    print("=" * 80)
    print()
    
    # Get subscription ID
    subscription_id = get_env_value("AZURE_SUBSCRIPTION_ID")
    
    if not subscription_id:
        print("[ERROR] AZURE_SUBSCRIPTION_ID not found in environment!")
        print("  Run 'azd env set AZURE_SUBSCRIPTION_ID <your-subscription-id>'")
        return 1
    
    # Get target resource group
    target_resource_group = get_env_value("AZURE_RESOURCE_GROUP")
    
    if not target_resource_group:
        # Fallback to constructing from environment name
        env_name = get_env_value("AZURE_ENV_NAME")
        if env_name:
            target_resource_group = f"rg-bing-grounding-mcp-{env_name}"
        else:
            print("[ERROR] AZURE_RESOURCE_GROUP not found in environment!")
            print("  Run 'azd env set AZURE_RESOURCE_GROUP <your-resource-group>'")
            return 1
    
    print(f"[INFO] Subscription: {subscription_id}")
    print(f"[INFO] Target Resource Group: {target_resource_group}")
    print()
    print("[IMPORTANT] Per Microsoft documentation, the Bing Grounding resource")
    print("            MUST be in the SAME resource group as your AI project.")
    print(f"            Only showing resources in: {target_resource_group}")
    print()
    
    # List existing Bing resources in the target resource group
    print("[1/2] Searching for Bing Grounding resources...")
    resources = list_bing_resources(subscription_id, target_resource_group)
    
    if not resources:
        print()
        print("=" * 80)
        print("NO BING GROUNDING RESOURCE FOUND IN TARGET RESOURCE GROUP")
        print("=" * 80)
        print()
        print("A Bing Grounding resource is REQUIRED for this deployment.")
        print()
        print("IMPORTANT: The Bing resource MUST be in the SAME resource group")
        print("           as your AI Foundry project for automatic connection.")
        print()
        print("To create one:")
        print()
        print("1. Open: https://portal.azure.com/#create/Microsoft.BingGroundingSearch")
        print(f"2. Subscription: {subscription_id}")
        print(f"3. Resource Group: {target_resource_group}  ← MUST USE THIS")
        print("4. Name: Choose a unique name (e.g., 'bing-grounding-prod')")
        print("5. Pricing Tier: F0 (Free - 1,000 transactions/month)")
        print("6. Click 'Review + Create' -> 'Create' (takes ~1 minute)")
        print()
        print("After creation, run 'azd up' again.")
        print("=" * 80)
        print()
        return 1
    
    # Display available resources
    print()
    print(f"[INFO] Found {len(resources)} Bing Grounding resource(s):")
    print()
    
    for i, resource in enumerate(resources, 1):
        print(f"  [{i}] {resource['name']}")
        print(f"      Resource Group: {resource['resourceGroup']}")
        print(f"      Location: {resource['location']}")
        print(f"      ID: {resource['id']}")
        print()
    
    # Prompt user to select
    print("[2/2] Select a Bing Grounding resource:")
    
    while True:
        try:
            choice = input(f"Enter number (1-{len(resources)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print()
                print("[CANCELLED] Deployment cancelled by user")
                return 1
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(resources):
                selected = resources[choice_num - 1]
                break
            else:
                print(f"  [ERROR] Please enter a number between 1 and {len(resources)}")
        except ValueError:
            print(f"  [ERROR] Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print()
            print()
            print("[CANCELLED] Deployment cancelled by user")
            return 1
    
    # Save selected resource ID to .env
    resource_id = selected['id']
    resource_name = selected['name']
    resource_group = selected['resourceGroup']
    
    # Validate resource group matches target (defensive check)
    if resource_group != target_resource_group:
        print()
        print("[ERROR] Selected resource is in wrong resource group!")
        print(f"  Selected: {resource_group}")
        print(f"  Required: {target_resource_group}")
        print()
        print("Per Microsoft documentation, the Bing resource MUST be in the")
        print("SAME resource group as your AI Foundry project.")
        print()
        return 1
    
    set_env_value("BING_GROUNDING_RESOURCE_ID", resource_id)
    set_env_value("BING_GROUNDING_RESOURCE_NAME", resource_name)
    set_env_value("BING_GROUNDING_RESOURCE_GROUP", resource_group)
    
    print()
    print(f"[SUCCESS] Selected Bing Grounding resource: {resource_name}")
    print(f"  Resource Group: {resource_group}")
    print(f"  Resource ID: {resource_id}")
    print()
    print("[INFO] Saved to .env - agents will use this resource")
    print("        Connection will be automatic (same resource group)")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
