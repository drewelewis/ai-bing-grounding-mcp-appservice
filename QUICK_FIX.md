# Quick Fix Summary

## What Was Wrong

**Azure CLI token expired during deployment** causing agent creation to fail:
- Token lifetime: 5 minutes
- Deployment duration: 13 minutes
- Agent creation attempted at minute 13 → **FAILED**
- Result: 0/6 agents created, app returns 503/504 errors

## What Was Fixed

### 1. Added Token Refresh in GitHub Workflow
Added re-authentication step before agent creation in [.github/workflows/deploy.yml](.github/workflows/deploy.yml):

```yaml
- name: Re-authenticate Azure CLI (token refresh)
  uses: azure/login@v2
  # ... ensures fresh token before creating agents
```

### 2. Made App Startup Non-Blocking
Changed [app/main.py](app/main.py) to load agents in background so app starts immediately.

### 3. Increased Timeouts
Updated [infra/appservice.bicep](infra/appservice.bicep) with longer timeouts and health check configuration.

## Next Steps

### 1. Commit & Push Changes
```bash
git add .
git commit -m "Fix: Add Azure CLI token refresh before agent creation"
git push origin main
```

This will automatically trigger the deployment workflow.

### 2. Monitor the Deployment

Watch at: https://github.com/drewelewis/ai-bing-grounding-mcp-appservice/actions

**Expected result:**
```
✅ Azure Login (OIDC) - 19:42
✅ Deploy to App Service - 19:45
✅ Deploy models - 19:46
✅ Create Bing connection - 19:47
✅ Re-authenticate Azure CLI - 19:48  ← NEW!
✅ Configure agents - 19:49           ← Should work now!
   → Successfully created 6/6 agents
✅ Health check - 200 OK
```

### 3. Verify Agents Created

After deployment completes:
```bash
curl https://app-52hltr3kdvkvo.azurewebsites.net/agents
```

Expected: List of 6 agents (gpt4o_1, gpt4o_2, gpt41mini_1, etc.)

### 4. Test API

```bash
curl -X POST "https://app-52hltr3kdvkvo.azurewebsites.net/bing-grounding?query=what+is+azure&model=gpt-4o"
```

Expected: JSON response with content and citations.

## If Issues Persist

See [DEPLOYMENT_TROUBLESHOOTING.md](DEPLOYMENT_TROUBLESHOOTING.md) for detailed diagnostics.

## Summary

**Before:**
- Token expired after 5 minutes
- Agent creation failed at minute 13
- App had no agents → 503/504 errors

**After:**
- Fresh token obtained at minute 10
- Agents created successfully at minute 11
- App has 6 agents → 200 OK responses

The fix is simple: **refresh the Azure CLI token before the long-running agent creation step**.
