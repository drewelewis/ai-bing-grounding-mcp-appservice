"""Test what endpoint the agent creation script is using"""
import os
import re

# Simulate what the workflow sets
project_endpoint = "https://ai-foundry-52hltr3kdvkvo.cognitiveservices.azure.com/"
foundry_name = "ai-foundry-52hltr3kdvkvo"
project_name = "ai-proj-52hltr3kdvkvo"

print("=== Agent Creation Script Logic ===")
print(f"Input endpoint: {project_endpoint}")
print(f"Foundry name: {foundry_name}")
print(f"Project name: {project_name}")
print()

# This is what the script does:
if project_endpoint.endswith('.cognitiveservices.azure.com/') or '.cognitiveservices.azure.com' in project_endpoint:
    base_endpoint = project_endpoint.rstrip('/')
    if project_name:
        api_endpoint = f"{base_endpoint}/api/projects/{project_name}"
        print(f"✅ Project-scoped endpoint: {api_endpoint}")
    else:
        api_endpoint = base_endpoint
        print(f"⚠️ AI Services endpoint (no project): {api_endpoint}")
else:
    api_endpoint = project_endpoint.rstrip('/')
    print(f"Using provided endpoint: {api_endpoint}")

print()
print("=== App's Endpoint ===")
app_endpoint = project_endpoint  # App uses it directly
print(f"App uses: {app_endpoint}")

print()
print("=== Issue? ===")
if api_endpoint != app_endpoint:
    print(f"❌ MISMATCH!")
    print(f"   Agent script uses: {api_endpoint}")
    print(f"   App uses: {app_endpoint}")
    print(f"   Agents created in one project, app looks in another!")
else:
    print("✅ Both use same endpoint")
