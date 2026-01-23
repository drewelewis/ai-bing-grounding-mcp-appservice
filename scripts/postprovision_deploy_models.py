#!/usr/bin/env python3
"""
Deploy AI Foundry model deployments based on agents.config.json.

This script reads the models section from agents.config.json and ensures
the required model deployments exist in Azure AI Foundry.

Usage:
    python scripts/postprovision_deploy_models.py
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_env_value(key: str) -> str:
    """Get environment variable from OS env or .azure/{env}/.env"""
    # First check OS environment (for CI/CD)
    value = os.environ.get(key)
    if value:
        return value
    
    # Fallback to .azure/{env}/.env
    config_file = Path(".azure/config.json")
    env_name = "prod"
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                env_name = config.get("defaultEnvironment", "prod")
        except Exception:
            pass
    
    env_file = Path(f".azure/{env_name}/.env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        if k.strip() == key:
                            return v.strip().strip('"')
    return ""


def load_agents_config() -> dict:
    """Load configuration from agents.config.json."""
    config_paths = [
        Path("agents.config.json"),
        Path("./agents.config.json"),
        Path(__file__).parent.parent / "agents.config.json"
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    print("⚠️ Warning: agents.config.json not found")
    return {}


def run_command(cmd, check=True):
    """Run a command and return success, stdout, stderr."""
    try:
        result = subprocess.run(
            ' '.join(cmd) if isinstance(cmd, list) else cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def main():
    print("=" * 80)
    print("Deploying AI Foundry Model Deployments")
    print("=" * 80)
    print()
    
    # Get configuration
    foundry_name = get_env_value("AZURE_FOUNDRY_NAME")
    resource_group = get_env_value("AZURE_RESOURCE_GROUP")
    
    if not foundry_name or not resource_group:
        print("❌ ERROR: Missing configuration.")
        print(f"   AZURE_FOUNDRY_NAME: {foundry_name}")
        print(f"   AZURE_RESOURCE_GROUP: {resource_group}")
        return 1
    
    print(f"📍 Foundry: {foundry_name}")
    print(f"📍 Resource Group: {resource_group}")
    print()
    
    # Load models from agents.config.json
    config = load_agents_config()
    models_config = config.get("models", {})
    
    if not models_config:
        print("⚠️ No models defined in agents.config.json")
        return 0
    
    # Get list of models used by enabled agents
    agents = config.get("agents", [])
    required_models = set()
    for agent in agents:
        if agent.get("enabled", True):
            required_models.add(agent.get("model"))
    
    print(f"📋 Models required by enabled agents: {', '.join(required_models)}")
    print()
    
    # Check existing deployments
    print("🔍 Checking existing deployments...")
    success, stdout, stderr = run_command([
        "az", "cognitiveservices", "account", "deployment", "list",
        "--name", foundry_name,
        "--resource-group", resource_group,
        "-o", "json"
    ])
    
    existing_deployments = set()
    if success and stdout.strip():
        try:
            deployments = json.loads(stdout)
            existing_deployments = {d["name"] for d in deployments}
            if existing_deployments:
                print(f"   Found: {', '.join(existing_deployments)}")
            else:
                print("   None found")
        except Exception as e:
            print(f"   Could not parse: {e}")
    print()
    
    # Deploy models
    deployed_count = 0
    skipped_count = 0
    failed_count = 0
    
    for model_name, model_cfg in models_config.items():
        # Skip if model is not enabled
        if not model_cfg.get("enabled", False):
            print(f"⏭️ {model_name} (disabled in config)")
            skipped_count += 1
            continue
        
        # Skip if model is not required by any agent
        if model_name not in required_models:
            print(f"⏭️ {model_name} (not used by any agent)")
            skipped_count += 1
            continue
        
        # Skip if already deployed
        if model_name in existing_deployments:
            print(f"✅ {model_name} (already deployed)")
            continue
        
        # Deploy the model
        print(f"🚀 Deploying {model_name}...", end=" ")
        
        sku = model_cfg.get("sku", "GlobalStandard")
        capacity = model_cfg.get("capacity", 10)
        version = model_cfg.get("version", "")
        
        cmd = [
            "az", "cognitiveservices", "account", "deployment", "create",
            "--name", foundry_name,
            "--resource-group", resource_group,
            "--deployment-name", model_name,
            "--model-name", model_name,
            "--model-format", "OpenAI",
            "--sku-capacity", str(capacity),
            "--sku-name", sku
        ]
        
        if version:
            cmd.extend(["--model-version", version])
        
        success, stdout, stderr = run_command(cmd, check=False)
        
        if success:
            print("✅ SUCCESS")
            deployed_count += 1
        else:
            print("❌ FAILED")
            if "already exists" in stderr.lower() or "conflict" in stderr.lower():
                print(f"   (Model may already exist with different name)")
            else:
                print(f"   Error: {stderr[:300]}")
            failed_count += 1
    
    print()
    print("=" * 80)
    print(f"📊 Deployment Summary:")
    print(f"   ✅ Deployed: {deployed_count}")
    print(f"   ⏭️ Skipped: {skipped_count}")
    print(f"   ❌ Failed: {failed_count}")
    print("=" * 80)
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
