#!/usr/bin/env python3
"""
Register required Azure resource providers for Bing Grounding deployment.

This script registers the Microsoft.Bing resource provider which is required
for deploying Grounding with Bing Search resources.
"""
import sys
import subprocess

def main():
    print("\033[36mRegistering Azure Resource Providers...\033[0m")
    print()

    # Register Microsoft.Bing provider
    print("Registering Microsoft.Bing resource provider...", end="", flush=True)
    try:
        result = subprocess.run(
            ["az", "provider", "show", "--namespace", "Microsoft.Bing", "--query", "registrationState", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=False,
            shell=True
        )
        
        provider_state = result.stdout.strip()
        
        if provider_state == "Registered":
            print(" \033[32m[OK] Already registered\033[0m")
        else:
            print()
            print("   \033[33mRegistering (this may take a few minutes)...\033[0m")
            result = subprocess.run(
                ["az", "provider", "register", "--namespace", "Microsoft.Bing", "--wait"],
                check=True,
                shell=True
            )
            print("   \033[32m[OK] Successfully registered Microsoft.Bing\033[0m")
    except subprocess.CalledProcessError as e:
        print(" \033[31m[ERROR] Failed to register Microsoft.Bing\033[0m")
        print(f"\033[31mError: {e}\033[0m")
        sys.exit(1)
    except Exception as e:
        print(" \033[31m[ERROR] Error checking provider status\033[0m")
        print(f"\033[31mError: {e}\033[0m")
        sys.exit(1)

    print()
    print("\033[32m[SUCCESS] All resource providers registered successfully!\033[0m")

if __name__ == "__main__":
    main()
