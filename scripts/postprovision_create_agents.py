#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create multiple Bing grounding agents in Azure AI Project.

This script creates agents with Bing Search grounding enabled.
It uses the Azure AI Projects SDK to programmatically create agents.

Usage:
    python scripts/create-agents.py
"""
import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure required packages are installed
try:
    from azure.ai.projects import AIProjectClient
    from azure.ai.agents.models import (
        BingGroundingToolDefinition,
        BingGroundingSearchToolParameters,
        BingGroundingSearchConfiguration
    )
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("[INFO] Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "azure-ai-projects", "azure-identity"])
    from azure.ai.projects import AIProjectClient
    from azure.ai.agents.models import (
        BingGroundingToolDefinition,
        BingGroundingSearchToolParameters,
        BingGroundingSearchConfiguration
    )
    from azure.identity import DefaultAzureCredential

# Number of agents to create
NUM_AGENTS = 10

def get_env_value(key: str) -> str:
    """Get environment variable value from OS environment or azd environment .env file.
    
    Priority: OS environment variable > .azure/{env}/.env file
    """
    # First check OS environment (for CI/CD scenarios)
    env_value = os.environ.get(key)
    if env_value:
        return env_value
    
    # Fallback: determine which azd environment we're in by checking azd's config
    env_name = None
    
    # Try to read the default environment from .azure/config.json
    import json
    config_file = Path(".azure/config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                env_name = config.get("defaultEnvironment")
        except Exception:
            pass
    
    # Fallback: check for azd's environment indicator files
    if not env_name:
        azure_dir = Path(".azure")
        if azure_dir.exists():
            # Look for .env files in subdirectories to find current environment
            for env_dir in azure_dir.iterdir():
                if env_dir.is_dir() and (env_dir / ".env").exists():
                    # Check if this env has the key we need (like AZURE_AI_PROJECT_ENDPOINT)
                    test_file = env_dir / ".env"
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'AZURE_AI_PROJECT_ENDPOINT' in content:
                            env_name = env_dir.name
                            break
    
    if not env_name:
        env_name = "dev"  # Fallback default
    
    # Read from .azure/{env}/.env
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

def set_env_value(key: str, value: str):
    """Set environment variable in current azd environment's .env file."""
    # Detect current environment the same way as get_env_value
    env_name = None
    
    # Try to read the default environment from .azure/config.json
    import json
    config_file = Path(".azure/config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                env_name = config.get("defaultEnvironment")
        except Exception:
            pass
    
    # Fallback: check for azd's environment indicator files
    if not env_name:
        azure_dir = Path(".azure")
        if azure_dir.exists():
            for env_dir in azure_dir.iterdir():
                if env_dir.is_dir() and (env_dir / ".env").exists():
                    test_file = env_dir / ".env"
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'AZURE_AI_PROJECT_ENDPOINT' in content:
                            env_name = env_dir.name
                            break
    
    if not env_name:
        env_name = "dev"
    
    env_file = Path(f".azure/{env_name}/.env")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    
    lines = []
    found = False
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Update or add the key
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('#'):
            if '=' in line:
                k, _ = line.split('=', 1)
                if k.strip() == key:
                    lines[i] = f'{key}="{value}"\n'
                    found = True
                    break
    
    if not found:
        lines.append(f'{key}="{value}"\n')
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def load_agents_config() -> dict:
    """Load agent pool configuration from agents.config.json."""
    import json
    config_paths = [
        Path("agents.config.json"),
        Path("./agents.config.json"),
        Path(__file__).parent.parent / "agents.config.json"
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    print("⚠️ Warning: agents.config.json not found, using defaults")
    return {}

def main():
    """Create Bing grounding agents."""
    print("🤖 Creating Bing Grounding Agent Pools...")
    print()
    
    # Check if we're in CI/CD mode (environment variables set directly)
    is_ci_mode = os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
    
    # Get AI Project endpoint - check OS env first, then .azure/ folder
    project_endpoint = get_env_value("AZURE_AI_PROJECT_ENDPOINT")
    
    if not project_endpoint:
        print("❌ Error: AZURE_AI_PROJECT_ENDPOINT not found")
        print("   In CI/CD: Set AZURE_AI_PROJECT_ENDPOINT environment variable")
        print("   Locally: Run 'azd provision' first to create the AI Project.")
        sys.exit(1)
    
    # For CI/CD, we may not have resource ID - that's OK for agent creation
    project_resource_id = get_env_value("AZURE_AI_PROJECT_RESOURCE_ID")
    if not project_resource_id and not is_ci_mode:
        print("⚠️ Warning: AZURE_AI_PROJECT_RESOURCE_ID not found (optional for agent creation)")
    
    # Bing connection ID - optional for now (connection can be created later)
    bing_connection_id = get_env_value("AZURE_BING_CONNECTION_ID")
    
    # Load configuration from agents.config.json
    agents_config = load_agents_config()
    models_config = agents_config.get("models", {})
    
    # Model configurations - read from agents.config.json
    # Map config keys to model IDs
    model_mapping = {
        "gpt4o": {"name": "gpt-4o", "key": "GPT4O"},
        "gpt41mini": {"name": "gpt-4.1-mini", "key": "GPT41_MINI"},
        "gpt4": {"name": "gpt-4", "key": "GPT4"},
        "gpt35turbo": {"name": "gpt-35-turbo", "key": "GPT35_TURBO"},
    }
    
    model_configs = []
    for config_key, mapping in model_mapping.items():
        model_info = models_config.get(config_key, {})
        if model_info.get("enabled", False):
            pool_size = model_info.get("agentPoolSize", 0)
            if pool_size > 0:
                model_configs.append({
                    "name": model_info.get("modelId", mapping["name"]),
                    "key": mapping["key"],
                    "pool_size": pool_size
                })
    
    # Fallback to hardcoded defaults if no config found
    if not model_configs:
        print("⚠️ No models enabled in config, using defaults")
        model_configs = [
            {"name": "gpt-4o", "key": "GPT4O", "pool_size": 1},
            {"name": "gpt-4.1-mini", "key": "GPT41_MINI", "pool_size": 1},
        ]
    
    total_agents = sum(c["pool_size"] for c in model_configs)
    
    print(f"?? AI Project Endpoint: {project_endpoint}")
    print(f"?? Agent Pool Configuration:")
    for config in model_configs:
        print(f"   {config['name']}: {config['pool_size']} agents")
    print(f"   Total: {total_agents} agents")
    print()
    
    try:
        # Initialize AI Project client using HTTPS endpoint (for Foundry projects with GA SDK v1.0.0)
        credential = DefaultAzureCredential()
        
        # Determine the project endpoint to use
        # CI/CD: Use the endpoint directly (cognitiveservices.azure.com format)
        # Local: Construct from foundry_name and project_name (services.ai.azure.com format)
        
        # Always get foundry_name and project_name (needed for connection ID construction later)
        foundry_name = get_env_value("AZURE_FOUNDRY_NAME")
        project_name = get_env_value("AZURE_AI_PROJECT_NAME")
        
        # In CI mode, try to extract from the endpoint URL if not explicitly set
        if not foundry_name and project_endpoint:
            # Extract from endpoint like: https://ai-foundry-52hltr3kdvkvo.cognitiveservices.azure.com/
            import re
            match = re.search(r'https://([^.]+)\.cognitiveservices\.azure\.com', project_endpoint)
            if match:
                foundry_name = match.group(1)
                print(f"📍 Extracted foundry name from endpoint: {foundry_name}")
        
        # For Azure AI Foundry with cognitiveservices.azure.com endpoints,
        # the AIProjectClient needs the project context in the endpoint
        if project_endpoint.endswith('.cognitiveservices.azure.com/') or '.cognitiveservices.azure.com' in project_endpoint:
            # For cognitiveservices endpoints, we need to append the project path
            # Format: https://{account}.cognitiveservices.azure.com/api/projects/{project}
            base_endpoint = project_endpoint.rstrip('/')
            if project_name:
                api_endpoint = f"{base_endpoint}/api/projects/{project_name}"
                print(f"📍 Using project-scoped endpoint: {api_endpoint}")
            else:
                # Fall back to base endpoint (may fail for agents)
                api_endpoint = base_endpoint
                print(f"📍 Using AI Services endpoint (no project): {api_endpoint}")
        elif foundry_name and project_name:
            # Format: https://{foundry}.services.ai.azure.com/api/projects/{project}
            api_endpoint = f"https://{foundry_name}.services.ai.azure.com/api/projects/{project_name}"
            print(f"📍 Using constructed project endpoint: {api_endpoint}")
        else:
            # Fall back to using the endpoint as-is
            api_endpoint = project_endpoint.rstrip('/')
            print(f"📍 Using provided endpoint: {api_endpoint}")
        
        print()
        
        project_client = AIProjectClient(
            endpoint=api_endpoint,
            credential=credential
        )
        
        # Delete all existing agents with our naming pattern to avoid duplicates
        print("?? Cleaning up existing agents...")
        try:
            existing_agents = project_client.agents.list_agents()
            deleted_count = 0
            for agent in existing_agents:
                if agent.name and agent.name.startswith("agent_bing_"):
                    print(f"  Deleting old agent: {agent.name} ({agent.id})")
                    project_client.agents.delete_agent(agent.id)
                    deleted_count += 1
            if deleted_count > 0:
                print(f"?? Deleted {deleted_count} old agent(s)")
            else:
                print("  No existing agents to delete")
        except Exception as e:
            print(f"  Warning: Could not clean up agents: {e}")
        print()
        
        agent_ids = []
        agent_counter = 1
        
        # Create agents for each model pool
        for config in model_configs:
            model_name = config["name"]
            model_key = config["key"]
            pool_size = config["pool_size"]
            
            if pool_size == 0:
                continue
            
            print(f"\n?? Creating {model_name} pool ({pool_size} agents)...")
            
            for i in range(1, pool_size + 1):
                # Naming convention: agent_bing_{model_key}_{index}
                # Examples: agent_bing_gpt4o_1, agent_bing_gpt4_turbo_2, agent_bing_gpt35_turbo_1
                agent_name = f"agent_bing_{model_key.lower()}_{i}"
                
                # Traffic weight for blue/green deployments
                # Agent 1 = 100% (production), Agent 2 = 0% (standby)
                # Use update_agent() to adjust weights for canary/cutover
                weight = "100" if i == 1 else "0"
                
                print(f"  [{agent_counter}] Creating {agent_name} (weight: {weight}%)...", end=" ")
                
                try:
                    # Get Bing resource ID from preprovision selection
                    bing_resource_id = get_env_value("BING_GROUNDING_RESOURCE_ID")
                    if not bing_resource_id:
                        print()
                        print()
                        print("[ERROR] BING_GROUNDING_RESOURCE_ID not found!")
                        print("  This should have been set during preprovision.")
                        print("  Run 'azd up' again to select a Bing resource.")
                        return 1
                    
                    # Validate foundry_name and project_name are available
                    if not foundry_name:
                        print()
                        print()
                        print("[ERROR] AZURE_FOUNDRY_NAME not found and could not be extracted from endpoint!")
                        print("  Please ensure AZURE_FOUNDRY_NAME is set in your environment.")
                        return 1
                    
                    if not project_name:
                        print()
                        print()
                        print("[ERROR] AZURE_AI_PROJECT_NAME not found!")
                        print("  Please ensure AZURE_AI_PROJECT_NAME is set in your environment.")
                        return 1
                    
                    # Construct connection ID: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{foundry}/projects/{project}/connections/default-bing
                    subscription_id = get_env_value("AZURE_SUBSCRIPTION_ID")
                    resource_group = get_env_value("AZURE_RESOURCE_GROUP")
                    bing_connection_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{foundry_name}/projects/{project_name}/connections/default-bing"
                    
                    # Create Bing grounding tool configuration
                    bing_tool = BingGroundingToolDefinition(
                        bing_grounding=BingGroundingSearchToolParameters(
                            search_configurations=[
                                BingGroundingSearchConfiguration(
                                    connection_id=bing_connection_id
                                )
                            ]
                        )
                    )
                    
                    # Create agent using AgentsClient (creates modern agents, not classic)
                    agent = project_client.agents.create_agent(
                        model=model_name,
                        name=agent_name,
                        instructions="""You are a web search assistant with ONE RULE: Never answer without searching first.

For every query, you MUST:
- Call Bing Search tool BEFORE answering (mandatory step)
- Base your entire response on search results only
- Include citations [1], [2] for all facts

FORBIDDEN: Answering from memory or training data. Search is required for ALL queries.""",
                        tools=[bing_tool],
                        description="Agent with Bing grounding for real-time web search",
                        metadata={"weight": weight}
                    )
                    
                    agent_ids.append({"id": agent.id, "name": agent_name, "model": model_name, "weight": weight})
                    print(f"✓ {agent.id}")
                    
                    # Store in environment with consistent naming
                    # AZURE_AI_AGENT_GPT4O_1, AZURE_AI_AGENT_GPT4_TURBO_2, etc.
                    env_key = f"AZURE_AI_AGENT_{model_key}_{i}"
                    set_env_value(env_key, agent.id)
                    
                    agent_counter += 1
                    
                except Exception as e:
                    print(f"? Failed: {str(e)}")
                    # Print more details for debugging
                    if hasattr(e, 'response'):
                        print(f"   Response: {e.response}")
                    if hasattr(e, 'status_code'):
                        print(f"   Status: {e.status_code}")
                    continue
        
        print()
        print(f"\n? Successfully created {len(agent_ids)}/{total_agents} agents")
        print()
        
        if agent_ids:
            # Set the first agent as the default
            set_env_value("AZURE_AI_AGENT_ID", agent_ids[0]["id"])
            print(f"?? Default agent: {agent_ids[0]['name']} ({agent_ids[0]['id']})")
            print()
            
            # Detect which env we're in for display (use same logic as get_env_value)
            import json
            env_name = "unknown"
            config_file = Path(".azure/config.json")
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        env_name = config.get("defaultEnvironment", "unknown")
                except Exception:
                    # Fallback to directory scanning
                    azure_dir = Path(".azure")
                    for env_dir in azure_dir.iterdir():
                        if env_dir.is_dir() and (env_dir / ".env").exists():
                            with open(env_dir / ".env", 'r') as f:
                                if 'AZURE_AI_PROJECT_ENDPOINT' in f.read():
                                    env_name = env_dir.name
                                    break
            
            print(f"Agent IDs saved to .azure/{env_name}/.env:")
            
            # Group by model for cleaner output
            for config in model_configs:
                model_agents = [a for a in agent_ids if a["model"] == config["name"]]
                if model_agents:
                    print(f"\n  {config['name']}:")
                    for agent in model_agents:
                        env_key = f"AZURE_AI_AGENT_{config['key']}_{agent['name'].split('_')[-1]}"
                        print(f"    {env_key}={agent['id']}")
            
            print()
            print("? Agent pools are ready to use!")
        else:
            print("??  No agents were created successfully")
            sys.exit(1)
            
    except Exception as e:
        print(f"? Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
