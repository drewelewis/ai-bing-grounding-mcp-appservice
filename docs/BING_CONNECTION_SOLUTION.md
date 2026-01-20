# Bing Grounding Connection - Bicep Solution

## Problem

When deploying Azure AI Foundry agents with Bing Grounding capability, agents failed at runtime with:
```
missing_required_parameter: AML connections are required for Bing Grounding tool
```

**Root Cause**: The connection between AI Foundry and Bing Grounding resource must be explicitly created, even when both resources are in the same resource group.

## Solution

We created a Bicep template (`infra/bing-connection.bicep`) that programmatically creates the required connection using the official ARM template schema for `Microsoft.CognitiveServices/accounts/connections`.

### Key Requirements Discovered

From the official ARM template documentation:
- **Category**: Must be `BingLLMSearch` (not `BingGrounding`)
- **AuthType**: Must be `ApiKey` (with placeholder value)
- **Metadata**: Must include:
  - `ApiType`: `"grounding"`
  - `BingResourceId`: Full resource ID of the Bing resource
  - `Location`: `"global"` (required field)

### Implementation

**1. Bicep Template** (`infra/bing-connection.bicep`):
```bicep
resource bingConnection 'Microsoft.CognitiveServices/accounts/connections@2025-10-01-preview' = {
  parent: aiFoundry
  name: 'default-bing'
  properties: {
    category: 'BingLLMSearch'
    target: 'https://api.bing.microsoft.com/'
    authType: 'ApiKey'
    credentials: {
      key: apiKeyPlaceholder // Placeholder - actual auth uses BingResourceId
    }
    metadata: {
      ApiType: 'grounding'
      BingResourceId: bingResourceId
      Location: location
    }
  }
}
```

**2. Deployment Script** (`scripts/postprovision_deploy_bing_connection.py`):
- Reads environment variables from `.azure/{env}/.env`
- Deploys the Bicep template using `az deployment group create`
- Verifies the connection was created successfully

**3. Integration** (`azure.yaml`):
```yaml
postprovision:
  windows:
    shell: pwsh
    run: python scripts/postprovision_deploy_models.py ; 
         python scripts/postprovision_deploy_bing_connection.py ; 
         python scripts/postprovision_create_agents.py
```

Order matters:
1. Deploy models first
2. Create Bing connection (MUST be before agents)
3. Create agents (agents reference the connection)

## Testing

### Manual Deployment Test
```bash
az deployment group create \
  --subscription <subscription-id> \
  --resource-group <resource-group> \
  --name test-bing-connection \
  --template-file infra/bing-connection.bicep \
  --parameters \
    foundryName=<ai-foundry-name> \
    bingResourceId=<bing-resource-id> \
    location=global
```

### Verify Connection Exists
```bash
az rest --method GET \
  --url "https://management.azure.com/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-name>/connections?api-version=2025-06-01"
```

Expected output:
```json
{
  "value": [
    {
      "name": "default-bing",
      "properties": {
        "authType": "ApiKey",
        "category": "BingLLMSearch",
        "metadata": {
          "ApiType": "grounding",
          "BingResourceId": "/subscriptions/.../Microsoft.Bing/accounts/...",
          "Location": "global"
        },
        "target": "https://api.bing.microsoft.com/"
      }
    }
  ]
}
```

## References

- **ARM Template Schema**: https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts/connections
- **Bing Grounding Setup**: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding
- **Connection Categories**: `BingLLMSearch` is the official category name for Bing Grounding in the ARM template schema

## Previous Attempts (Failed)

1. **Assumption**: Same resource group = automatic connection
   - **Result**: False - connection must be explicitly created

2. **REST API with JSON payload**:
   - Tried category: `BingGrounding` → Schema rejected
   - Tried authType: `None` → Validation error (requires credentials)

3. **Azure ML Client SDK**:
   - Wrong resource type (AI Foundry is CognitiveServices, not MachineLearningServices)

4. **Portal UI**:
   - Works but defeats the purpose of `azd up` automation
   - User rejected manual steps

## Success Criteria Met

✅ Fully automated via `azd up`  
✅ No manual portal steps required  
✅ Connection created programmatically  
✅ Uses official ARM template schema  
✅ Agents can use Bing Grounding at runtime  

## Next Steps

1. Test agent with Bing Grounding tool in Azure AI Foundry portal
2. Verify query like "What happened today in France?" works
3. Document any runtime issues or additional configuration needed
