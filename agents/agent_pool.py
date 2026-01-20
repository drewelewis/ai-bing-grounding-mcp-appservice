"""Agent Pool Manager - Discovers Bing agents from Azure AI Foundry project.

Multi-region architecture: 1 agent per model per region.
Regional scaling is handled by APIM geo-routing, not agent pooling.
"""
import os
import re
from typing import Dict, List
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def discover_agents_from_project(endpoint: str = None) -> Dict[str, List[dict]]:
    """
    Discover all Bing agents from Azure AI Foundry project using SDK.
    
    Args:
        endpoint: Azure AI Project endpoint. If not provided, uses AZURE_AI_PROJECT_ENDPOINT env var.
    
    Returns:
        Dict with model names as keys and lists of agent info as values
        Example: {
            "gpt-4o": [{"id": "asst_xxx1", "index": 1, "name": "agent_bing__gpt4o__1"}],
            "gpt-4.1-mini": [{"id": "asst_xxx2", "index": 1, "name": "agent_bing__gpt41_mini__1"}]
        }
    """
    endpoint = endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    
    if not endpoint:
        print("❌ AZURE_AI_PROJECT_ENDPOINT not set. Cannot discover agents.")
        return {}
    
    agents = {}
    
    try:
        client = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=endpoint
        )
        
        all_agents = client.agents.list_agents()
        
        # Pattern to match Bing agents: agent_bing__{model}__{index} or agent_bing_{model}_{index}
        # Supports both naming conventions
        bing_pattern = re.compile(r'^agent_bing_+([a-zA-Z0-9\-\.]+)_+(\d+)$')
        
        for agent in all_agents:
            match = bing_pattern.match(agent.name or "")
            if match:
                index = int(match.group(2))
                
                # Use the model from SDK (already normalized: gpt-4o, gpt-4.1-mini, etc.)
                model = agent.model
                if not model:
                    print(f"⚠️  Skipping agent {agent.name}: no model specified")
                    continue
                
                if model not in agents:
                    agents[model] = []
                
                agents[model].append({
                    "id": agent.id,
                    "index": index,
                    "name": agent.name,
                    "model": model
                })
                
                print(f"✅ Discovered: {agent.name} -> {agent.id} ({model})")
        
        # Sort by index within each model
        for model in agents:
            agents[model].sort(key=lambda x: x["index"])
        
        print(f"\n🔍 Total Bing agents discovered: {sum(len(v) for v in agents.values())}")
        
    except Exception as e:
        print(f"❌ Failed to discover agents from project: {e}")
        return {}
    
    return agents


def get_all_agent_ids() -> List[Dict[str, str]]:
    """
    Get flat list of all Bing agents with their metadata.
    
    In multi-region setup, each region has 1 agent per model.
    Regional scaling is handled by APIM, not agent pooling.
    
    Returns:
        List of dicts with agent_id, model, and index
        Example: [
            {"agent_id": "asst_xxx", "model": "gpt-4o", "index": 1, "route": "gpt4o_1"},
            {"agent_id": "asst_yyy", "model": "gpt-4.1-mini", "index": 1, "route": "gpt41mini_1"}
        ]
    """
    agents_by_model = discover_agents_from_project()
    all_agents = []
    
    for model, agents_list in agents_by_model.items():
        for agent_info in agents_list:
            # Create route-friendly name: gpt4o_1, gpt41mini_1
            route = model.replace('-', '').replace('.', '') + '_' + str(agent_info['index'])
            
            all_agents.append({
                "agent_id": agent_info["id"],
                "model": model,
                "index": agent_info["index"],
                "route": route,
                "name": agent_info.get("name", "")
            })
    
    return all_agents
