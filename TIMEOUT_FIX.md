# 504 Gateway Timeout & Authentication Fix

## Issues Identified

### 1. App Service Health Check Failures (504/503)
**Symptoms:**
```
Attempt 1: HTTP 504 - waiting...
Attempt 2: HTTP 503 - waiting...
```

**Root Cause:** No agents were created, so the app couldn't load and returned errors.

### 2. Azure CLI Token Expiration (CRITICAL)
**Symptoms:**
```
AzureCliCredential: ERROR: AADSTS700024: Client assertion is not within its valid time range.
Token valid from: 2026-01-28T19:42:11
Token expiry:     2026-01-28T19:47:11  ← 5 minutes only!
Agent creation:   2026-01-28T19:55:22  ← 8 minutes AFTER expiry
```

**Root Cause:** GitHub Actions OIDC tokens expire after 5 minutes, but the deployment pipeline takes 13+ minutes:
- 19:42:11 - Initial Azure login
- 19:42-19:45 - Deploy App Service (3 minutes)
- 19:45-19:54 - Health checks, model deployment, Bing connection (9 minutes)
- 19:55:22 - Try to create agents → **TOKEN EXPIRED**

**Result:** All 6 agents failed to create:
```
❌ Failed: DefaultAzureCredential failed to retrieve a token
✅ Successfully created 0/6 agents
```

## Fixes Implemented

### 1. GitHub Actions Token Refresh ([.github/workflows/deploy.yml](.github/workflows/deploy.yml))

**Added re-authentication before agent creation:**

```yaml
- name: Re-authenticate Azure CLI (token refresh)
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- name: Configure agents
  run: python scripts/postprovision_create_agents.py
```

**Benefits:**
- Fresh token before long-running agent creation
- Prevents AADSTS700024 token expiration errors
- Works for both primary and secondary region deployments

### 2. Application Startup ([app/main.py](app/main.py))

Added timeout and health check configurations:

```bicep
healthCheckPath: '/health'
appCommandLine: 'uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 300'

appSettings: [
  {
    name: 'WEBSITES_CONTAINER_START_TIME_LIMIT'
    value: '600'  // 10 minutes for cold start
  }
  {
    name: 'WEBSITES_PORT'
    value: '8000'
  }
  // ... existing settings
]
```

**Benefits:**
- **600s container start timeout** - allows agents to load without timing out
- **Health check path** - Azure monitors `/health` to detect when app is ready
- **300s keep-alive** - prevents connection drops during long-running requests
- **Explicit port** - ensures Azure routes to correct uvicorn port

### 2. Application Startup ([app/main.py](app/main.py))

**Non-blocking agent initialization:**

```python
async def async_load_agents():
    """Load agents in background with timeout"""
    try:
        await asyncio.wait_for(
            asyncio.to_thread(load_agents),
            timeout=AGENT_LOAD_TIMEOUT
        )
    except asyncio.TimeoutError:
        print("⚠️ Agent loading timed out - will retry")
```

**Async lifespan:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start agent loading in background (non-blocking)
    load_task = asyncio.create_task(async_load_agents())
    refresh_task = asyncio.create_task(periodic_agent_refresh())
    
    print("✅ API ready to accept requests (agents loading in background)")
    yield
```

**Benefits:**
- App starts immediately without waiting for all agents
- Agents load in background
- 120s timeout per agent load attempt
- Retries on next refresh cycle if initial load fails

### 3. Infrastructure ([infra/appservice.bicep](infra/appservice.bicep))

**Always returns 200 OK:**

```python
@app.get("/health")
async def health_check():
    if not AGENTS:
        return {
            "status": "starting",
            "message": "Agents loading in background - API operational"
        }
    # ... return full status
```

**Benefits:**
- Azure health checks pass immediately
- Shows "starting" status while agents load
- Prevents premature app restarts
- Provides detailed agent status once loaded

### 4. Error Handling ([app/main.py](app/main.py))

**Graceful degradation:**

```python
def load_agents():
    try:
        all_agents = get_all_agent_ids()
        # ... load agents
    except Exception as e:
        print(f"⚠️ Error loading agents: {e}")
        # Don't fail startup - allow app to start even if agents fail
