#!/usr/bin/env python3
"""
Create federated credentials for GitHub Actions environments.

This script creates Azure AD federated credentials for GitHub Actions OIDC authentication.
Run this ONCE per repository to set up federated credentials for all environments.

Prerequisites:
- Azure CLI installed and authenticated: az login
- Permissions: Owner or User Access Administrator on the subscription
- .env file with GITHUB_REPO=owner/repo
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manually parse .env if dotenv not available
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def run_command(cmd: list, check: bool = True) -> tuple:
    """Run a command and return stdout, stderr, and return code."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    if check and result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def get_service_principal():
    """Get the service principal app ID from environment or prompt."""
    app_id = os.getenv("AZURE_CLIENT_ID")
    
    if not app_id:
        print("❌ AZURE_CLIENT_ID not found in .env file")
        print("\nOptions:")
        print("  1. Add AZURE_CLIENT_ID=<your-sp-app-id> to .env file")
        print("  2. Create a new service principal:")
        print("     az ad sp create-for-rbac --name github-actions-bing-grounding \\")
        print("       --role Contributor \\")
        print("       --scopes /subscriptions/<subscription-id>")
        sys.exit(1)
    
    return app_id


def get_repo_name():
    """Get GitHub repo from environment."""
    repo = os.getenv("GITHUB_REPO")
    
    if not repo or '/' not in repo:
        print("❌ GITHUB_REPO not found or invalid in .env file")
        print("   Add to .env: GITHUB_REPO=owner/repo")
        print(f"   Example: GITHUB_REPO=drewelewis/ai-bing-grounding-mcp-appservice")
        sys.exit(1)
    
    return repo


def create_federated_credential(app_id: str, repo: str, environment: str):
    """Create a federated credential for a GitHub environment."""
    
    credential_name = f"github-{environment}"
    
    # Check if credential already exists
    check_cmd = [
        "az", "ad", "app", "federated-credential", "list",
        "--id", app_id,
        "--query", f"[?name=='{credential_name}'].name",
        "-o", "tsv"
    ]
    
    existing, _, _ = run_command(check_cmd, check=False)
    
    if existing:
        print(f"  ⏭️  {environment} - already exists, skipping")
        return False
    
    # Create the credential
    subject = f"repo:{repo}:environment:{environment}"
    
    create_cmd = [
        "az", "ad", "app", "federated-credential", "create",
        "--id", app_id,
        "--parameters", f'{{"name":"{credential_name}","issuer":"https://token.actions.githubusercontent.com","subject":"{subject}","description":"GitHub Actions deployment for {environment}","audiences":["api://AzureADTokenExchange"]}}'
    ]
    
    try:
        run_command(create_cmd)
        print(f"  ✅ {environment} - created")
        return True
    except:
        print(f"  ❌ {environment} - failed to create")
        return False


def main():
    print("🔐 Azure AD Federated Credentials Setup")
    print()
    
    # Check Azure CLI is installed and authenticated
    print("Checking Azure CLI authentication...")
    stdout, _, code = run_command(["az", "account", "show"], check=False)
    
    if code != 0:
        print("❌ Azure CLI not authenticated")
        print("   Run: az login")
        sys.exit(1)
    
    print("✅ Azure CLI authenticated")
    print()
    
    # Get configuration
    app_id = get_service_principal()
    repo = get_repo_name()
    
    print(f"📦 Repository: {repo}")
    print(f"🔑 Service Principal: {app_id}")
    print()
    
    # Environments to create credentials for
    environments = [
        "production_primary",
        "production_secondary",
        "qa_primary",
        "qa_secondary"
    ]
    
    print(f"Creating federated credentials for {len(environments)} environments...")
    print()
    
    created_count = 0
    for env in environments:
        if create_federated_credential(app_id, repo, env):
            created_count += 1
    
    print()
    print("="*60)
    if created_count > 0:
        print(f"✅ Created {created_count} new federated credential(s)")
    else:
        print("✅ All federated credentials already exist")
    print()
    print("Next steps:")
    print("  1. Verify credentials in Azure Portal:")
    print(f"     Entra ID → App registrations → {app_id[:8]}... → Federated credentials")
    print("  2. Run infrastructure deployment:")
    print("     gh workflow run deploy-infra.yml --field action=provision --field environment=qa")


if __name__ == "__main__":
    main()
