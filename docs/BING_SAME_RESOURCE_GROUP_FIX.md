# Bing Grounding Same-Resource-Group Requirement Fix

## Problem

Agents were failing with error:
```
Error: missing_required_parameter: AML connections are required for Bing Grounding tool
RunId: run_3TRCnWkThnxAQo25CM86Pc4B
```

## Root Cause

Per [Microsoft documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding):

> "Make sure you create this Grounding with Bing Search resource in the **same resource group** as your Azure AI Agent, AI Project, and other resources"

The Bing Grounding resource MUST be in the **same resource group** as the AI Foundry project. When they are in different resource groups, the automatic connection does not work, causing the error above.

### Previous State
- Bing resource: `bing_grounding` in resource group `bing_grounding_rg`
- AI Project: in resource group `rg-bing-grounding-mcp-dev5`
- Result: ❌ Connection failed

### Required State
- Bing resource: in resource group `rg-bing-grounding-mcp-{env}`
- AI Project: in resource group `rg-bing-grounding-mcp-{env}`
- Result: ✅ Automatic connection works

## Solution

### 1. Updated `preprovision_select_bing_resource.py`

**Changes:**
- Added `target_resource_group` parameter to `list_bing_resources()` function
- Filters Bing resources to only show those in the target deployment resource group
- Reads `AZURE_RESOURCE_GROUP` from environment to determine target
- If no Bing resource found in target RG, shows clear instructions to create one
- Added defensive validation after selection to ensure correct RG

**Key Code:**
```python
def list_bing_resources(subscription_id: str, target_resource_group: str = None) -> list[dict]:
    # ... existing code ...
    
    # Filter to target resource group if specified
    if target_resource_group and all_resources:
        filtered = [r for r in all_resources if r.get('resourceGroup') == target_resource_group]
        return filtered
    
    return all_resources
```

**User Experience:**
```
[INFO] Target Resource Group: rg-bing-grounding-mcp-prod
[IMPORTANT] Per Microsoft documentation, the Bing Grounding resource
            MUST be in the SAME resource group as your AI project.
            Only showing resources in: rg-bing-grounding-mcp-prod

[1/2] Searching for Bing Grounding resources...
```

If no Bing resource in correct RG:
```
NO BING GROUNDING RESOURCE FOUND IN TARGET RESOURCE GROUP

IMPORTANT: The Bing resource MUST be in the SAME resource group
           as your AI Foundry project for automatic connection.

To create one:
1. Open: https://portal.azure.com/#create/Microsoft.BingGroundingSearch
2. Subscription: {subscription_id}
3. Resource Group: {target_resource_group}  ← MUST USE THIS
4. Name: Choose a unique name (e.g., 'bing-grounding-prod')
5. Pricing Tier: F0 (Free - 1,000 transactions/month)
6. Click 'Review + Create' -> 'Create' (takes ~1 minute)

After creation, run 'azd up' again.
```

### 2. Updated `postprovision_create_bing_connection.py`

**Changes:**
- Removed all connection creation logic (not needed per Microsoft docs)
- Changed to verification script that checks resource group match
- Returns error if Bing resource is in different RG
- Provides clear fix instructions if validation fails

**Key Code:**
```python
# Verify same resource group
if bing_resource_group != resource_group:
    print("❌ ERROR: RESOURCE GROUP MISMATCH")
    print(f"  AI Project RG: {resource_group}")
    print(f"  Bing Resource RG: {bing_resource_group}")
    print("The connection will NOT work with this configuration!")
    return 1

print("✅ VERIFICATION PASSED")
print("Bing resource is in same resource group - connection will be automatic")
```

## How Connection Works

Per Microsoft documentation, **no explicit connection creation is needed** when the Bing resource is in the same resource group as the AI project.

### Automatic Connection Flow
1. Bing resource created in same RG as AI project
2. Agent created with `BingGroundingToolDefinition`:
   ```python
   bing_tool = BingGroundingToolDefinition(
       bing_grounding=BingGroundingSearchToolParameters(
           search_configurations=[
               BingGroundingSearchConfiguration(
                   connection_id=f"{project_resource_id}/connections/default-bing"
               )
           ]
       )
   )
   ```
3. Azure AI automatically creates connection (no manual step needed)
4. Agent can use Bing grounding immediately