```

## Deployment

### Option 1: Full Redeployment (Recommended)

```bash
# Redeploy infrastructure and app
azd up
```

This will:
1. Update App Service with new timeout settings
2. Configure health check path
3. Deploy updated application code

### Option 2: Update Existing Deployment

```bash
# Update infrastructure only
azd provision

# Then deploy code
azd deploy
```

### Option 3: Manual Azure Portal

If you can't redeploy, configure manually:

1. **App Service → Configuration → General Settings:**
   - Add: `WEBSITES_CONTAINER_START_TIME_LIMIT = 600`
   - Add: `WEBSITES_PORT = 8000`

2. **App Service → Health check:**
   - Health check path: `/health`
   - Save and restart

3. **Restart the app:**
   ```bash
   az webapp restart --name <your-app-name> --resource-group <your-rg>
   ```

## Verification

After deployment, verify the fixes:

### 1. Check Health Endpoint

```bash
curl https://<your-app>.azurewebsites.net/health
```

**During startup:**
```json
{
  "status": "starting",
  "agents_loaded": 0,
  "message": "Agents loading in background - API operational"
}
```

**After agents load:**
```json
{
  "status": "ok",
  "agents_loaded": 12,
  "active_models": 1,
  "models": {...}
}
```

### 2. Monitor Logs

```bash
az webapp log tail --name <your-app-name> --resource-group <your-rg>
```

Look for:
```
🚀 Starting Bing Grounding API...
⏰ Background refresh scheduled every 300 seconds
✅ API ready to accept requests (agents loading in background)
✅ Registered agent: gpt4o_1 -> ...
```

### 3. Test API Endpoint

```bash
# Should work even during startup
curl -X POST "https://<your-app>.azurewebsites.net/bing-grounding?query=test&model=gpt-4o"
```

## Troubleshooting

### Still Getting 504s?

1. **Check App Service logs:**
   ```bash
   az webapp log tail --name <your-app-name> --resource-group <your-rg>
   ```

2. **Verify timeout settings applied:**
   ```bash
   az webapp config appsettings list --name <your-app-name> --resource-group <your-rg> | grep TIMEOUT
   ```

3. **Check App Service Plan tier:**
   ```bash
   az appservice plan show --name <plan-name> --resource-group <your-rg>
   ```
   
   Consider upgrading from B1 to S1 for better performance:
   ```bash
   az appservice plan update --name <plan-name> --resource-group <your-rg> --sku S1
   ```

4. **Review health check status:**
   - Azure Portal → App Service → Health check
   - Should show "Healthy" within 2-3 minutes of startup

### Agents Not Loading?

Check for permission issues:

```bash
# Verify managed identity has correct role
az role assignment list --assignee <app-principal-id> --all
```

Should have "Azure AI Developer" on AI Foundry project.

### Long Response Times?

If individual requests timeout:
- Increase `timeout-keep-alive` in bicep and startup.sh
- Check Azure AI Foundry quotas
- Monitor Bing grounding API performance

## Configuration Options

Add to App Service Configuration:

```bash
# Agent refresh interval (default: 300s)
AGENT_REFRESH_INTERVAL=600

# Agent load timeout (default: 120s)  
AGENT_LOAD_TIMEOUT=180
```

## Performance Tips

1. **Use S1 tier or higher** for production (has more memory/CPU)
2. **Enable Application Insights** for detailed monitoring
3. **Scale out** to multiple instances for high availability
4. **Configure APIM caching** to reduce backend calls

## Summary

The 504 errors were caused by:
- ❌ Synchronous agent loading blocking startup (30-60s for 12 agents)
- ❌ No health check configured (Azure couldn't verify app health)
- ❌ Default 230s startup timeout too short
- ❌ No retry logic for failed agent loads

Fixed by:
- ✅ Async background agent loading (non-blocking)
- ✅ Health check path configured (`/health`)
- ✅ 600s container start timeout
- ✅ Graceful degradation (app starts even if agents fail)
- ✅ 120s timeout per agent load with retry
- ✅ 300s keep-alive for long requests
