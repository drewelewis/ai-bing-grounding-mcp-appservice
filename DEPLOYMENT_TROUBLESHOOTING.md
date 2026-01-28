# Deployment Troubleshooting Guide

## Quick Diagnosis

### Check GitHub Actions Log for These Errors:

#### ❌ Token Expiration Error
```
AzureCliCredential: ERROR: AADSTS700024: Client assertion is not within its valid time range
```
**Fix:** Re-authenticate before long-running steps (already implemented in workflow)

#### ❌ Health Check Failures
```
Attempt 1: HTTP 504 - waiting...
Attempt 2: HTTP 503 - waiting...
```
**Causes:**
1. Agents not created (check logs above)
2. App still starting up (normal for first deployment)
3. Container timeout (check `WEBSITES_CONTAINER_START_TIME_LIMIT`)

#### ❌ No Agents Created
```
✅ Successfully created 0/6 agents
⚠️ No agents were created successfully
```
**Causes:**
1. Token expired (see above)
2. Missing permissions (need "Azure AI Developer" role)
3. Missing Bing connection

## Verification Steps

### 1. Check Deployment Status

```bash
# Get workflow run status
gh run list --limit 5

# View specific run logs
gh run view <RUN_ID> --log
```

### 2. Check App Service Health

```bash
APP_NAME="app-52hltr3kdvkvo"

# Health endpoint
curl https://${APP_NAME}.azurewebsites.net/health

# Expected response when healthy:
{
  "status": "ok",
  "agents_loaded": 6,
  "active_models": 1
}
```

### 3. Check Agents

```bash
# List all agents
curl https://${APP_NAME}.azurewebsites.net/agents

# Expected: 6 agents (gpt4o_1, gpt4o_2, etc.)
```

### 4. Check App Service Logs

```bash
# Stream live logs
az webapp log tail --name $APP_NAME --resource-group rg-bing-grounding-mcp-prod

# Look for:
✅ Registered agent: gpt4o_1 -> ...
🚀 Total agents available: 6
```

## Common Issues & Fixes

### Issue: "DefaultAzureCredential failed" in GitHub Actions

**Symptoms:**
- Agent creation fails
- Token expiration errors

**Solution:**
Already fixed in workflow - re-authentication happens automatically before agent creation.

**Verify fix:**
```yaml
# In .github/workflows/deploy.yml, look for:
- name: Re-authenticate Azure CLI (token refresh)
  uses: azure/login@v2
```

### Issue: "No agents loaded" in health check

**Symptoms:**
```json
{
  "status": "starting",
  "agents_loaded": 0,
  "message": "Agents loading in background - API operational"
}
```

**Solutions:**

1. **Wait for background loading** (30-120 seconds):
   ```bash
   watch -n 5 'curl -s https://app-52hltr3kdvkvo.azurewebsites.net/health | jq .'
   ```

2. **Check if agents exist in Azure AI Foundry:**
   ```bash
   # List agents using Azure CLI
   az ml agent list --workspace-name ai-proj-52hltr3kdvkvo --resource-group rg-bing-grounding-mcp-prod
   ```

3. **Manually create agents if missing:**
   ```bash
   # In your local environment
   python scripts/postprovision_create_agents.py
   ```

4. **Trigger agent refresh:**
   ```bash
   curl -X POST https://app-52hltr3kdvkvo.azurewebsites.net/admin/refresh
   ```

### Issue: "Container start timeout"

**Symptoms:**
- App Service shows "Application Error"
- Logs show timeout after 230 seconds

**Solution:**
Already configured with 600-second timeout:
```bicep
appSettings: [
  {
    name: 'WEBSITES_CONTAINER_START_TIME_LIMIT'
    value: '600'
  }
]
```

**Verify:**
```bash
az webapp config appsettings list \
  --name app-52hltr3kdvkvo \
  --resource-group rg-bing-grounding-mcp-prod \
  --query "[?name=='WEBSITES_CONTAINER_START_TIME_LIMIT'].value" -o tsv
```