## Testing the Fix

### Test Environment Cleanup
```bash
# Delete current environment (has Bing in wrong RG)
azd env delete dev5 --purge

# Create fresh environment
azd env new prod
```

### Test Deployment

1. **Run deployment:**
   ```bash
   azd up
   ```

2. **Preprovision will:**
   - Check for Bing resources in `rg-bing-grounding-mcp-prod`
   - If none exist, stop with instructions to create one
   - If one exists, validate it's in correct RG

3. **Postprovision will:**
   - Verify Bing resource is in same RG as AI project
   - Error if resource groups don't match
   - Confirm automatic connection is ready

4. **Test agent:**
   ```python
   from azure.ai.projects import AIProjectClient
   from azure.identity import DefaultAzureCredential
   
   # Create client
   client = AIProjectClient.from_connection_string(
       conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"],
       credential=DefaultAzureCredential()
   )
   
   # Get agent (already created by deployment)
   agents = client.agents.list_agents()
   agent = next(a for a in agents.value if "bing" in a.name.lower())
   
   # Create thread and test Bing search
   thread = client.agents.create_thread()
   message = client.agents.create_message(
       thread_id=thread.id,
       role="user",
       content="What's the latest news about GitHub Copilot?"
   )
   
   # Run agent
   run = client.agents.create_and_process_run(
       thread_id=thread.id,
       assistant_id=agent.id
   )
   
   # Should work without "missing_required_parameter" error
   assert run.status == "completed"
   ```

## Validation Checklist

- [x] Preprovision filters Bing resources to target RG only
- [x] Preprovision shows clear instructions if no Bing in target RG
- [x] Preprovision validates selected Bing is in correct RG
- [x] Postprovision verifies RG match before continuing
- [x] Postprovision provides fix instructions if RG mismatch
- [x] Documentation references Microsoft official docs
- [x] No manual connection creation needed

## References

- **Microsoft Documentation:** https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding
- **Key Quote:** "Make sure you create this Grounding with Bing Search resource in the same resource group as your Azure AI Agent, AI Project, and other resources"
- **Resource Type:** `Microsoft.Bing/accounts`
- **Resource Kind:** `Bing.Grounding`
- **SKU:** `G1` (Free tier - 1,000 transactions/month)

## Migration Guide for Existing Deployments

If you already have a deployment with Bing in the wrong resource group:

### Option 1: Create New Bing Resource (Recommended)

1. **Create Bing resource in correct RG:**
   ```bash
   # Get your current resource group
   azd env get-values | findstr AZURE_RESOURCE_GROUP
   
   # Create Bing resource in that RG
   # Open: https://portal.azure.com/#create/Microsoft.BingGroundingSearch
   # Use the resource group from above
   ```

2. **Update environment:**
   ```bash
   # Clear old Bing variables
   azd env set BING_GROUNDING_RESOURCE_ID ""
   azd env set BING_GROUNDING_RESOURCE_NAME ""
   azd env set BING_GROUNDING_RESOURCE_GROUP ""
   
   # Re-run deployment
   azd up
   # Script will prompt to select new Bing resource
   ```

### Option 2: Fresh Deployment

```bash
# Delete current environment
azd env delete {env-name} --purge

# Create new environment
azd env new {new-env-name}

# Deploy (will prompt for Bing resource in correct RG)
azd up
```

## Troubleshooting

### Error: "missing_required_parameter: AML connections are required"

**Cause:** Bing resource is in different resource group than AI project

**Fix:**
1. Check resource groups:
   ```bash
   azd env get-values | findstr RESOURCE_GROUP
   ```
2. Verify Bing RG matches AI project RG
3. If different, create new Bing resource in correct RG (see Migration Guide)

### Error: "NO BING GROUNDING RESOURCE FOUND IN TARGET RESOURCE GROUP"

**Cause:** No Bing resource exists in the deployment's target resource group

**Fix:**
1. Follow instructions in error message
2. Create Bing resource in specified resource group
3. Run `azd up` again

### Preprovision selects Bing but postprovision fails validation

**Cause:** Bug in preprovision filtering (shouldn't happen with fix)

**Fix:**
1. Report as bug
2. Manually verify Bing resource RG matches deployment RG
3. Create new Bing in correct RG if needed
