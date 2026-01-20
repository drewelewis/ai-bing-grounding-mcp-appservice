#!/usr/bin/env python3
"""
Check if resource group exists and confirm deployment.

This script checks if the target resource group already exists and prompts
the user to confirm if they want to deploy to an existing resource group.
"""
import os
import sys
import subprocess

def main():
    print("\033[36mChecking resource group status...\033[0m")
    print()

    env_name = os.getenv("AZURE_ENV_NAME")
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")

    if not env_name:
        print("\033[31m[ERROR] AZURE_ENV_NAME environment variable not set\033[0m")
        sys.exit(1)

    if not subscription_id:
        print("\033[31m[ERROR] AZURE_SUBSCRIPTION_ID environment variable not set\033[0m")
        sys.exit(1)

    # Construct resource group name (must match main.bicep logic)
    resource_group_name = f"rg-bing-grounding-mcp-{env_name}"

    print(f"\033[37mEnvironment: {env_name}\033[0m")
    print(f"\033[37mResource Group: {resource_group_name}\033[0m")
    print(f"\033[37mSubscription: {subscription_id}\033[0m")
    print()

    # Check if resource group exists
    try:
        result = subprocess.run(
            ["az", "group", "exists", "--name", resource_group_name, "--subscription", subscription_id],
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        
        rg_exists = result.stdout.strip().lower() == "true"
        
        if rg_exists:
            print(f"\033[33m[WARNING] Resource group '{resource_group_name}' already exists!\033[0m")
            print()
            print("\033[33mDeploying to an existing resource group will:\033[0m")
            print("\033[33m  - Update existing resources with new configurations\033[0m")
            print("\033[33m  - Potentially modify or delete resources\033[0m")
            print("\033[33m  - May cause downtime for running services\033[0m")
            print()
            
            # Prompt for confirmation
            confirmation = input("Do you want to continue deploying to the existing resource group? (yes/no): ")
            
            if confirmation.lower() != "yes":
                print()
                print("\033[31m[CANCELLED] Deployment cancelled by user\033[0m")
                print()
                print("\033[36mTo deploy to a new resource group:\033[0m")
                print("\033[36m  1. Create a new environment: azd env new <env-name>\033[0m")
                print("\033[36m  2. Or delete the existing resource group first\033[0m")
                sys.exit(1)
            
            print()
            print("\033[32m[CONFIRMED] Proceeding with deployment to existing resource group\033[0m")
        else:
            print(f"\033[32m[OK] Resource group '{resource_group_name}' does not exist - will create new\033[0m")
    except subprocess.CalledProcessError as e:
        print("\033[31m[ERROR] Failed to check resource group status\033[0m")
        print(f"\033[31mError: {e}\033[0m")
        sys.exit(1)

    print()

if __name__ == "__main__":
    main()
