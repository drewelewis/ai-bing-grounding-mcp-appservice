# Migration to Azure AI Foundry

## Overview

This project has been migrated from **Azure AI Hub/Project (preview)** to **Azure AI Foundry (GA)** architecture. This migration ensures:
- **Generally Available (GA)** agent support
- Latest SDK compatibility (`azure-ai-projects` v1.0.0b12+)
- Simpler infrastructure (fewer resources)
- Future-proof architecture

## Key Architecture Changes

### Old Architecture (Hub-based - DEPRECATED)
```
Azure AI Hub (MachineLearningServices/workspaces kind='Hub')
├── Azure AI Project (MachineLearningServices/workspaces kind='Project')
└── Azure OpenAI (separate CognitiveServices/accounts)
```

**Endpoint Format:** Connection string  
`eastus.api.azureml.ms;subscription-id;resource-group;workspace-name`

**SDK:** azure-ai-projects v1.0.0b10 (max version for hub-based)

**Client Init:**
```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient.from_connection_string(
    conn_str=project_endpoint,
    credential=DefaultAzureCredential()
)
```

### New Architecture (Foundry - GA)
```
Microsoft Foundry (CognitiveServices/accounts kind='AIServices')
├── Foundry Project (CognitiveServices/accounts/projects)
└── Azure OpenAI (built-in, deployed directly to Foundry)
```

**Endpoint Format:** HTTPS  
`https://{foundryName}.cognitiveservices.azure.com/`

**SDK:** azure-ai-projects v1.0.0b12+ (latest)

**Client Init:**
```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)
```

## Migration Checklist

### ✅ Completed

- [x] Deleted all hub-based resources (`azd down --force --purge`)
- [x] Backed up original Bicep template (`infra/resources.bicep.hub-backup`)
- [x] Updated `infra/resources.bicep`:
  - [x] Changed parameters: `aiHubName` → `foundryName`, `aiProjectName` → `projectName`
  - [x] Replaced AI Hub with Foundry resource (`Microsoft.CognitiveServices/accounts` kind='AIServices')
  - [x] Replaced AI Project with Foundry Project (child resource)
  - [x] Removed separate Azure OpenAI resource (built into Foundry)
  - [x] Updated GPT-4o deployment to use Foundry parent with GlobalStandard SKU
  - [x] Updated Container App environment variables to use HTTPS endpoint
  - [x] Updated role assignments to reference Foundry/Project
  - [x] Updated outputs section with Foundry endpoint format
- [x] Updated `infra/main.bicep`:
  - [x] Changed parameters to `foundryName` and `projectName`
  - [x] Updated outputs to use new resource references
- [x] Updated `scripts/create-agents.py`:
  - [x] Changed client init to `AIProjectClient(endpoint, credential)`
  - [x] Updated Bing tool to use beta12+ SDK format
  - [x] Updated comments to reflect Foundry architecture
- [x] Validated Bicep template syntax

### 🔄 Next Steps

1. **Provision Foundry Infrastructure**
   ```bash
   azd provision
   ```

2. **Create Bing Grounding Resource** (if Bicep deployment fails)
   - Via Azure Portal: Create Microsoft.Bing/accounts kind='Bing.Grounding'
   - Or via postprovision script

3. **Create Bing Connection in Foundry**
   - Azure AI Foundry Studio → Connections → Add Bing connection

4. **Install Latest SDK**
   ```bash
   pip install --upgrade azure-ai-projects
   ```

5. **Create Agent Pool**
   ```bash
   python scripts/create-agents.py
   ```

6. **Deploy Application**
   ```bash
   azd deploy
   ```

7. **Test Endpoints**
   ```bash
   curl $AZURE_APIM_GATEWAY_URL/api/v1/chat
   ```

## Environment Variables

### Updated in azd Outputs
- `AZURE_FOUNDRY_NAME` - Name of the Foundry resource
- `AZURE_AI_PROJECT_NAME` - Name of the Foundry project
- `AZURE_AI_PROJECT_ENDPOINT` - HTTPS endpoint (https://{foundry}.cognitiveservices.azure.com/)
- `AZURE_AI_PROJECT_RESOURCE_ID` - Full resource ID of the project
- `AZURE_OPENAI_MODEL_GPT4O` - Deployment name for GPT-4o model

### Removed from Outputs
- `AZURE_AI_HUB_NAME` (no longer needed)
- `AZURE_OPENAI_NAME` (OpenAI is built into Foundry)
- `AZURE_OPENAI_ENDPOINT` (use Foundry endpoint instead)

## Resource Changes

### Removed Resources
- `Microsoft.MachineLearningServices/workspaces` (AI Hub)
- `Microsoft.MachineLearningServices/workspaces` (AI Project)
- `Microsoft.CognitiveServices/accounts` kind='OpenAI' (separate OpenAI)
- `Microsoft.MachineLearningServices/workspaces/connections` (OpenAI connection)

### New Resources
- `Microsoft.CognitiveServices/accounts` kind='AIServices' (Foundry)
- `Microsoft.CognitiveServices/accounts/projects` (Foundry Project)

### Modified Resources
- GPT-4o Deployment:
  - Parent: `foundry` (instead of separate OpenAI resource)
  - SKU: `GlobalStandard` (instead of Standard)
  - API Version: `2024-10-01`

## SDK Differences

### Hub-based (beta10)
```python
# Client initialization
project_client = AIProjectClient.from_connection_string(
    conn_str="eastus.api.azureml.ms;sub-id;rg;workspace",
    credential=DefaultAzureCredential()
)

# Bing tool with connection ID
tools=[BingGroundingToolDefinition(
    bing_grounding={"connection_id": bing_connection_id}
)]
```

### Foundry (beta12+)
```python
# Client initialization
project_client = AIProjectClient(
    endpoint="https://foundry-name.cognitiveservices.azure.com/",
    credential=DefaultAzureCredential()
)

# Bing tool (connection built-in)
tools=[BingGroundingToolDefinition()]
```

## Role Assignments

### Old Roles (Hub-based)
- Container Apps → AI Project: Contributor
- AI Project → OpenAI: Azure AI Developer
- AI Hub → OpenAI: Azure AI Developer

### New Roles (Foundry)
- Container Apps → Foundry Project: Azure AI Developer

Simplified! Foundry's built-in OpenAI means no cross-resource role assignments needed.

## Deployment Models

### Hub-based
- SKU: `Standard`
- Capacity: 10
- Parent: Separate OpenAI resource

### Foundry
- SKU: `GlobalStandard`
- Capacity: 10
- Parent: Foundry resource

GlobalStandard provides better availability and performance through Azure's global load balancing.

## References

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/what-is-ai-foundry)
- [Azure AI Projects SDK](https://pypi.org/project/azure-ai-projects/)
- [Bing Grounding for Agents](https://learn.microsoft.com/azure/ai-foundry/agents/tools/bing-grounding)
- [Official Foundry Bicep Sample](https://github.com/Azure-AI-Foundry/foundry-samples/tree/main/samples/microsoft/infrastructure-setup)

## Backup

The original hub-based Bicep template is backed up at:
- `infra/resources.bicep.hub-backup`

To restore: `Copy-Item infra\resources.bicep.hub-backup infra\resources.bicep`
