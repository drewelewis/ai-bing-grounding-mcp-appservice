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
    """Get environment variable value from current azd environment .env file."""
    # First, determine which environment we're in by checking azd's config
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

def main():
    """Create Bing grounding agents."""
    print("?? Creating Bing Grounding Agent Pools...")
    print()
    
    # Get AI Project endpoint and resource ID from .azure/{env}/.env file
    project_endpoint = get_env_value("AZURE_AI_PROJECT_ENDPOINT")
    project_resource_id = get_env_value("AZURE_AI_PROJECT_RESOURCE_ID")
    
    if not project_endpoint:
        print("? Error: AZURE_AI_PROJECT_ENDPOINT not found in .azure/ folder")
        print("   Run 'azd provision' first to create the AI Project.")
        sys.exit(1)
    
    if not project_resource_id:
        print("? Error: AZURE_AI_PROJECT_RESOURCE_ID not found in .azure/ folder")
        print("   Run 'azd provision' first to create the AI Project.")
        sys.exit(1)
    
    # Bing connection ID - optional for now (connection can be created later)
    # For beta10 SDK with hub-based projects, Bing tool may work without explicit connection ID
    bing_connection_id = get_env_value("AZURE_BING_CONNECTION_ID")
    
    # Model configurations (ONLY officially supported models for Bing grounding)
    # GPT-4o, GPT-4, GPT-3.5-Turbo are the ONLY verified models per Microsoft docs
    # GPT-4.1 REMOVED - not a real model
    # GPT-5 series REMOVED - does not support Bing grounding tool (uses Responses API only)
    # o-series REMOVED - reasoning models use different API
    # NOTE: pool_size_env must match camelCase parameter names in .azure/{env}/.env
    # 
    # MULTI-REGION NOTE: Use 1 agent per model per region.
    # Regional APIM routing provides throughput scaling, not agent pooling.
    model_configs = [
        # GPT-4o series - recommended: 1 per region
        {"name": "gpt-4o", "key": "GPT4O", "pool_size_env": "agentPoolSizeGpt4o", "default_size": 1},
        
        # GPT-4.1-mini - recommended: 1 per region  
        {"name": "gpt-4.1-mini", "key": "GPT41_MINI", "pool_size_env": "agentPoolSizeGpt41Mini", "default_size": 1},
        
        # GPT-4 series - optional
        {"name": "gpt-4", "key": "GPT4", "pool_size_env": "agentPoolSizeGpt4", "default_size": 0},
        {"name": "gpt-4-turbo", "key": "GPT4_TURBO", "pool_size_env": "agentPoolSizeGpt4Turbo", "default_size": 0},
        
        # GPT-3.5 series - optional
        {"name": "gpt-35-turbo", "key": "GPT35_TURBO", "pool_size_env": "agentPoolSizeGpt35Turbo", "default_size": 0},
    ]
    
    # Read pool sizes from environment
    for config in model_configs:
        pool_size_str = get_env_value(config["pool_size_env"])
        try:
            config["pool_size"] = int(pool_size_str) if pool_size_str else config["default_size"]
        except ValueError:
            config["pool_size"] = config["default_size"]
    
    total_agents = sum(c["pool_size"] for c in model_configs)
    
    print(f"?? AI Project Endpoint: {project_endpoint}")
    print(f"?? Agent Pool Configuration:")
    for config in model_configs:
        print(f"   {config['name']}: {config['pool_size']} agents")
    print(f"   Total: {total_agents} agents")
    print()
    
    try:
        # Initialize AI Project client using HTTPS endpoint (for Foundry projects with GA SDK v1.0.0)
        # For GA SDK, we need to construct the full project endpoint
        credential = DefaultAzureCredential()
        
        # For GA SDK v1.0.0, use the project-specific AI Foundry API endpoint
        # Get required parameters for AIProjectClient v1.0.0+
        foundry_name = get_env_value("AZURE_FOUNDRY_NAME")
        project_name = get_env_value("AZURE_AI_PROJECT_NAME")
        
        # Format: https://{foundry}.services.ai.azure.com/api/projects/{project}
        project_endpoint = f"https://{foundry_name}.services.ai.azure.com/api/projects/{project_name}"
        
        print(f"?? Using project endpoint: {project_endpoint}")
        print()
        
        project_client = AIProjectClient(
            endpoint=project_endpoint,
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
                print(f"  [{agent_counter}] Creating {agent_name}...", end=" ")
                
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
                        description="Agent with Bing grounding for real-time web search"
                    )
                    
                    agent_ids.append({"id": agent.id, "name": agent_name, "model": model_name})
                    print(f"? {agent.id}")
                    
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
