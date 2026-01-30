#!/usr/bin/env python3
"""
Sync environment configuration from .env files to GitHub Environment variables.

Usage:
    python sync_github_env.py --environment production_primary
    python sync_github_env.py --environment all
    python sync_github_env.py  # Interactive selection
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_gh_cli():
    """Verify GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {result.stdout.split()[0]} {result.stdout.split()[2]}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI not found. Install: https://cli.github.com/")
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
        print("❌ Not authenticated. Run: gh auth login")
        sys.exit(1)


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


def create_github_environment(environment_name: str):
    """Create GitHub environment if it doesn't exist."""
    print(f"📦 Ensuring environment '{environment_name}' exists...")
    
    # GitHub CLI will create environment when setting first variable
    # No separate create command needed
    pass


def set_github_variable(environment_name: str, key: str, value: str):
    """Set a variable in GitHub environment."""
    try:
        subprocess.run(
            ["gh", "variable", "set", key, "--env", environment_name, "--body", value],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to set {key}: {e.stderr}")
        return False


def sync_environment(environment_name: str) -> bool:
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
    
    # Create environment
    create_github_environment(environment_name)
    
    # Set each variable
    success_count = 0
    for key, value in variables.items():
        if set_github_variable(environment_name, key, value):
            print(f"  ✅ {key}")
            success_count += 1
        else:
            print(f"  ❌ {key}")
    
    print(f"\n✅ Synced {success_count}/{len(variables)} variables to '{environment_name}'")
    return success_count == len(variables)


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
    
    print("🚀 GitHub Environment Sync")
    print()
    
    # Check prerequisites
    check_gh_cli()
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
        if not sync_environment(env_name):
            all_success = False
    
    print(f"\n{'='*60}")
    if all_success:
        print("✅ All environments synced successfully!")
    else:
        print("⚠️  Some environments had errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
