#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purge soft-deleted Azure resources before deployment.

This script attempts to purge soft-deleted Key Vaults and AI Foundry (Cognitive Services)
resources that might conflict with new deployments. Soft-deleted resources have a 90-day
retention period and must be purged before creating resources with the same name.
"""
import os
import sys
import io
import subprocess
import json

# Windows UTF-8 encoding support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def run_command(cmd, check=False):
    """Run a command and return output."""
    try:
        # On Windows, need shell=True for az commands
        result = subprocess.run(
            cmd if isinstance(cmd, str) else ' '.join(cmd),
            capture_output=True,
            text=True,
            check=check,
            shell=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr
    except Exception as e:
        return False, "", str(e)

def purge_keyvaults(subscription_id, location):
    """Purge soft-deleted Key Vaults."""
    print("🔍 Checking for soft-deleted Key Vaults...")
    
    # List soft-deleted Key Vaults
    success, stdout, stderr = run_command([
        "az", "keyvault", "list-deleted",
        "--subscription", subscription_id,
        "--resource-type", "vault",
        "-o", "json"
    ])
    
    if not success:
        print(f"  ⚠️  Could not list deleted Key Vaults (may not have permissions)")
        return
    
    try:
        deleted_vaults = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse deleted Key Vaults list")
        return
    
    if not deleted_vaults:
        print(f"  ✅ No soft-deleted Key Vaults found")
        return
    
    # Filter for the current location
    local_deleted = [v for v in deleted_vaults if v.get('properties', {}).get('location', '').replace(' ', '').lower() == location.replace(' ', '').lower()]
    
    if not local_deleted:
        print(f"  ✅ No soft-deleted Key Vaults in {location}")
        return
    
    print(f"  🗑️  Found {len(local_deleted)} soft-deleted Key Vault(s) in {location}")
    
    for vault in local_deleted:
        vault_name = vault.get('name')
        vault_location = vault.get('properties', {}).get('location', location)
        
        print(f"     Purging: {vault_name}...", end=" ")
        success, stdout, stderr = run_command([
            "az", "keyvault", "purge",
            "--name", vault_name,
            "--location", vault_location,
            "--subscription", subscription_id
        ])
        
        if success:
            print("✅")
        else:
            print(f"⚠️  (may not exist or already purged)")

def purge_cognitive_services(subscription_id, location, resource_group_prefix):
    """Purge soft-deleted Cognitive Services accounts (AI Foundry)."""
    print("🔍 Checking for soft-deleted Cognitive Services (AI Foundry)...")
    
    # List all soft-deleted accounts
    success, stdout, stderr = run_command([
        "az", "cognitiveservices", "account", "list-deleted",
        "--subscription", subscription_id,
        "-o", "json"
    ])
    
    if not success:
        print(f"  ⚠️  Could not list deleted Cognitive Services")
        print(f"  Error: {stderr[:200]}")
        return
    
    try:
        deleted_accounts = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse deleted Cognitive Services list")
        return
    
    if not deleted_accounts:
        print(f"  ✅ No soft-deleted Cognitive Services found")
        return
    
    # Filter for location - purge ALL in the location to avoid conflicts
    matching_accounts = []
    for account in deleted_accounts:
        props = account.get('properties', {})
        acc_location = props.get('location', '').replace(' ', '').lower()
        
        # Purge any soft-deleted account in the same location (safer approach)
        if acc_location == location.replace(' ', '').lower():
            matching_accounts.append(account)
    
    if not matching_accounts:
        print(f"  ✅ No soft-deleted Cognitive Services in {location}")
        return
    
    print(f"  🗑️  Found {len(matching_accounts)} soft-deleted Cognitive Services account(s) in {location}")
    
    for account in matching_accounts:
        account_name = account.get('name')
        resource_id = account.get('id', '')
        # Extract resource group from ID
        parts = resource_id.split('/')
        resource_group = parts[4] if len(parts) > 4 else None
        acc_location = account.get('properties', {}).get('location', location)
        
        print(f"     Purging: {account_name} (RG: {resource_group})...", end=" ", flush=True)
        
        # Try purge command
        success, stdout, stderr = run_command([
            "az", "cognitiveservices", "account", "purge",
            "--name", account_name,
            "--resource-group", resource_group,
            "--location", acc_location,
            "--subscription", subscription_id
        ])
        
        if success:
            print("✅")
        else:
            # If purge fails, might already be purged
            print(f"⚠️")
            if "ResourceNotFound" not in stderr and "NotFound" not in stderr:
                print(f"       Error: {stderr[:200]}")


def purge_apim(subscription_id, location, resource_group_prefix):
    """Purge soft-deleted API Management instances."""
    print("🔍 Checking for soft-deleted API Management instances...")
    
    # List soft-deleted APIM instances (no --subscription parameter for this command)
    success, stdout, stderr = run_command([
        "az", "apim", "deletedservice", "list",
        "-o", "json"
    ])
    
    if not success:
        print(f"  ⚠️  Could not list deleted API Management instances")
        if stderr:
            print(f"  Error: {stderr}")
        return
    
    # Debug: show raw output to understand the structure
    print(f"  [DEBUG] Raw stdout length: {len(stdout)}")
    print(f"  [DEBUG] Raw stdout (first 500 chars): {stdout[:500]}")
    
    try:
        result = json.loads(stdout) if stdout.strip() else {}
        # The API returns { "value": [...] } structure
        deleted_apims = result.get('value', []) if isinstance(result, dict) else result
        print(f"  [DEBUG] Parsed type: {type(deleted_apims)}")
        print(f"  [DEBUG] Found {len(deleted_apims)} deleted service(s)")
        if deleted_apims:
            print(f"  [DEBUG] First item keys: {deleted_apims[0].keys() if isinstance(deleted_apims, list) and len(deleted_apims) > 0 else 'N/A'}")
            for apim in deleted_apims:
                print(f"  [DEBUG]   - {apim.get('name', 'unknown')} in {apim.get('location', 'unknown')}")
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Could not parse deleted API Management list: {e}")
        print(f"  Raw output: {stdout[:200]}")
        return
    
    if not deleted_apims:
        print(f"  ✅ No soft-deleted API Management instances found")
        return
    
    # Filter for matching location
    matching_apims = []
    for apim in deleted_apims:
        apim_location = apim.get('location', '').replace(' ', '').lower()
        apim_name = apim.get('name', '')
        
        # Check if location matches
        if apim_location == location.replace(' ', '').lower():
            matching_apims.append({
                'name': apim_name,
                'location': apim.get('location', location)
            })
    
    if not matching_apims:
        print(f"  ✅ No soft-deleted API Management instances in {location}")
        return
    
    print(f"  🗑️  Found {len(matching_apims)} soft-deleted API Management instance(s)")
    
    for apim in matching_apims:
        apim_name = apim['name']
        apim_location = apim['location']
        
        print(f"     Purging: {apim_name} in {apim_location}...", end=" ", flush=True)
        success, stdout, stderr = run_command([
            "az", "apim", "deletedservice", "purge",
            "--service-name", apim_name,
            "--location", f'"{apim_location}"'
        ])
        
        if success:
            print("✅")
        else:
            print(f"❌")
            if stderr:
                print(f"       Error: {stderr[:200]}")

def main():
    print()
    print("=" * 80)
    print("Purging Soft-Deleted Resources")
    print("=" * 80)
    print()
    
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    location = os.getenv("AZURE_LOCATION", "eastus")
    env_name = os.getenv("AZURE_ENV_NAME")
    
    if not subscription_id:
        print("❌ AZURE_SUBSCRIPTION_ID not set")
        sys.exit(1)
    
    if not env_name:
        print("❌ AZURE_ENV_NAME not set")
        sys.exit(1)
    
    # Resource group pattern for this deployment
    resource_group_prefix = f"rg-bing-grounding-mcp-{env_name}"
    
    print(f"📍 Subscription: {subscription_id}")
    print(f"📍 Location: {location}")
    print(f"📍 Resource Group Pattern: {resource_group_prefix}")
    print()
    
    # Purge soft-deleted resources
    purge_keyvaults(subscription_id, location)
    print()
    purge_cognitive_services(subscription_id, location, resource_group_prefix)
    print()
    purge_apim(subscription_id, location, resource_group_prefix)
    
    print()
    print("✅ Soft-deleted resource purge check complete!")
    print()

if __name__ == "__main__":
    main()
