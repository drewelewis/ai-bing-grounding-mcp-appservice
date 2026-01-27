import json
import os
import random
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.agent_pool import get_all_agent_ids
from agents.bing_grounding import BingGroundingAgent
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load .env file before reading environment variables
load_dotenv()

# Discover all agents on startup
AGENTS = {}
PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
# REGION_NAME is auto-set by Azure App Service (e.g., "East US")
# Falls back to "local" for local development
AZURE_REGION = os.getenv("REGION_NAME") or os.getenv("AZURE_REGION", "local")

# Agent refresh interval (seconds)
AGENT_REFRESH_INTERVAL = int(os.getenv("AGENT_REFRESH_INTERVAL", "300"))  # Default: 5 minutes


async def periodic_agent_refresh():
    """Background task to refresh agents periodically"""
    while True:
        await asyncio.sleep(AGENT_REFRESH_INTERVAL)
        try:
            print(f"🔄 Periodic agent refresh (every {AGENT_REFRESH_INTERVAL}s)...")
            load_agents()
        except Exception as e:
            print(f"⚠️ Periodic refresh failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    # Startup: load agents and start background refresh
    load_agents()
    refresh_task = asyncio.create_task(periodic_agent_refresh())
    print(f"⏰ Background refresh scheduled every {AGENT_REFRESH_INTERVAL} seconds")
    
    yield  # App is running
    
    # Shutdown: cancel background task
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        print("🛑 Background refresh stopped")


app = FastAPI(
    title="Bing Grounding API",
    description="API wrapper for Azure AI Agent with Bing grounding capabilities - Multiple agent instances",
    version="2.0.0",
    lifespan=lifespan
)

# Request model
class QueryRequest(BaseModel):
    query: str

# Weight update model
class WeightUpdate(BaseModel):
    weight: int  # 0-100


def load_agents():
    """Load/reload all agents from Azure AI Foundry project"""
    global AGENTS
    
    if not PROJECT_ENDPOINT:
        print("⚠️  Warning: AZURE_AI_PROJECT_ENDPOINT not set")
        return
    
    all_agents = get_all_agent_ids()
    
    if not all_agents:
        print("⚠️  Warning: No Bing agents found in project")
        return
    
    # Clear existing agents if reloading
    new_agents = {}
    
    # Create agent instance for each discovered agent
    for agent_info in all_agents:
        route = agent_info["route"]
        agent_id = agent_info["agent_id"]
        weight = agent_info.get("weight", 100)
        
        try:
            agent_instance = BingGroundingAgent(endpoint=PROJECT_ENDPOINT, agent_id=agent_id)
            
            new_agents[route] = {
                "agent_id": agent_id,
                "model": agent_info["model"],
                "index": agent_info["index"],
                "weight": weight,
                "instance": agent_instance
            }
            
            print(f"✅ Registered agent: {route} -> {agent_id} ({agent_info['model']}, weight: {weight}%)")
        except Exception as e:
            print(f"⚠️  Failed to initialize agent {route}: {e}")
    
    AGENTS = new_agents
    print(f"\n🚀 Total agents available: {len(AGENTS)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns 200 OK if the service is running.
    Shows per-model status for multi-region routing decisions.
    """
    # Calculate per-model status
    models_status = {}
    for route, info in AGENTS.items():
        model = info["model"]
        weight = info.get("weight", 100)
        
        if model not in models_status:
            models_status[model] = {
                "agents": 0,
                "active_agents": 0,
                "total_weight": 0
            }
        
        models_status[model]["agents"] += 1
        models_status[model]["total_weight"] += weight
        if weight > 0:
            models_status[model]["active_agents"] += 1
    
    # Determine status per model
    models_detail = {}
    active_models = 0
    for model, stats in models_status.items():
        if stats["total_weight"] > 0:
            status = "active"
            active_models += 1
        else:
            status = "inactive"
        
        models_detail[model] = {
            "status": status,
            "agents": stats["agents"],
            "active_agents": stats["active_agents"],
            "total_weight": stats["total_weight"]
        }
    
    # Overall status
    if active_models == len(models_status):
        overall_status = "ok"
    elif active_models > 0:
        overall_status = "partial"
    else:
        overall_status = "inactive"
    
    return {
        "status": overall_status,
        "service": "bing-grounding-api",
        "region": AZURE_REGION,
        "agents_loaded": len(AGENTS),
        "active_models": active_models,
        "total_models": len(models_status),
        "models": models_detail
    }


@app.get("/agents")
async def list_agents():
    """
    List all available agent endpoints.
    
    Returns:
        List of available agents with their routes, models, and weights
    """
    agents_list = []
    for route, info in AGENTS.items():
        agents_list.append({
            "route": f"/bing-grounding/{route}",
            "model": info["model"],
            "index": info["index"],
            "agent_id": info["agent_id"],
            "weight": info.get("weight", 100)
        })
    
    return {
        "total": len(agents_list),
        "region": AZURE_REGION,
        "agents": agents_list
    }


@app.get("/models")
async def list_models():
    """
    List all model deployments in the Azure AI Foundry.
    
    Returns:
        List of model deployments with their configuration
    """
    import subprocess
    import json as json_module
    
    # Get resource group and foundry name from environment
    resource_group = os.getenv("AZURE_RESOURCE_GROUP")
    foundry_name = os.getenv("AZURE_FOUNDRY_NAME")
    
    if not resource_group or not foundry_name:
        # Try to extract from endpoint
        if PROJECT_ENDPOINT:
            # Endpoint format: https://<foundry>.cognitiveservices.azure.com/
            import re
            match = re.search(r'https://([^.]+)\.', PROJECT_ENDPOINT)
            if match:
                foundry_name = match.group(1)
    
    models_list = []
    
    if foundry_name and resource_group:
        try:
            result = subprocess.run(
                [
                    "az", "cognitiveservices", "account", "deployment", "list",
                    "--name", foundry_name,
                    "--resource-group", resource_group,
                    "-o", "json"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                deployments = json_module.loads(result.stdout)
                for deployment in deployments:
                    model_info = deployment.get("properties", {}).get("model", {})
                    sku = deployment.get("sku", {})
                    models_list.append({
                        "name": deployment.get("name"),
                        "model": model_info.get("name"),
                        "version": model_info.get("version"),
                        "format": model_info.get("format"),
                        "sku": sku.get("name"),
                        "capacity": sku.get("capacity"),
                        "status": deployment.get("properties", {}).get("provisioningState")
                    })
        except Exception as e:
            print(f"⚠️ Could not list models: {e}")
    
    return {
        "total": len(models_list),
        "region": AZURE_REGION,
        "foundry": foundry_name,
        "models": models_list
    }


# =============================================================================
# Admin Endpoints - Agent Weight Management
# =============================================================================

@app.post("/admin/refresh")
async def refresh_agents():
    """
    Reload all agents from Azure AI Foundry project.
    Call this after updating agent weights to refresh the cache.
    
    Returns:
        Updated list of agents with their weights
    """
    load_agents()
    return {
        "status": "refreshed",
        "region": AZURE_REGION,
        "total": len(AGENTS),
        "agents": [
            {"route": route, "model": info["model"], "weight": info.get("weight", 100)}
            for route, info in AGENTS.items()
        ]
    }


@app.put("/admin/agents/{agent_route}/weight")
async def update_agent_weight(agent_route: str, update: WeightUpdate):
    """
    Update the weight for an agent (for blue/green deployments).
    
    Args:
        agent_route: Agent route (e.g., "gpt4o_1", "gpt4o_2")
        update: Weight update payload (0-100)
        
    Returns:
        Updated agent info
        
    Example:
        PUT /admin/agents/gpt4o_2/weight
        Body: {"weight": 10}
    """
    if agent_route not in AGENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_route}' not found. Available: {list(AGENTS.keys())}"
        )
    
    if not 0 <= update.weight <= 100:
        raise HTTPException(
            status_code=400,
            detail="Weight must be between 0 and 100"
        )
    
    agent_id = AGENTS[agent_route]["agent_id"]
    
    try:
        # Update agent metadata in Azure AI Agent Service
        client = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=PROJECT_ENDPOINT
        )
        
        # Get current agent to preserve other metadata
        current_agent = client.agents.get_agent(agent_id)
        current_metadata = current_agent.metadata or {}
        current_metadata["weight"] = str(update.weight)
        
        # Update agent with new weight
        client.agents.update_agent(
            assistant_id=agent_id,
            metadata=current_metadata
        )
        
        # Update local cache
        AGENTS[agent_route]["weight"] = update.weight
        
        return {
            "status": "updated",
            "agent_route": agent_route,
            "agent_id": agent_id,
            "weight": update.weight
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update agent weight: {str(e)}"
        )


# Valid model patterns for validation (models that support Bing grounding)
VALID_MODEL_PATTERNS = [
    "gpt-4o", "gpt-4", "gpt-4.1-mini", "gpt-4-turbo",
    "gpt-35-turbo", "gpt-3.5-turbo"
]


def validate_model_and_query(query: str, model: str):
    """Validate that query and model parameters aren't swapped."""
    # Check if model looks like a question (contains spaces or question marks)
    if " " in model or "?" in model:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model '{model}'. It looks like you swapped 'query' and 'model' parameters. "
                   f"Use: ?query=your+question&model=gpt-4o"
        )
    
    # Check if query looks like a model name
    query_lower = query.lower().replace(" ", "")
    for valid_model in VALID_MODEL_PATTERNS:
        if query_lower == valid_model.replace("-", "").replace(".", ""):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid query '{query}'. It looks like a model name. "
                       f"Did you swap 'query' and 'model' parameters? "
                       f"Use: ?query=your+question&model={query}"
            )


