#!/usr/bin/env python3
"""
Cleanup old federated credentials from service principal.

This script removes outdated regional federated credentials that were created
before switching to the enterprise pattern of one credential per environment.
"""

import json
import subprocess
import sys

def run_command(cmd):
    """Run shell command and return result."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result

def main():
    print("=" * 70)
    print("Cleanup Old Federated Credentials")
    print("=" * 70)
    print()
    
    # Get service principal from Azure CLI
    print("🔍 Finding service principal...")
    result = run_command("az ad sp list --filter \"displayName eq 'github-actions-bing-grounding'\" --query \"[0].appId\" -o tsv")
    
    if result.returncode != 0 or not result.stdout.strip():
        print("❌ Service principal 'github-actions-bing-grounding' not found")
        sys.exit(1)
    
    app_id = result.stdout.strip()
    print(f"✅ Found service principal: {app_id}")
    print()
    
    # Get app object ID
    result = run_command(f"az ad app show --id {app_id} --query id -o tsv")
    if result.returncode != 0:
        print("❌ Failed to get app object ID")
        sys.exit(1)
    
    app_object_id = result.stdout.strip()
    
    # List all federated credentials
    print("📋 Listing federated credentials...")
    result = run_command(f"az ad app federated-credential list --id {app_id} -o json")
    
    if result.returncode != 0:
        print("❌ Failed to list federated credentials")
        sys.exit(1)
    
    credentials = json.loads(result.stdout)
    
    if not credentials:
        print("ℹ️  No federated credentials found")
        return
    
    print(f"Found {len(credentials)} federated credential(s):")
    print()
    
    # Patterns for old credentials to remove
    old_patterns = [
        '-primary',
        '-secondary',
        'development-'
    ]
    
    credentials_to_keep = []
    credentials_to_delete = []
    
    for cred in credentials:
        name = cred['name']
        # Check if credential matches old pattern
        if any(pattern in name for pattern in old_patterns):
            credentials_to_delete.append(cred)
        else:
            credentials_to_keep.append(cred)
    
    # Show what will be kept
    if credentials_to_keep:
        print("✅ Keeping:")
        for cred in credentials_to_keep:
            print(f"   • {cred['name']}")
            print(f"     Subject: {cred['subject']}")
        print()
    
    # Show what will be deleted
    if credentials_to_delete:
        print("🗑️  Will delete:")
        for cred in credentials_to_delete:
            print(f"   • {cred['name']}")
            print(f"     Subject: {cred['subject']}")
        print()
        
        # Confirm deletion
        response = input("Proceed with deletion? (Y/n): ").strip().lower()
        if response not in ('', 'y', 'yes'):
            print("❌ Cancelled")
            return
        
        print()
        print("🗑️  Deleting old credentials...")
        
        for cred in credentials_to_delete:
            cred_id = cred['id']
            cred_name = cred['name']
            
            # Delete using the credential ID
            result = run_command(f"az ad app federated-credential delete --id {app_id} --federated-credential-id {cred_id}")
            
            if result.returncode == 0:
                print(f"   ✅ Deleted: {cred_name}")
            else:
                print(f"   ❌ Failed to delete: {cred_name}")
                print(f"      Error: {result.stderr}")
        
        print()
        print("✅ Cleanup complete!")
    else:
        print("ℹ️  No old credentials to delete")
    
    print()

if __name__ == '__main__':
    main()
