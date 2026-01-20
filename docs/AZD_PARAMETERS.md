# Azure Developer CLI Parameter Configuration

## Problem Solved

When running `azd provision` or `azd up`, azd was repeatedly prompting for the `location` parameter, even though it was stored in `.azure/dev/config.json`. This made deployment frustrating and blocked automation.

## Root Cause

Azure Developer CLI (azd) requires parameters to be **explicitly mapped** from environment variables to Bicep parameters using a `main.parameters.json` file. Simply having the parameters in `.azure/dev/config.json` or setting personal defaults with `azd config set` is not sufficient.

## Solution

Created `infra/main.parameters.json` to map environment variables to Bicep parameters:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName": {
      "value": "${AZURE_ENV_NAME}"
    },
    "location": {
      "value": "${AZURE_LOCATION}"
    }
  }
}
```

## How It Works

1. **First Run**: When you run `azd up` or `azd provision`, azd prompts for:
   - Environment name (e.g., `dev`, `prod`)
   - Azure location (e.g., `eastus2`)
   - Azure subscription (if multiple available)

2. **Storage**: azd stores these values in `.azure/<env-name>/.env`:
   ```
   AZURE_ENV_NAME=dev
   AZURE_LOCATION=eastus2
   AZURE_SUBSCRIPTION_ID=...
   ```

3. **Substitution**: During provisioning, azd:
   - Reads `infra/main.parameters.json`
   - Substitutes `${AZURE_ENV_NAME}` → `"dev"`
   - Substitutes `${AZURE_LOCATION}` → `"eastus2"`
   - Passes these resolved values to Bicep as parameters

4. **Future Runs**: azd automatically uses the stored values from `.azure/<env-name>/.env` without prompting again

## Why This Approach Works for Teams

✅ **No personal configuration required** - no `azd config set` needed  
✅ **Works for any developer** - just run `azd up` and answer prompts once  
✅ **Environment-specific** - different developers can use different environments (`dev`, `staging`, `prod`)  
✅ **Git-friendly** - `main.parameters.json` is committed, `.azure/` folder is excluded  
✅ **Repeatable** - same process works for everyone on the team  

## What NOT To Do

❌ **Don't set personal defaults**: `azd config set defaults.location eastus2`  
   - This only works for your machine  
   - Other developers won't have these defaults  
   - Not suitable for team repositories  

❌ **Don't commit `.azure/` folder**  
   - Contains environment-specific data  
   - Each developer should have their own  
   - Already excluded in `.gitignore`  

❌ **Don't rely on `.azure/dev/config.json` alone**  
   - This file stores parameters but doesn't map them to Bicep  
   - You need `main.parameters.json` for the mapping  

## Standard azd Environment Variables

azd automatically manages these standard variables:

| Variable | Description | Set During |
|----------|-------------|------------|
| `AZURE_ENV_NAME` | Environment name (dev, prod, etc.) | `azd init` or `azd up` |
| `AZURE_LOCATION` | Azure region for resources | First `azd provision` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | First `azd provision` |
| `AZURE_RESOURCE_GROUP` | Resource group name | `azd provision` |
| `AZURE_PRINCIPAL_ID` | User/service principal ID | `azd provision` |
| `AZURE_TENANT_ID` | Azure tenant ID | `azd provision` |

## Multiple Environments

Each developer or environment can have its own configuration:

```bash
# Developer 1: Create 'dev' environment
azd env new dev
azd up  # Prompts for location → saves to .azure/dev/.env

# Developer 2: Create 'staging' environment
azd env new staging
azd up  # Prompts for location → saves to .azure/staging/.env

# Developer 3: Create 'prod' environment
azd env new prod
azd up  # Prompts for location → saves to .azure/prod/.env
```

Each environment maintains its own `.env` file with independent configurations.

## CI/CD Considerations

For GitHub Actions or Azure DevOps pipelines:

1. **Set environment variables in pipeline**:
   ```yaml
   env:
     AZURE_ENV_NAME: prod
     AZURE_LOCATION: eastus2
     AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
   ```

2. **azd automatically uses these** for parameter substitution

3. **No manual prompts** - all values provided via environment variables

## References

- [Azure Developer CLI Environment Variables](https://learn.microsoft.com/azure/developer/azure-developer-cli/manage-environment-variables)
- [Azure Developer CLI azure.yaml Schema](https://learn.microsoft.com/azure/developer/azure-developer-cli/azd-schema)
- [Work with Environments in azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/work-with-environments)
