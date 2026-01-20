#!/usr/bin/env python3
"""
Post-provision script to create MCP server in APIM.

This script runs after infrastructure provisioning to automatically
expose the REST API as an MCP server in Azure API Management.

Note: This uses Azure REST API directly since MCP server resources
may not yet be available in Bicep/ARM templates.
"""

import os
import sys
import json
import subprocess
from typing import Dict, Optional

def run_command(cmd: list[str]) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def get_azd_env_value(key: str) -> Optional[str]:
    """Get environment variable value from azd."""
    success, output = run_command(["azd", "env", "get-values"])
    if not success:
        return None
    
    for line in output.split('\n'):
        if line.startswith(f"{key}="):
            return line.split('=', 1)[1].strip().strip('"')
    return None

def get_access_token() -> Optional[str]:
    """Get Azure access token for management API."""
    try:
        success, output = run_command([
            "az", "account", "get-access-token",
            "--resource", "https://management.azure.com/",
            "--query", "accessToken",
            "-o", "tsv"
        ])
        if success and output.strip():
            return output.strip()
    except Exception as e:
        print(f"   Exception: {e}")
    return None

def create_mcp_server(
    subscription_id: str,
    resource_group: str,
    apim_name: str,
    api_name: str,
    access_token: str
) -> bool:
    """
    Create MCP server in APIM using Azure REST API.
    
    Note: This function attempts to use the Azure Management REST API.
    If the MCP server resource type is not yet available, this will fail
    and manual configuration will be required.
    """
    
    # MCP server configuration
    mcp_server_name = f"{api_name}-mcp"
    
    # Construct Azure Management REST API URL
    # Note: Adjust this URL based on actual Azure MCP server API when available
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}/"
        f"resourceGroups/{resource_group}/"
        f"providers/Microsoft.ApiManagement/service/{apim_name}/"
        f"mcpServers/{mcp_server_name}?api-version=2023-05-01-preview"
    )
    
    # MCP server payload
    payload = {
        "properties": {
            "displayName": "Bing Grounding MCP Server",
            "description": "MCP server for Bing Grounding API - exposes API operations as MCP tools",
            "sourceType": "RestApi",
            "sourceApiId": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}",
            "path": f"{api_name}-mcp"
        }
    }
    
    # Try using Azure CLI to make REST API call
    payload_json = json.dumps(payload)
    
    success, output = run_command([
        "az", "rest",
        "--method", "PUT",
        "--url", url,
        "--body", payload_json,
        "--headers", f"Authorization=Bearer {access_token}",
        "Content-Type=application/json"
    ])
    
    return success

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("Post-Deploy: MCP Server Configuration")
    print("=" * 80)
    print("\nThis script provides configuration details for setting up the MCP server")
    print("in Azure API Management Portal.")
    
    # Get environment values from azd
    print("\n[1/6] Getting environment configuration...")
    subscription_id = get_azd_env_value("AZURE_SUBSCRIPTION_ID")
    resource_group = get_azd_env_value("AZURE_RESOURCE_GROUP")
    apim_name = get_azd_env_value("AZURE_APIM_NAME")
    
    if not all([subscription_id, resource_group, apim_name]):
        print("❌ ERROR: Missing required environment variables")
        print(f"   AZURE_SUBSCRIPTION_ID: {subscription_id or 'NOT SET'}")
        print(f"   AZURE_RESOURCE_GROUP: {resource_group or 'NOT SET'}")
        print(f"   AZURE_APIM_NAME: {apim_name or 'NOT SET'}")
        return 1
    
    print(f"✅ Subscription: {subscription_id}")
    print(f"✅ Resource Group: {resource_group}")
    print(f"✅ APIM Service: {apim_name}")
    
    # Get access token
    print("\n[2/6] Getting Azure access token...")
    access_token = get_access_token()
    if not access_token:
        print("⚠️  WARNING: Could not get Azure access token")
        print("   Automatic MCP server creation will be skipped")
        print("   (This is normal - manual setup instructions will be provided)")
    else:
        print("✅ Access token obtained")
    
    # Attempt to create MCP server
    print("\n[3/6] Checking MCP server automation...")
    print("   API Name: bing-grounding-api")
    print("   MCP Server Name: bing-grounding-api-mcp")
    
    success = False
    if access_token:
        success = create_mcp_server(
            subscription_id=subscription_id,
            resource_group=resource_group,
            apim_name=apim_name,
            api_name="bing-grounding-api",
            access_token=access_token
        )
    else:
        print("   Skipping automatic creation (no access token)")
    
    if success:
        print("✅ MCP server created successfully!")
        print(f"\n📌 MCP Server URL: https://{apim_name}.azure-api.net/bing-grounding-api-mcp/mcp")
    else:
        print("⚠️  WARNING: Automatic MCP server creation may not be supported yet")
        print("\n📋 MANUAL CONFIGURATION REQUIRED:")
        print("\n   Please complete these steps in Azure Portal:")
        print(f"\n   1. Navigate to: https://portal.azure.com/#@/resource/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/overview")
        print("   2. In left menu: APIs > MCP Servers")
        print("   3. Click: + Create MCP server")
        print("   4. Select: Expose an API as an MCP server")
        print("   5. Backend MCP server:")
        print("      - API: bing-grounding-api")
        print("      - Operations: Select all operations")
        print("   6. New MCP server:")
        print("      - Name: bing-grounding-api-mcp")
        print("      - Description: MCP server for Bing Grounding with citations")
        print("   7. Click: Create")
        print(f"\n   MCP Server URL will be: https://{apim_name}.azure-api.net/bing-grounding-api-mcp/mcp")
        print("\n   See docs/APIM_MCP_SERVER.md for detailed instructions")
    
    print("\n[4/6] Getting APIM subscription key...")
    success, output = run_command([
        "az", "apim", "subscription", "list",
        "--resource-group", resource_group,
        "--service-name", apim_name,
        "--query", "[0].primaryKey",
        "-o", "tsv"
    ])
    
    if success and output.strip():
        subscription_key = output.strip()
        print("✅ APIM subscription key obtained")
        
        print("\n[5/6] Testing APIM health endpoint...")
        apim_gateway_url = get_azd_env_value("AZURE_APIM_GATEWAY_URL")
        if apim_gateway_url:
            # Test health endpoint
            import urllib.request
            import urllib.error
            
            try:
                url = f"{apim_gateway_url}/bing-grounding/health"
                req = urllib.request.Request(url)
                req.add_header("Ocp-Apim-Subscription-Key", subscription_key)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        print("✅ APIM health check passed")
                    else:
                        print(f"⚠️  Health check returned status: {response.status}")
            except Exception as e:
                print(f"⚠️  Health check failed: {e}")
                print("   This is normal if Container Apps are still starting")
    else:
        print("⚠️  Could not retrieve APIM subscription key")
        subscription_key = None
    
    print("\n[6/6] Configuration summary")
    print("=" * 80)
    
    # Save configuration for test.py
    config_info = {
        "APIM_GATEWAY_URL": get_azd_env_value("AZURE_APIM_GATEWAY_URL"),
        "APIM_NAME": apim_name,
        "APIM_MCP_SERVER_URL": f"https://{apim_name}.azure-api.net/bing-grounding-api-mcp/mcp",
        "APIM_SUBSCRIPTION_KEY": subscription_key if subscription_key else "*** RUN: az apim subscription list ... ***",
        "AZURE_OPENAI_ENDPOINT": get_azd_env_value("AZURE_AI_PROJECT_ENDPOINT"),
        "AZURE_OPENAI_DEPLOYMENT": get_azd_env_value("AZURE_OPENAI_MODEL_GPT4O")
    }
    
    print("\n📝 Environment variables for test.py (.env file):")
    print("-" * 80)
    print(f"AZURE_OPENAI_ENDPOINT={config_info['AZURE_OPENAI_ENDPOINT']}")
    print(f"AZURE_OPENAI_API_KEY=*** GET FROM AZURE PORTAL ***")
    print(f"AZURE_OPENAI_DEPLOYMENT_NAME={config_info['AZURE_OPENAI_DEPLOYMENT']}")
    print(f"APIM_MCP_SERVER_URL={config_info['APIM_MCP_SERVER_URL']}")
    print(f"APIM_SUBSCRIPTION_KEY={config_info['APIM_SUBSCRIPTION_KEY']}")
    print("-" * 80)
    
    print("\n✅ Post-deploy configuration information displayed!")
    print("\n📚 Next steps:")
    print("   1. Complete manual MCP server setup (see instructions above)")
    print("   2. Copy .env.test.sample to .env")
    print("   3. Update .env with values shown above")
    print("   4. Run: python test.py")
    print(f"\n📖 Documentation: docs/APIM_MCP_SERVER.md")
    print(f"📖 Testing Guide: docs/TESTING.md")
    print("")
    
    return 0  # Always succeed - don't fail deployment

if __name__ == "__main__":
    sys.exit(main())
