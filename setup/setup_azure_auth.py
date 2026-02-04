#!/usr/bin/env python3
"""
Complete Azure authentication setup for GitHub Actions.

This script:
1. Creates Azure Service Principal
2. Creates federated credentials for GitHub environments
3. Sets GitHub repository secrets
4. Updates .env file with credentials

Run once per repository to set up GitHub Actions authentication.
"""

import json
import subprocess
import sys
from pathlib import Path

def run_command(cmd, capture_output=True):
    """Run shell command and return result."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True
    )
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def get_input(prompt, required=True):
    """Get user input with validation."""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("❌ This field is required")

def select_region(region_type="primary"):
    """Interactive region selector."""
    regions = [
        ("eastus", "East US"),
        ("eastus2", "East US 2"),
        ("westus", "West US"),
        ("westus2", "West US 2"),
        ("westus3", "West US 3"),
        ("centralus", "Central US"),
        ("northcentralus", "North Central US"),
        ("southcentralus", "South Central US"),
        ("westcentralus", "West Central US"),
        ("canadacentral", "Canada Central"),
        ("canadaeast", "Canada East"),
        ("brazilsouth", "Brazil South"),
        ("northeurope", "North Europe"),
        ("westeurope", "West Europe"),
        ("uksouth", "UK South"),
        ("ukwest", "UK West"),
        ("francecentral", "France Central"),
        ("germanywestcentral", "Germany West Central"),
        ("norwayeast", "Norway East"),
        ("switzerlandnorth", "Switzerland North"),
        ("swedencentral", "Sweden Central"),
        ("australiaeast", "Australia East"),
        ("australiasoutheast", "Australia Southeast"),
        ("japaneast", "Japan East"),
        ("japanwest", "Japan West"),
        ("koreacentral", "Korea Central"),
        ("southeastasia", "Southeast Asia"),
        ("eastasia", "East Asia"),
        ("southindia", "South India"),
        ("centralindia", "Central India"),
        ("westindia", "West India"),
    ]
    
    print(f"\n📍 Select {region_type} region:")
    print("-" * 70)
    for i, (code, name) in enumerate(regions, 1):
        print(f"  {i:2}. {name:30} ({code})")
    print()
    
    while True:
        choice = input(f"Enter number (1-{len(regions)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(regions):
                selected = regions[idx][0]
                print(f"  ✅ Selected: {regions[idx][1]} ({selected})")
                return selected
            else:
                print(f"❌ Please enter a number between 1 and {len(regions)}")
        except ValueError:
            print("❌ Please enter a valid number")

def main():
    print("=" * 70)
    print("Azure Authentication Setup for GitHub Actions")
    print("=" * 70)
    print()
    
    # Check Azure CLI authentication
    print("🔍 Checking Azure CLI authentication...")
    try:
        result = run_command("az account show --query id -o tsv")
        subscription_id = result.stdout.strip()
        print(f"✅ Authenticated with Azure")
        print(f"   Subscription ID: {subscription_id}")
        print()
        
        # Ask for confirmation or allow override
        while True:
            override = input(f"Use this subscription? (Y/n): ").strip().lower()
            if override in ('', 'y', 'yes'):
                break
            elif override == 'n' or override == 'no':
                subscription_id = get_input("Enter Azure Subscription ID: ")
                break
            else:
                print("❌ Please enter Y or n")
    except:
        print("❌ Not authenticated with Azure CLI")
        print("   Please run: az login")
        sys.exit(1)
    
    # Step 1: Get required information
    print("📋 Step 1: Collect Information")
    print("-" * 70)
    
    # Environment name
    print("\nEnvironment name (e.g., 'production', 'qa', 'dev'):")
    env_name = get_input("Environment: ").lower()
    
    # GitHub repository
    github_repo = get_input("\nGitHub Repository (owner/repo): ")
    
    # Region selection
    primary_region = select_region("primary")
    secondary_region = select_region("secondary")
    
    # Service principal name
    sp_name = get_input("\nService Principal Name [github-actions-bing-grounding]: ", required=False) or "github-actions-bing-grounding"
    
    print()
    
    # Step 2: Create Service Principal
    print("🔐 Step 2: Create Azure Service Principal")
    print("-" * 70)
    print(f"Creating service principal '{sp_name}'...")
    
    cmd = f"""az ad sp create-for-rbac \
        --name "{sp_name}" \
        --role Contributor \
        --scopes /subscriptions/{subscription_id} \
        --output json"""
    
    result = run_command(cmd)
    sp_data = json.loads(result.stdout)
    
    client_id = sp_data['appId']
    tenant_id = sp_data['tenant']
    
    print(f"✅ Service Principal created:")
    print(f"   Client ID: {client_id}")
    print(f"   Tenant ID: {tenant_id}")
    print()
    
    # Step 3: Update .env file
    print("📝 Step 3: Update .env File")
    print("-" * 70)
    
    # Get repo root directory (parent of setup/)
    repo_root = Path(__file__).parent.parent
    env_file = repo_root / ".env"
    env_content = {}
    
    # Read existing .env if it exists
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # Update with new values
    env_content['AZURE_CLIENT_ID'] = client_id
    env_content['AZURE_TENANT_ID'] = tenant_id
    env_content['AZURE_SUBSCRIPTION_ID'] = subscription_id
    env_content['GITHUB_REPO'] = github_repo
    env_content['AZURE_ENV_NAME'] = env_name
    env_content['AZURE_LOCATION_PRIMARY'] = primary_region
    env_content['AZURE_LOCATION_SECONDARY'] = secondary_region
    
    # Write back to .env
    try:
        with open(env_file, 'w') as f:
            f.write("# Azure Authentication\n")
            f.write(f"AZURE_CLIENT_ID={env_content['AZURE_CLIENT_ID']}\n")
            f.write(f"AZURE_TENANT_ID={env_content['AZURE_TENANT_ID']}\n")
            f.write(f"AZURE_SUBSCRIPTION_ID={env_content['AZURE_SUBSCRIPTION_ID']}\n")
            f.write(f"GITHUB_REPO={env_content['GITHUB_REPO']}\n")
            f.write("\n# Deployment Configuration\n")
            f.write(f"AZURE_ENV_NAME={env_content['AZURE_ENV_NAME']}\n")
            f.write(f"AZURE_LOCATION_PRIMARY={env_content['AZURE_LOCATION_PRIMARY']}\n")
            f.write(f"AZURE_LOCATION_SECONDARY={env_content['AZURE_LOCATION_SECONDARY']}\n")
            f.write("\n")
            
            # Write other existing values
            for key, value in env_content.items():
                if key not in ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_SUBSCRIPTION_ID', 'GITHUB_REPO', 
                              'AZURE_ENV_NAME', 'AZURE_LOCATION_PRIMARY', 'AZURE_LOCATION_SECONDARY']:
                    f.write(f"{key}={value}\n")
        
        print(f"✅ Updated {env_file}")
    except Exception as e:
        print(f"❌ Failed to update .env file: {e}")
        sys.exit(1)
    print()
    
    # Step 4: Create Federated Credentials
    print("🔑 Step 4: Create Federated Credentials for GitHub Environments")
    print("-" * 70)
    
    # Create credentials for the environment the user specified
    environments = [
        f'{env_name}_primary',
        f'{env_name}_secondary'
    ]
    
    for env_suffix in environments:
        credential_name = f"github-{env_suffix.replace('_', '-')}"
        subject = f"repo:{github_repo}:environment:{env_suffix}"
        
        # Check if credential already exists
        check_cmd = f'az ad app federated-credential list --id {client_id} --query "[?name==\'{credential_name}\']" -o json'
        result = run_command(check_cmd)
        existing = json.loads(result.stdout)
        
        if existing:
            print(f"   ⏭️  {credential_name} already exists, skipping")
            continue
        
        # Create federated credential using JSON file to avoid shell escaping issues
        credential_json = {
            "name": credential_name,
            "issuer": "https://token.actions.githubusercontent.com",
            "subject": subject,
            "description": f"GitHub Actions federated credential for {env_suffix}",
            "audiences": ["api://AzureADTokenExchange"]
        }
        
        # Write to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(credential_json, f)
            temp_file = f.name
        
        try:
            create_cmd = f'az ad app federated-credential create --id {client_id} --parameters @{temp_file}'
            run_command(create_cmd, capture_output=False)
            print(f"   ✅ Created {credential_name}")
        finally:
            import os
            os.unlink(temp_file)
    
    print()
    
    # Step 5: Set GitHub Secrets
    print("🔒 Step 5: Set GitHub Repository Secrets")
    print("-" * 70)
    
    # Check if gh CLI is available
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  GitHub CLI (gh) not found. Skipping secret setup.")
        print("   Install from: https://cli.github.com/")
        print("   Or set secrets manually in GitHub:")
        print(f"   - AZURE_CLIENT_ID={client_id}")
        print(f"   - AZURE_TENANT_ID={tenant_id}")
        print(f"   - AZURE_SUBSCRIPTION_ID={subscription_id}")
        print()
    else:
        secrets = {
            'AZURE_CLIENT_ID': client_id,
            'AZURE_TENANT_ID': tenant_id,
            'AZURE_SUBSCRIPTION_ID': subscription_id
        }
        
        for key, value in secrets.items():
            cmd = f'gh secret set {key} --body "{value}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Set {key}")
            else:
                print(f"   ⚠️  Failed to set {key}: {result.stderr}")
        
        print()
    
    # Step 6: Set GitHub Environment Variables
    print("🔧 Step 6: Set GitHub Environment Variables")
    print("-" * 70)
    
    # Check if gh CLI is available
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  GitHub CLI (gh) not found. You'll need to set environment variables manually.")
        print(f"   Or install from: https://cli.github.com/")
        print()
    else:
        # Set environment variables for primary and secondary environments
        env_vars = {
            'AZURE_ENV_NAME': env_name,
            'AZURE_LOCATION_PRIMARY': primary_region,
            'AZURE_LOCATION_SECONDARY': secondary_region
        }
        
        for env_suffix in [f'{env_name}_primary', f'{env_name}_secondary']:
            github_env_name = env_suffix
            print(f"\n   Setting variables for {github_env_name}...")
            
            for key, value in env_vars.items():
                cmd = f'gh variable set {key} --body "{value}" --env {github_env_name}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"      ✅ Set {key}={value}")
                else:
                    # Environment might not exist yet, that's okay
                    print(f"      ⏭️  Environment {github_env_name} will be created during first deployment")
                    break
        
        print()
    
    # Step 7: Success Summary
    print("=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print()
    print(f"Configuration saved:")
    print(f"  Environment: {env_name}")
    print(f"  Primary Region: {primary_region}")
    print(f"  Secondary Region: {secondary_region}")
    print(f"  GitHub Repo: {github_repo}")
    print()
    print("=" * 70)
    print("🚀 NEXT STEPS")
    print("=" * 70)
    print()
    print("1️⃣  Deploy Infrastructure (wait ~10-15 minutes)")
    print()
    print(f"  gh workflow run deploy-infra.yml --field action=provision --field environment={env_name}")
    print()
    print("2️⃣  After deployment completes, get resource names from Azure:")
    print()
    print(f"  az resource list --tag environment={env_name} --query \"[?type=='Microsoft.Web/sites' || type=='Microsoft.CognitiveServices/accounts'].{{name:name, type:type, resourceGroup:resourceGroup}}\" -o table")
    print()
    print("3️⃣  Create environment configuration files:")
    print()
    print(f"  Create .env.{env_name}_primary with:")
    print(f"  ┌─────────────────────────────────────────────────────────────────┐")
    print(f"  │ AZURE_ENV_NAME={env_name}")
    print(f"  │ WEBAPP_NAME=<webapp-name-from-azure>")
    print(f"  │ AI_PROJECT_ENDPOINT=<ai-foundry-endpoint-from-azure>")
    print(f"  │ AI_PROJECT_NAME=<ai-project-name-from-azure>")
    print(f"  │ REGION={primary_region}")
    print(f"  │ RESOURCE_GROUP=rg-bing-grounding-mcp-{env_name}-primary")
    print(f"  └─────────────────────────────────────────────────────────────────┘")
    print()
    print(f"  Create .env.{env_name}_secondary with:")
    print(f"  ┌─────────────────────────────────────────────────────────────────┐")
    print(f"  │ AZURE_ENV_NAME={env_name}")
    print(f"  │ WEBAPP_NAME=<webapp-name-from-azure>")
    print(f"  │ AI_PROJECT_ENDPOINT=<ai-foundry-endpoint-from-azure>")
    print(f"  │ AI_PROJECT_NAME=<ai-project-name-from-azure>")
    print(f"  │ REGION={secondary_region}")
    print(f"  │ RESOURCE_GROUP=rg-bing-grounding-mcp-{env_name}-secondary")
    print(f"  └─────────────────────────────────────────────────────────────────┘")
    print()
    print("4️⃣  Sync configuration to GitHub:")
    print()
    print(f"  python configure/sync_github_env_simple.py --environment {env_name}_primary")
    print(f"  python configure/sync_github_env_simple.py --environment {env_name}_secondary")
    print()
    print("5️⃣  Deploy the application:")
    print()
    print(f"  gh workflow run deploy.yml --field environment={env_name}")
    print()

if __name__ == '__main__':
    main()