def select_agent_by_weight(model: str) -> str:
    """
    Select an agent for the given model based on weights.
    
    Uses weighted random selection:
    - Agents with weight 0 are excluded
    - Agents with higher weights get more traffic
    - Returns 503 if no active agents (triggers APIM failover to another region)
    
    Args:
        model: Model name (e.g., "gpt-4o", "gpt-4.1-mini")
        
    Returns:
        Agent route (e.g., "gpt4o_1")
        
    Raises:
        HTTPException 503 if no active agents for model (allows APIM retry)
        HTTPException 404 if model doesn't exist at all
    """
    # Find all agents for this model with weight > 0
    model_agents = [
        (route, info) for route, info in AGENTS.items() 
        if info["model"] == model and info.get("weight", 100) > 0
    ]
    
    if not model_agents:
        # Check if model exists but has no active agents (all weights 0)
        all_model_agents = [(route, info) for route, info in AGENTS.items() if info["model"] == model]
        
        if all_model_agents:
            # Model exists but all agents have weight 0 - return 503 for APIM failover
            raise HTTPException(
                status_code=503,
                detail=f"No active agents for model '{model}' in region '{AZURE_REGION}'. "
                       f"All {len(all_model_agents)} agents have weight 0. "
                       f"Request may be retried on another region."
            )
        
        # Model doesn't exist - try fallback to gpt-4o
        fallback_agents = [
            (route, info) for route, info in AGENTS.items() 
            if info["model"] == "gpt-4o" and info.get("weight", 100) > 0
        ]
        
        if fallback_agents:
            model_agents = fallback_agents
        else:
            # No active gpt-4o agents either
            raise HTTPException(
                status_code=503,
                detail=f"No active agents for model '{model}' or fallback 'gpt-4o' in region '{AZURE_REGION}'. "
                       f"Request may be retried on another region."
            )
    
    # If only one agent, return it directly
    if len(model_agents) == 1:
        return model_agents[0][0]
    
    # Weighted random selection
    total_weight = sum(info.get("weight", 100) for _, info in model_agents)
    
    roll = random.randint(1, total_weight)
    cumulative = 0
    
    for route, info in model_agents:
        cumulative += info.get("weight", 100)
        if roll <= cumulative:
            return route
    
    # Fallback (shouldn't reach here)
    return model_agents[0][0]


