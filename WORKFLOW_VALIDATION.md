# Workflow & Naming Validation

## Step-by-Step Workflow

### ✅ Step 1: Create .env Files
Create environment configuration files:
- `.env.production_primary`
- `.env.production_secondary`
- `.env.qa_primary`
- `.env.qa_secondary`

**Status:** ✅ Created

### ✅ Step 2: Sync to GitHub
Run sync script to push values to GitHub Environments:
```powershell
.\sync-github-env.ps1 -Environment all
```

**Status:** ⏳ Pending (user action required)

### ✅ Step 3: Deploy Infrastructure
Run `deploy-infra.yml` workflow:
```bash
gh workflow run deploy-infra.yml --field action=provision --field environment=prod
```

**Status:** ⏳ Pending

### ✅ Step 4: Deploy Application
Push to main branch (auto-triggers) or manually trigger `deploy.yml`:
```bash
gh workflow run deploy.yml --field environment=production
```

**Status:** ⏳ Pending

---

## Azure Naming Convention Validation

### Parameters Used in Bicep

**From deploy-infra.yml:**
- `environmentName` = `vars.AZURE_ENV_NAME` (e.g., "prod", "qa", "dev")
  - ✅ **Valid:** Alphanumeric, lowercase, no special characters
  - Used in: Resource group names, tags

**From .env files (NOT used in infrastructure creation):**
- These reference EXISTING resources after infrastructure is deployed
- Used by deployment workflow to configure App Service settings

### Generated Azure Resource Names

Based on `environmentName: "prod"` and `location: "eastus2"`:

| Resource Type | Generated Name | Naming Rules | Valid? |
|--------------|----------------|--------------|--------|
| **Resource Group** | `rg-bing-grounding-mcp-prod-primary` | Letters, numbers, periods, hyphens, underscores, parentheses<br>Max: 90 chars | ✅ |
| **App Service** | `app-52hltr3kdvkvo` | Letters, numbers, hyphens<br>Max: 60 chars | ✅ |
| **App Service Plan** | `asp-52hltr3kdvkvo` | Letters, numbers, hyphens<br>Max: 40 chars | ✅ |
| **AI Foundry** | `ai-foundry-52hltr3kdvkvo` | Letters, numbers, hyphens<br>Max: 64 chars | ✅ |
| **AI Project** | `ai-proj-52hltr3kdvkvo` | Letters, numbers, hyphens, underscores<br>Max: 64 chars | ✅ |
| **API Management** | `apim-52hltr3kdvkvo` | Letters, numbers, hyphens<br>Max: 50 chars | ✅ |

**Notes:**
- `resourceToken` = `uniqueString(subscription().id, environmentName, location)`
  - Result: 13 lowercase alphanumeric characters (e.g., "52hltr3kdvkvo")
  - Deterministic - same inputs = same output
  - Different per region (eastus2 vs westus2)

### Critical Insight: environmentName vs GitHub Environments

**Two separate concepts:**

1. **`environmentName` (Bicep parameter):**
   - Set via `AZURE_ENV_NAME` variable
   - Examples: "prod", "qa", "dev"
   - Used in resource naming: `rg-bing-grounding-mcp-${environmentName}-primary`
   - ✅ NO UNDERSCORES

2. **GitHub Environment names:**
   - Examples: `production_primary`, `production_secondary`
   - Used by GitHub Actions for variable scoping
   - NOT used in Azure resource names
   - ✅ CAN HAVE UNDERSCORES

### Current Configuration Mismatch

**Problem identified:**

```yaml
# deploy-infra.yml
environment: prod  # AZURE_ENV_NAME = "prod"
```

But resource groups created from Bicep will be:
- `rg-bing-grounding-mcp-prod-primary`
- `rg-bing-grounding-mcp-prod-secondary`

And .env files reference:
- `RESOURCE_GROUP=rg-bing-grounding-mcp-prod-primary`

**However**, the existing production resources are:
- `rg-bing-grounding-mcp-prod` ❌ (missing -primary)

### Verification Needed

Check actual resource group names in Azure:
```bash
az group list --query "[?contains(name, 'bing-grounding-mcp')].name" -o table
```

**If they exist as:**
- `rg-bing-grounding-mcp-prod` (no -primary)
- `rg-bing-grounding-mcp-prod-secondary`

**Then we need to either:**

**Option A:** Update Bicep to match existing (remove -primary from line 65)
```bicep
var finalResourceGroupName = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}bing-grounding-mcp-${environmentName}'
```

**Option B:** Update .env files to match Bicep (remove -primary)
```
RESOURCE_GROUP=rg-bing-grounding-mcp-prod
```

**Option C:** Delete and recreate with new naming (destructive)

---

## Workflow Validation Summary

✅ **Step sequence is correct:**
1. Create .env files with actual Azure resource names
2. Sync to GitHub Environments
3. Run infra deployment
4. Run app deployment

❌ **Naming mismatch found:**
- Bicep generates: `rg-bing-grounding-mcp-prod-primary`
- Existing resources: `rg-bing-grounding-mcp-prod` (likely)
- Need to verify and align

✅ **Azure naming rules compliance:**
- All generated names use valid characters
- All within length limits
- GitHub Environment names (with underscores) NOT used in Azure resources

## Recommended Next Step

Run verification command:
```bash
az group list --query "[?contains(name, 'bing-grounding-mcp')].{Name:name, Location:location}" -o table
```

Then decide whether to:
- Update Bicep to match existing resources, OR
- Update .env files to match Bicep output