Should return: `600`

### Issue: "ManagedIdentityCredential authentication unavailable"

**Symptoms:**
- App can't load agents on startup
- Authentication errors in app logs

**Solution:**
Verify managed identity has correct role:

```bash
# Get App Service principal ID
PRINCIPAL_ID=$(az webapp identity show \
  --name app-52hltr3kdvkvo \
  --resource-group rg-bing-grounding-mcp-prod \
  --query principalId -o tsv)

# Check role assignments
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --all \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table

# Should include:
# Azure AI Developer | /subscriptions/.../ai-foundry-...
```

## Manual Recovery Steps

### If GitHub Actions Deployment Fails

1. **Re-run failed jobs:**
   ```bash
   gh run rerun <RUN_ID> --failed
   ```

2. **Or deploy manually:**
   ```bash
   cd c:\gitrepos\ai-bing-grounding-mcp-appservice
   
   # Authenticate
   az login
   az account set --subscription <YOUR_SUB_ID>
   
   # Deploy app
   az webapp deployment source config-zip \
     --name app-52hltr3kdvkvo \
     --resource-group rg-bing-grounding-mcp-prod \
     --src deploy.zip
   
   # Create agents
   export AZURE_AI_PROJECT_ENDPOINT=https://ai-foundry-52hltr3kdvkvo.cognitiveservices.azure.com/
   export AZURE_SUBSCRIPTION_ID=<YOUR_SUB_ID>
   python scripts/postprovision_create_agents.py
   ```

### If App Service Won't Start

1. **Check logs for errors:**
   ```bash
   az webapp log tail --name app-52hltr3kdvkvo --resource-group rg-bing-grounding-mcp-prod
   ```

2. **Restart app:**
   ```bash
   az webapp restart --name app-52hltr3kdvkvo --resource-group rg-bing-grounding-mcp-prod
   ```

3. **Check for deployment errors:**
   ```bash
   az webapp deployment list \
     --name app-52hltr3kdvkvo \
     --resource-group rg-bing-grounding-mcp-prod \
     --query "[0]" -o json
   ```

## Expected Timeline

Typical successful deployment:
```
00:00 - Start GitHub Actions workflow
00:02 - Build package complete
00:03 - Deploy to App Service started
00:06 - Deploy to App Service complete
00:07 - Health check (may show "starting")
00:08 - Deploy models (skipped if already exists)
00:09 - Create Bing connection (skipped if exists)
00:10 - Re-authenticate Azure CLI ← NEW STEP
00:11 - Create agents (6 agents × ~10s each)
00:12 - Agents created successfully ✅
00:13 - Health check returns 200 OK ✅
```

## Contact & Support

If issues persist:

1. Check [TIMEOUT_FIX.md](TIMEOUT_FIX.md) for detailed fix explanations
2. Review App Service diagnostic logs in Azure Portal
3. Check Application Insights for runtime errors
4. Verify all environment variables and secrets in GitHub

## Quick Commands Reference

```bash
# Variables
APP_NAME="app-52hltr3kdvkvo"
RG="rg-bing-grounding-mcp-prod"

# Health check
curl https://${APP_NAME}.azurewebsites.net/health | jq .

# List agents
curl https://${APP_NAME}.azurewebsites.net/agents | jq .

# Refresh agents
curl -X POST https://${APP_NAME}.azurewebsites.net/admin/refresh | jq .

# Stream logs
az webapp log tail --name $APP_NAME --resource-group $RG

# Restart app
az webapp restart --name $APP_NAME --resource-group $RG

# Check settings
az webapp config appsettings list --name $APP_NAME --resource-group $RG

# Check managed identity role
PRINCIPAL_ID=$(az webapp identity show --name $APP_NAME --resource-group $RG --query principalId -o tsv)
az role assignment list --assignee $PRINCIPAL_ID --all -o table
```
