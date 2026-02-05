#!/usr/bin/env python3
"""
Set GitHub repository secrets for Azure authentication.

This script uses GitHub CLI to set repository secrets needed for GitHub Actions.

Prerequisites:
- GitHub CLI installed: https://cli.github.com/
- Authenticated: gh auth login
- .env file with AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, GITHUB_REPO
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


def check_gh_cli():
    """Check if GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {result.stdout.split()[0]} {result.stdout.split()[2]}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI not found")
        print("   Install: https://cli.github.com/")
        print("   Or run: winget install GitHub.cli")
        sys.exit(1)
    
    # Check authentication
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            check=True
        )
        print("✅ Authenticated with GitHub")
    except subprocess.CalledProcessError:
        print("❌ Not authenticated with GitHub")
        print("   Run: gh auth login")
        sys.exit(1)


def get_repo():
    """Get repository from .env."""
    repo = os.getenv("GITHUB_REPO")
    if not repo:
        print("❌ GITHUB_REPO not found in .env file")
        print("   Add: GITHUB_REPO=owner/repo")
        sys.exit(1)
    return repo


def set_secret(repo: str, name: str, value: str) -> bool:
    """Set a repository secret."""
    try:
        subprocess.run(
            ["gh", "secret", "set", name, "--repo", repo, "--body", value],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to set {name}: {e.stderr}")
        return False


def main():
    print("🔐 GitHub Repository Secrets Setup")
    print()
    
    # Check prerequisites
    check_gh_cli()
    print()
    
    # Get repository
    repo = get_repo()
    print(f"📦 Repository: {repo}")
    print()
    
    # Get secrets from .env
    secrets = {
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID"),
        "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID"),
        "AZURE_SUBSCRIPTION_ID": os.getenv("AZURE_SUBSCRIPTION_ID")
    }
    
    # Validate all secrets are present
    missing = [name for name, value in secrets.items() if not value]
    if missing:
        print(f"❌ Missing values in .env file:")
        for name in missing:
            print(f"   - {name}")
        print("\nAdd these to your .env file:")
        print("   AZURE_CLIENT_ID=your-service-principal-app-id")
        print("   AZURE_TENANT_ID=your-tenant-id")
        print("   AZURE_SUBSCRIPTION_ID=your-subscription-id")
        sys.exit(1)
    
    print(f"Setting {len(secrets)} repository secrets...")
    print()
    
    # Set each secret
    success_count = 0
    for name, value in secrets.items():
        if set_secret(repo, name, value):
            print(f"  ✅ {name}")
            success_count += 1
        else:
            print(f"  ❌ {name}")
    
    print()
    print("="*60)
    if success_count == len(secrets):
        print(f"✅ All {success_count} secrets set successfully!")
    else:
        print(f"⚠️  Only {success_count}/{len(secrets)} secrets were set")
    print()
    print("Next steps:")
    print("  1. Verify secrets in GitHub:")
    print(f"     https://github.com/{repo}/settings/secrets/actions")
    print("  2. Set up environment variables:")
    print("     python sync_github_env_simple.py --environment all")


if __name__ == "__main__":
    main()
