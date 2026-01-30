#!/usr/bin/env python3
"""
Sync environment configuration from .env files to GitHub Environment variables.

Requires: pip install PyGithub python-dotenv

Usage:
    python sync_github_env_simple.py --environment production_primary
    python sync_github_env_simple.py --environment all
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from github import Github, GithubException
    from dotenv import load_dotenv
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install PyGithub python-dotenv")
    sys.exit(1)

# Load .env file
load_dotenv()


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


def sync_environment(repo, environment_name: str) -> bool:
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
    
    try:
        # Get or create environment
        try:
            env = repo.get_environment(environment_name)
            print(f"  ✅ Environment exists: {environment_name}")
        except GithubException as e:
            if e.status == 404:
                # Create environment
                print(f"  📦 Creating environment: {environment_name}")
                env = repo.create_environment(environment_name)
            elif e.status == 403:
                print(f"\n❌ Permission denied: Cannot create environment")
                print(f"\n🔑 SOLUTION: Personal Access Tokens (classic) cannot create environments!")
                print(f"\nOption 1 (EASIEST): Manually create environments in GitHub UI:")
                print(f"  1. Go to: https://github.com/{repo.full_name}/settings/environments/new")
                print(f"  2. Create environment: {environment_name}")
                print(f"  3. Run this script again")
                print(f"\nOption 2: Use Fine-Grained Personal Access Token:")
                print(f"  1. Go to: https://github.com/settings/personal-access-tokens/new")
                print(f"  2. Select 'Only select repositories' → {repo.name}")
                print(f"  3. Repository permissions:")
                print(f"     - Administration: Read and write")
                print(f"     - Environments: Read and write")
                print(f"  4. Generate token and update .env file")
                print(f"\nOption 3: Install GitHub CLI:")
                print(f"  winget install GitHub.cli")
                print(f"  gh auth login")
                print(f"  python sync_github_env.py --environment all")
                return False
            else:
                raise
        
        # Set each variable
        success_count = 0
        for key, value in variables.items():
            try:
                env.create_variable(key, value)
                print(f"  ✅ {key} (created)")
                success_count += 1
            except GithubException as e:
                if e.status == 409:  # Variable exists, update it
                    try:
                        # Get the variable and update it
                        var = env.get_variable(key)
                        var.edit(value)
                        print(f"  ✅ {key} (updated)")
                        success_count += 1
                    except Exception as update_error:
                        print(f"  ❌ {key}: Failed to update - {update_error}")
                else:
                    print(f"  ❌ {key}: {e.data.get('message', str(e))}")
        
        print(f"\n✅ Synced {success_count}/{len(variables)} variables to '{environment_name}'")
        return success_count == len(variables)
        
    except GithubException as e:
        print(f"❌ GitHub API error: {e.data.get('message', str(e))}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync .env files to GitHub Environment variables"
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["production_primary", "production_secondary", "qa_primary", "qa_secondary", "all"],
        help="Environment to sync (or 'all' for all environments)"
    )
    
    args = parser.parse_args()
    
    print("🚀 GitHub Environment Sync (PyGithub)")
    print()
    
    # Get credentials
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY")
    
    if not token:
        print("❌ GITHUB_TOKEN not found in .env file")
        print("   Add to .env: GITHUB_TOKEN=ghp_xxxxx")
        sys.exit(1)
    
    if not repo_name:
        print("❌ GITHUB_REPO not found in .env file")
        print("   Add to .env: GITHUB_REPO=owner/repo")
        sys.exit(1)
    
    # Connect to GitHub
    try:
        from github import Auth
        auth = Auth.Token(token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)
        print(f"📦 Repository: {repo.full_name}")
        print()
    except GithubException as e:
        if e.status == 401:
            print(f"❌ Authentication failed: Invalid token")
            print(f"\nCheck your GITHUB_TOKEN in .env file")
            print(f"Create new token: https://github.com/settings/tokens/new")
        else:
            print(f"❌ Failed to connect to GitHub: {e.data.get('message', str(e))}")
        sys.exit(1)
    except ImportError:
        # Fallback for older PyGithub
        g = Github(token)
        repo = g.get_repo(repo_name)
        print(f"📦 Repository: {repo.full_name}")
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
        if not sync_environment(repo, env_name):
            all_success = False
    
    print(f"\n{'='*60}")
    if all_success:
        print("✅ All environments synced successfully!")
    else:
        print("⚠️  Some environments had errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
