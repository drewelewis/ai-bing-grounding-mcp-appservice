# Agent API Update: Classic to New Agents API

## Issue

Agents were being created as **"Classic Agents"** in Azure AI Foundry portal, with a warning message:
```
Classic Agents (36)
To unlock the latest capabilities, select a classic agent from this list and save it as a new agent powered by the updated API.
```

## Root Cause

The deployment script (`scripts/postprovision_create_agents.py`) was using the **deprecated classic Agents API**:

```python
# OLD - Classic Agents API (deprecated)
from azure.ai.agents.models import BingGroundingTool

bing = BingGroundingTool(connection_id=bing_connection_id)

agent = project_client.agents.create_agent(
    model=model_name,
    name=agent_name,
    instructions="...",
    tools=bing.definitions
)
```

## Solution

Updated to use the **new Agents API** (introduced in azure-ai-projects SDK):

```python
# NEW - Current Agents API
from azure.ai.projects.models import (
    PromptAgentDefinition,
    BingGroundingAgentTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration
)

bing_tool = BingGroundingAgentTool(
    bing_grounding=BingGroundingSearchToolParameters(
        search_configurations=[
            BingGroundingSearchConfiguration(
                project_connection_id=bing_connection_id
            )
        ]
    )
)

agent = project_client.agents.create_version(
    agent_name=agent_name,
    definition=PromptAgentDefinition(
        model=model_name,
        instructions="...",
        tools=[bing_tool]
    ),
    description="Agent with Bing grounding for real-time web search"
)
```

## Key Differences

| Aspect | Classic API | New API |
|--------|-------------|---------|
| **Package** | `azure.ai.agents.models` | `azure.ai.projects.models` |
| **Method** | `create_agent()` | `create_version()` |
| **Tool Class** | `BingGroundingTool` | `BingGroundingAgentTool` |
| **Definition** | Direct parameters | `PromptAgentDefinition` wrapper |
| **Tool Config** | `tools=bing.definitions` | `tools=[bing_tool]` |
| **Versioning** | No versioning | Built-in versioning support |

## Changes Made

### 1. Updated Imports
- Removed: `azure.ai.agents.models.BingGroundingTool`
- Added: `azure.ai.projects.models.*`
  - `PromptAgentDefinition`
  - `BingGroundingAgentTool`
  - `BingGroundingSearchToolParameters`
  - `BingGroundingSearchConfiguration`

### 2. Updated Agent Creation Logic
- Changed from `create_agent()` to `create_version()`
- Wrapped configuration in `PromptAgentDefinition`
- Used new `BingGroundingAgentTool` configuration

### 3. Removed Deprecated Package
- No longer installing `azure-ai-agents` package
- Only `azure-ai-projects` and `azure-identity` required

## Benefits of New API

1. **Versioning Support**: Agents are now versioned automatically
2. **Better Tool Configuration**: More structured tool configuration
3. **Portal Compatibility**: Agents show in "Agents" section, not "Classic Agents"
4. **Latest Features**: Access to newest Azure AI Foundry capabilities
5. **Active Maintenance**: Microsoft is actively maintaining this API

## Testing After Update

To verify the fix works:

```bash
# 1. Redeploy agents
azd deploy

# 2. Check Azure Portal
# Navigate to: Azure AI Foundry > Project > Agents
# Verify agents appear in "Agents" section (not "Classic Agents")

# 3. Verify environment variables
azd env get-values | findstr AGENT
```

Expected output:
```
AZURE_AI_AGENT_GPT4O_1="agent_id_here"
AZURE_AI_AGENT_GPT4O_2="agent_id_here"
...
AZURE_AI_AGENT_GPT4O_12="agent_id_here"
```

## Portal Verification

After deployment, check the Azure AI Foundry portal:

**Before Fix:**
- Agents listed under "Classic Agents (36)"
- Warning banner about needing to migrate
- Limited features

**After Fix:**
- Agents listed under "Agents"
- No migration warnings
- Full access to latest features
- Versioning information displayed

## References

- [Azure AI Foundry Agents Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/)
- [Bing Grounding Tools](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-tools)
- [azure-ai-projects SDK](https://pypi.org/project/azure-ai-projects/)

## Rollout Plan

1. ✅ Update `postprovision_create_agents.py` script
2. ✅ Test locally with new SDK
3. ⏳ Deploy to QA environment
4. ⏳ Verify agents in portal
5. ⏳ Deploy to Production
6. ⏳ Clean up old classic agents (if needed)

## Notes

- **Backward Compatibility**: The new API is not backward compatible with classic agents
- **Existing Agents**: Existing classic agents will continue to work but should be migrated
- **Migration**: No automatic migration - must redeploy with new script
- **Connection ID Format**: Connection ID format remains the same

## Troubleshooting

### Issue: Import Error
```
ImportError: cannot import name 'BingGroundingAgentTool'
```
**Solution**: Update azure-ai-projects package
```bash
pip install --upgrade azure-ai-projects
```

### Issue: Agents still show as Classic
**Solution**: 
1. Delete old classic agents in portal
2. Run `azd deploy` to create new agents
3. Verify agents appear in "Agents" section

### Issue: Connection ID not found
**Solution**: Ensure `AZURE_BING_CONNECTION_ID` is set in environment or let script construct default

---

**Last Updated**: December 9, 2024  
**Updated By**: GitHub Copilot  
**Status**: ✅ Implemented
