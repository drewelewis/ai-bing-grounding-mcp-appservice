# GitHub Actions CI/CD Setup

This repository includes a GitHub Actions workflow that automatically builds and deploys the Bing Grounding API to Azure Container Apps.

## Workflow Overview

The workflow (`deploy.yml`) runs on:
- **Push to main** - Builds and deploys automatically
- **Pull requests** - Builds only (no deployment)
- **Manual trigger** - Via GitHub Actions UI

### Jobs

1. **Build** - Builds Docker image and pushes to Azure Container Registry
2. **Deploy** - Updates all Container App instances with the new image (main branch only)

## Setup Instructions

### 1. Create Azure Service Principal for GitHub Actions

```bash
# Create service principal with contributor access
az ad sp create-for-rbac \
  --name "github-actions-bing-grounding" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group-name> \
  --sdk-auth
```

Save the JSON output - you'll need it for GitHub secrets.

### 2. Get Azure Container Registry Credentials

```bash
# Get ACR login server
az acr show --name <acr-name> --query loginServer -o tsv

# Get ACR admin credentials
az acr credential show --name <acr-name>
```

### 3. Configure GitHub Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `AZURE_CLIENT_ID` | Service principal app ID | From step 1 JSON output: `clientId` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | From step 1 JSON output: `tenantId` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | From step 1 JSON output: `subscriptionId` |
| `AZURE_CONTAINER_REGISTRY` | ACR login server | From step 2: e.g., `acrabc123.azurecr.io` |
| `ACR_USERNAME` | ACR admin username | From step 2 `az acr credential` output |
| `ACR_PASSWORD` | ACR admin password | From step 2 `az acr credential` output |
| `AZURE_RESOURCE_GROUP` | Resource group name | Your Azure resource group name |
| `AZURE_CONTAINER_APP_NAME` | Container App base name | Base name without instance suffix, e.g., `ca-abc123` |

### 4. Enable Federated Identity (Optional - More Secure)

For better security, use workload identity federation instead of storing service principal secrets:

```bash
# Create federated credential for GitHub Actions
az ad app federated-credential create \
  --id <app-id> \
  --parameters '{
    "name": "github-actions-federated",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<your-org>/<your-repo>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

Then remove `ACR_USERNAME` and `ACR_PASSWORD` secrets and update the workflow to use managed identity for ACR access.

### 5. Test the Workflow

1. **Push to a feature branch** - Creates a PR, workflow builds but doesn't deploy
2. **Merge to main** - Workflow builds and deploys to all 3 Container App instances
3. **Manual trigger** - Go to Actions tab → Select workflow → Run workflow

## Workflow Features

✅ **Docker layer caching** - Faster builds using registry cache
✅ **Multi-tag images** - Tags with both `latest` and commit SHA
✅ **Zero-downtime deployment** - Updates instances one at a time
✅ **PR safety** - Pull requests build but don't deploy
✅ **Manual trigger** - Deploy on-demand via GitHub UI

## Monitoring Deployments

### View Workflow Runs
Go to: Repository → Actions → Build and Deploy to Azure

### Check Container App Status
```bash
# Check revision status
az containerapp revision list \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --output table

# View logs
az containerapp logs show \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --follow
```

## Troubleshooting

**Build fails with "permission denied"**
- Verify ACR credentials in GitHub secrets
- Ensure service principal has `AcrPush` role on ACR

**Deploy fails with "Container App not found"**
- Check `AZURE_CONTAINER_APP_NAME` secret matches base name (without `-0`, `-1`, `-2`)
- Verify resource group name is correct

**Image not updating**
- Check if the workflow completed successfully
- Verify the image tag in ACR: `az acr repository show-tags --name <acr-name> --repository bing-grounding-api`
- Check Container App revision: may need to restart if using `latest` tag

**"Could not authenticate" errors**
- Regenerate service principal credentials
- Update GitHub secrets with new values
- Ensure subscription ID is correct

## Advanced: Custom Deployment Strategy

To customize the deployment (e.g., blue-green, canary), modify the deploy job in `.github/workflows/deploy.yml`:

```yaml
# Example: Deploy to one instance first, then others
- name: Deploy to canary instance
  run: |
    az containerapp update --name ${{ secrets.AZURE_CONTAINER_APP_NAME }}-0 ...
    
- name: Wait and verify
  run: sleep 60
  
- name: Deploy to remaining instances
  run: |
    az containerapp update --name ${{ secrets.AZURE_CONTAINER_APP_NAME }}-1 ...
    az containerapp update --name ${{ secrets.AZURE_CONTAINER_APP_NAME }}-2 ...
```
