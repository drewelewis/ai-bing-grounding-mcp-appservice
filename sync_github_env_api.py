#!/usr/bin/env python3
"""
Sync environment configuration from .env files to GitHub Environment variables using REST API.

Requires: GITHUB_TOKEN environment variable or in .env file

Usage:
    python sync_github_env_api.py --environment production_primary
    python sync_github_env_api.py --environment all
    python sync_github_env_api.py  # Interactive selection
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Load .env file for GITHUB_TOKEN and GITHUB_REPO
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv not available, manually parse .env
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


# Get repo info from .env or git remote
GITHUB_REPO = os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY")


def get_github_token() -> str:
    """Get GitHub token from environment or .env file."""
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("❌ GITHUB_TOKEN not found in .env file or environment")
        print("\nCreate a Personal Access Token:")
        print("  1. Go to: https://github.com/settings/tokens/new")
        print("  2. Select scopes: repo, admin:org")
        print("  3. Generate token")
        print("  4. Add to .env file:")
        print("     GITHUB_TOKEN=ghp_xxxxx")
        sys.exit(1)
    return token


def get_repo_info() -> tuple:
    """Get owner and repo name."""
    repo = GITHUB_REPO
    
    if not repo:
        print("❌ Could not determine GitHub repository")
        print("   Add to .env file: GITHUB_REPO=owner/repo")
        sys.exit(1)
    
    parts = repo.split("/")
    if len(parts) != 2:
        print(f"❌ Invalid repository format: {repo}")
        print("   Expected: owner/repo")
        sys.exit(1)
    
    return parts[0], parts[1]


def github_api_request(method: str, endpoint: str, token: str, data: dict = None) -> dict:
    """Make a GitHub API request."""
    url = f"https://api.github.com{endpoint}"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    request_data = json.dumps(data).encode('utf-8') if data else None
    
    req = Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urlopen(req) as response:
            if response.status in (200, 201, 204):
                response_data = response.read()
                return json.loads(response_data) if response_data else {}
            else:
                print(f"❌ API request failed: {response.status}")
                return None
    except HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ API error: {e.code} - {error_body}")
        return None


def get_public_key(owner: str, repo: str, environment: str, token: str) -> dict:
    """Get the public key for encrypting environment variables."""
    # First, check if environment exists, if not try to create it
    env_endpoint = f"/repos/{owner}/{repo}/environments/{environment}"
    env_response = github_api_request("GET", env_endpoint, token)
    
    if not env_response:
        # Environment doesn't exist, try to create it with minimal settings
        print(f"  📦 Creating environment: {environment}")
        
        # For environment creation, we need to use a PUT with at least empty body
        # This works for both personal and org repos with proper token permissions
        create_data = {
            "wait_timer": 0,
            "reviewers": [],
            "deployment_branch_policy": None
        }
        
        create_response = github_api_request("PUT", env_endpoint, token, create_data)
        
        if not create_response:
            print(f"  ⚠️  Could not create environment - trying to set variables anyway...")
            # Don't fail - environment might exist but GET failed, or we can still set variables
    
    # Return dummy key (variables don't need encryption, only secrets do)
    return {"key_id": "not-needed", "key": "not-needed"}


def create_or_update_variable(owner: str, repo: str, environment: str, name: str, value: str, token: str) -> bool:
    """Create or update an environment variable."""
    endpoint = f"/repos/{owner}/{repo}/environments/{environment}/variables/{name}"
    
    # Try to update first
    response = github_api_request("PATCH", endpoint, token, {"name": name, "value": value})
    
    if response is not None:
        return True
    
    # If update failed, try to create
    endpoint = f"/repos/{owner}/{repo}/environments/{environment}/variables"
    response = github_api_request("POST", endpoint, token, {"name": name, "value": value})
    
    return response is not None


def parse_env_file(env_file: Path) -> dict:
    """Parse .env file and return key-value pairs."""
    variables = {}
    
    if not env_file.exists():
        print(f"❌ File not found: {env_file}")
        return variables
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                variables[key.strip()] = value.strip()
    
    return variables


def sync_environment(environment_name: str, owner: str, repo: str, token: str) -> bool:
    """Sync one environment's .env file to GitHub."""
    env_file = Path(f".env.{environment_name}")
    
    print(f"\n{'='*60}")
    print(f"📝 Syncing: {environment_name}")
    print(f"{'='*60}")
    
    if not env_file.exists():
        print(f"❌ File not found: {env_file}")
        return False
    
    # Parse .env file
    variables = parse_env_file(env_file)
    
    if not variables:
        print(f"⚠️  No variables found in {env_file}")
        return False
    
    print(f"📄 Read {len(variables)} variables from {env_file}")
    
    # Get public key (creates environment if needed)
    public_key = get_public_key(owner, repo, environment_name, token)
    if not public_key:
        print(f"❌ Failed to prepare environment: {environment_name}")
        return False
    
    # Set each variable
    success_count = 0
    for key, value in variables.items():
        if create_or_update_variable(owner, repo, environment_name, key, value, token):
            print(f"  ✅ {key}")
            success_count += 1
        else:
            print(f"  ❌ {key}")
    
    print(f"\n✅ Synced {success_count}/{len(variables)} variables to '{environment_name}'")
    return success_count == len(variables)


def main():
    parser = argparse.ArgumentParser(
        description="Sync .env files to GitHub Environment variables using REST API"
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["production_primary", "production_secondary", "qa_primary", "qa_secondary", "all"],
        help="Environment to sync (or 'all' for all environments)"
    )
    
    args = parser.parse_args()
    
    print("🚀 GitHub Environment Sync (REST API)")
    print()
    
    # Get credentials
    token = get_github_token()
    owner, repo = get_repo_info()
    
    print(f"📦 Repository: {owner}/{repo}")
    print()
    
    # Determine which environments to sync
    environments = []
    
    if args.environment == "all":
        environments = ["production_primary", "production_secondary", "qa_primary", "qa_secondary"]
    elif args.environment:
        environments = [args.environment]
    else:
        # Interactive selection
        print("Available environments:")
        print("  1. production_primary")
        print("  2. production_secondary")
        print("  3. qa_primary")
        print("  4. qa_secondary")
        print("  5. all")
        
        choice = input("\nSelect environment (1-5): ").strip()
        
        env_map = {
            "1": "production_primary",
            "2": "production_secondary",
            "3": "qa_primary",
            "4": "qa_secondary",
            "5": "all"
        }
        
        if choice not in env_map:
            print("❌ Invalid selection")
            sys.exit(1)
        
        if env_map[choice] == "all":
            environments = ["production_primary", "production_secondary", "qa_primary", "qa_secondary"]
        else:
            environments = [env_map[choice]]
    
    # Sync environments
    all_success = True
    for env_name in environments:
        if not sync_environment(env_name, owner, repo, token):
            all_success = False
    
    print(f"\n{'='*60}")
    if all_success:
        print("✅ All environments synced successfully!")
    else:
        print("⚠️  Some environments had errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
