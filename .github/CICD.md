# GitHub Actions CI/CD Setup

This repository includes a GitHub Actions workflow that automatically builds and deploys the Bing Grounding API to Azure Container Apps.

## Workflow Overview

The workflow (`build-deploy.yml`) runs on:
- **Push to `main` branch** - Builds image and deploys to production
- **Pull requests** - Builds image only (no deployment)
- **Manual trigger** - Via GitHub Actions UI

### Jobs

1. **Build Job**
   - Builds Docker image
   - Pushes to Azure Container Registry
   - Tags with branch name, commit SHA, and `latest`
   - Uses Docker layer caching for faster builds

2. **Deploy Job** (only on push to `main`)
   - Logs into Azure
   - Finds all Container App instances
   - Updates each instance with new image
   - Verifies health endpoints
   - Creates deployment summary

## Setup Instructions

### 1. Configure Azure Authentication

Create a service principal with permissions to push to ACR and manage Container Apps:

```bash
az ad sp create-for-rbac --name "github-actions-bing-grounding" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>
```

This returns:
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "github-actions-bing-grounding",
  "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 2. Add GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add the following secrets:

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `AZURE_CLIENT_ID` | Service Principal App ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CONTAINER_REGISTRY` | ACR login server | `acrabc123.azurecr.io` |
| `ACR_USERNAME` | ACR admin username | `acrabc123` |
| `ACR_PASSWORD` | ACR admin password | `xxxxxxxxxxxxxxxxxxxxx` |
| `AZURE_RESOURCE_GROUP` | Resource group name | `rg-bing-grounding` |
| `AZURE_CONTAINER_APP_PREFIX` | Container App name prefix | `ca-abc123` |

### 3. Get Required Values

**ACR Credentials:**
```bash
# Get ACR login server
az acr show --name <acr-name> --query loginServer -o tsv

# Get ACR admin credentials
az acr credential show --name <acr-name>
```

**Azure IDs:**
```bash
# Get subscription ID
az account show --query id -o tsv

# Get tenant ID
az account show --query tenantId -o tsv
```

**Container App Details:**
```bash
# List container apps
az containerapp list --resource-group <rg-name> --query "[].name" -o tsv

# Get the common prefix (e.g., "ca-abc123")
```

### 4. Configure Federated Identity (Alternative to Service Principal Password)

For better security, use workload identity federation instead of passwords:

```bash
# Get your repository details
REPO_OWNER="your-github-username"
REPO_NAME="ai-bing-grounding-mcp"
APP_ID="<service-principal-app-id>"

# Create federated credential for main branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters "{
    \"name\": \"github-deploy-main\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$REPO_OWNER/$REPO_NAME:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
```

If using federated identity, you can remove `ACR_PASSWORD` and use Azure login action with OIDC.

## Usage

### Automatic Deployment

1. **Make code changes** and commit to a feature branch
2. **Create a pull request** → Workflow builds image (no deployment)
3. **Merge to `main`** → Workflow builds and deploys automatically
4. **Check deployment status** in GitHub Actions tab

### Manual Deployment

1. Go to **Actions** tab in GitHub
2. Select **Build and Deploy** workflow
3. Click **Run workflow**
4. Select branch and click **Run workflow**

### Monitoring

After deployment:
- View workflow run details in **Actions** tab
- Check deployment summary in the workflow output
- View Container App logs in Azure Portal
- Test endpoints using the deployed URLs

## Workflow Features

✅ **Docker Layer Caching** - Faster builds using registry cache
✅ **Multi-tagging** - Images tagged with SHA, branch, and latest
✅ **Rolling Updates** - Each Container App instance updated sequentially
✅ **Health Checks** - Verifies endpoints after deployment
✅ **Deployment Summary** - Clear summary in GitHub Actions UI
✅ **Pull Request Builds** - Test builds without deploying

## Troubleshooting

**Build fails with "permission denied":**
- Verify ACR credentials in GitHub Secrets
- Ensure service principal has `AcrPush` role on ACR

**Deploy fails with "authentication failed":**
- Verify `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- Ensure service principal has `Contributor` role on resource group

**Health check fails after deployment:**
- Check Container App logs in Azure Portal
- Verify `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_AI_AGENT_ID` are set
- Ensure managed identity has access to AI Project

**Deployment is slow:**
- Docker layer caching should speed up subsequent builds
- Consider using more powerful GitHub-hosted runners
- Optimize Dockerfile with multi-stage builds

## Next Steps

- Add staging environment deployment
- Implement blue-green deployments
- Add integration tests to workflow
- Set up automated rollback on failure
- Configure deployment approvals for production