@app.post("/bing-grounding")
async def bing_grounding_with_model(query: str, model: str = "gpt-4o"):
    """
    Endpoint for Bing grounding with model selection and weighted routing.
    
    Args:
        query: Search query string
        model: Model to use (gpt-4o, gpt-4.1-mini, gpt-4, gpt-35-turbo). Defaults to gpt-4o
        
    Returns:
        JSON response with content and citations
        
    Note:
        Agents are selected based on their weight metadata:
        - weight: 100 = receives all traffic (or proportional share)
        - weight: 0 = standby (no traffic)
        - weight: 50/50 = A/B testing
        - weight: 90/10 = canary deployment
        
    Example:
        POST /bing-grounding?query=What+is+Azure&model=gpt-4o
    """
    # Validate parameters aren't swapped
    validate_model_and_query(query, model)
    
    # Select agent based on weights
    agent_route = select_agent_by_weight(model)
    
    try:
        agent_instance = AGENTS[agent_route]["instance"]
        response = agent_instance.chat(query)
        result = json.loads(response)
        result["metadata"] = {
            "agent_route": agent_route,
            "model": model,
            "agent_id": AGENTS[agent_route]["agent_id"],
            "weight": AGENTS[agent_route].get("weight", 100),
            "region": AZURE_REGION
        }
        return result
    except Exception as e:
        return {
            "error": "processing_error",
            "message": str(e),
            "metadata": {
                "agent_route": agent_route,
                "model": model,
                "agent_id": AGENTS.get(agent_route, {}).get("agent_id", "unknown"),
                "region": AZURE_REGION
            }
        }


@app.post("/bing-grounding/{agent_route}")
async def bing_grounding_specific_agent(agent_route: str, request: QueryRequest):
    """
    Endpoint for specific Bing grounding agent by route.
    
    Args:
        agent_route: Agent route (e.g., "gpt4o_1", "gpt41mini_1")
        request: Query request body
        
    Returns:
        JSON response with content and citations
        
    Example routes:
        POST /bing-grounding/gpt4o_1
        POST /bing-grounding/gpt41mini_1
    """
    if agent_route not in AGENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_route}' not found. Available: {list(AGENTS.keys())}"
        )
    
    try:
        agent_instance = AGENTS[agent_route]["instance"]
        response = agent_instance.chat(request.query)
        result = json.loads(response)
        result["metadata"] = {
            "agent_route": agent_route,
            "model": AGENTS[agent_route]["model"],
            "agent_id": AGENTS[agent_route]["agent_id"],
            "region": AZURE_REGION
        }
        return result
    except Exception as e:
        return {
            "error": "processing_error",
            "message": str(e),
            "metadata": {
                "agent_route": agent_route,
                "model": AGENTS[agent_route]["model"],
                "agent_id": AGENTS[agent_route]["agent_id"],
                "region": AZURE_REGION
            }
        }