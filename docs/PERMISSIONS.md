# Permissions Guide

This document describes all permissions required for the Bing Grounding MCP project, separated into:
1. **Manual (Bootstrap)** - One-time setup before workflows can run
2. **Automated (Workflow)** - Managed by GitHub Actions workflows

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MANUAL SETUP                                 │
│  (Run once before first deployment)                                  │
├─────────────────────────────────────────────────────────────────────┤
│  1. Create Service Principal                                         │
│  2. Configure Federated Credentials (OIDC)                          │
│  3. Assign Subscription-Level Roles                                  │
│  4. Configure GitHub Secrets/Variables                               │
│  5. Register Required Resource Providers                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AUTOMATED (WORKFLOW)                            │
│  (Managed by deploy-infra.yml)                                       │
├─────────────────────────────────────────────────────────────────────┤
│  1. Create Resource Groups                                           │
│  2. Deploy AI Foundry + Project                                      │
│  3. Deploy App Service                                               │
│  4. Create Bing Grounding Resources                                  │
│  5. Assign Resource-Level Roles to Service Principal                 │
│     - Azure AI Developer (AI Foundry + Project)                      │
│     - Cognitive Services User (AI Foundry)                           │
│  6. Deploy Model Configurations                                      │
│  7. Create Bing Connections                                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AUTOMATED (WORKFLOW)                            │
│  (Managed by deploy.yml)                                             │
├─────────────────────────────────────────────────────────────────────┤
│  1. Deploy Application Code                                          │
│  2. Create AI Agents with Bing Grounding                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Manual Setup (Bootstrap)

These steps must be completed **once** before running any GitHub Actions workflows.

### 1.1 Create Service Principal

```powershell
# Create service principal (no credentials - we'll use OIDC)
$sp = az ad sp create-for-rbac `
  --name "sp-bing-grounding-mcp-cicd" `
  --skip-assignment `
  --only-show-errors | ConvertFrom-Json

# Save these values - you'll need them for GitHub secrets
Write-Host "CLIENT_ID (App ID): $($sp.appId)"
Write-Host "TENANT_ID: $($sp.tenant)"

# Get the Object ID (needed for role assignments)
$spObjectId = az ad sp show --id $sp.appId --query id -o tsv
Write-Host "OBJECT_ID: $spObjectId"
```

### 1.2 Configure Federated Credentials (OIDC)

OIDC allows GitHub Actions to authenticate without storing secrets.

```powershell
$appId = "<your-app-id>"  # From step 1.1
$repoOwner = "your-github-username"
$repoName = "ai-bing-grounding-mcp-appservice"

# Get the App's Object ID (different from SP Object ID)
$appObjectId = az ad app show --id $appId --query id -o tsv

# Create federated credential for production-primary environment
$credentialPrimary = @{
    name = "github-actions-primary"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:${repoOwner}/${repoName}:environment:production-primary"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json

az ad app federated-credential create --id $appObjectId --parameters $credentialPrimary

# Create federated credential for production-secondary environment
$credentialSecondary = @{
    name = "github-actions-secondary"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:${repoOwner}/${repoName}:environment:production-secondary"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json

az ad app federated-credential create --id $appObjectId --parameters $credentialSecondary

# Create federated credential for prod environment (infrastructure)
$credentialProd = @{
    name = "github-actions-prod"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:${repoOwner}/${repoName}:environment:prod"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json

az ad app federated-credential create --id $appObjectId --parameters $credentialProd

# Create federated credential for main branch (for push triggers)
$credentialMain = @{
    name = "github-actions-main"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:${repoOwner}/${repoName}:ref:refs/heads/main"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json

az ad app federated-credential create --id $appObjectId --parameters $credentialMain
```

### 1.3 Assign Subscription-Level Roles

The service principal needs these roles at the **subscription** level to create and manage resources:

```powershell
$subscriptionId = "<your-subscription-id>"
$spObjectId = "<sp-object-id>"  # From step 1.1

# Contributor - Create/manage resources
az role assignment create `
  --role "Contributor" `
  --assignee-object-id $spObjectId `
  --assignee-principal-type ServicePrincipal `
  --scope "/subscriptions/$subscriptionId"

# User Access Administrator - Assign roles to resources
# Required so the workflow can assign AI Developer role to itself
az role assignment create `
  --role "User Access Administrator" `
  --assignee-object-id $spObjectId `
  --assignee-principal-type ServicePrincipal `
  --scope "/subscriptions/$subscriptionId"
```

### 1.4 Register Required Resource Providers

```powershell
# Register providers (some may take a few minutes)
az provider register --namespace Microsoft.CognitiveServices --wait
az provider register --namespace Microsoft.Bing --wait
az provider register --namespace Microsoft.Web --wait
az provider register --namespace Microsoft.Storage --wait
az provider register --namespace Microsoft.ManagedIdentity --wait
```

### 1.5 Configure GitHub Repository

#### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AZURE_CLIENT_ID` | `<app-id>` | Service principal App ID |
| `AZURE_TENANT_ID` | `<tenant-id>` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `<subscription-id>` | Azure subscription ID |

#### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `AZURE_LOCATION_PRIMARY` | `eastus2` | Primary region |
| `AZURE_LOCATION_SECONDARY` | `westus2` | Secondary region (optional) |

#### Environments (Settings → Environments)

Create these environments for deployment protection:

1. **prod** - For infrastructure deployment
2. **production-primary** - For primary region app deployment
3. **production-secondary** - For secondary region app deployment

For each environment, you can optionally configure:
- Required reviewers
- Wait timer
- Deployment branches (restrict to `main`)

---

## Part 2: Automated Permissions (Workflow-Managed)

These permissions are automatically assigned by `deploy-infra.yml` during infrastructure provisioning.

### 2.1 Resource-Level Role Assignments

The workflow assigns these roles to the service principal on specific resources:

| Role | Scope | Purpose |
|------|-------|---------|
| `Azure AI Developer` | AI Foundry Account | Agents API: create, read, update, delete agents |
| `Azure AI Developer` | AI Project | Agents API: project-scoped operations |
| `Cognitive Services User` | AI Foundry Account | Model deployments and inference |

**Why these roles?**

- **Azure AI Developer**: Contains data plane actions for the Agents API:
  - `Microsoft.CognitiveServices/accounts/AIServices/agents/read`
  - `Microsoft.CognitiveServices/accounts/AIServices/agents/write`
  - `Microsoft.CognitiveServices/accounts/AIServices/threads/*`
  - `Microsoft.CognitiveServices/accounts/AIServices/runs/*`

- **Cognitive Services User**: Required for:
  - Calling deployed models
  - Managing model deployments

### 2.2 Where Permissions Are Assigned in Workflows

**File: `.github/workflows/deploy-infra.yml`**

```yaml
- name: Configure service principal permissions
  run: |
    # Assigns Azure AI Developer and Cognitive Services User roles
    # to AI Foundry and Project resources in both regions
```

This step runs after infrastructure provisioning and ensures the service principal
can create agents in the subsequent deploy workflow.

---

## Part 3: Permission Summary Table

| Permission | Level | Assigned By | Required For |
|------------|-------|-------------|--------------|
| **Contributor** | Subscription | Manual | Create resource groups, resources |
| **User Access Administrator** | Subscription | Manual | Assign roles to resources |
| **Azure AI Developer** | AI Foundry | Workflow | Agents API access |
| **Azure AI Developer** | AI Project | Workflow | Agents API access |
| **Cognitive Services User** | AI Foundry | Workflow | Model access |

---

## Part 4: Troubleshooting

### Error: "does not have authorization to perform action"

**Cause**: Missing subscription-level role (Contributor or User Access Administrator)

**Fix**: Run the commands in section 1.3

### Error: "lacks the required data action Microsoft.CognitiveServices/accounts/AIServices/agents/write"

**Cause**: Missing Azure AI Developer role on AI Foundry/Project

**Fix**: 
1. Run `deploy-infra.yml` workflow (it will assign the role)
2. Or manually assign:
   ```bash
   az role assignment create \
     --role "Azure AI Developer" \
     --assignee-object-id "<sp-object-id>" \
     --assignee-principal-type ServicePrincipal \
     --scope "<ai-foundry-resource-id>"
   ```

### Error: "AADSTS700024: Client assertion is not within its valid time range"

**Cause**: Federated credential subject claim doesn't match

**Fix**: Ensure federated credentials match exactly:
- Check environment name matches GitHub environment
- Check branch name for ref-based credentials

### Error: "AuthorizationFailed" when creating Bing resource

**Cause**: Microsoft.Bing provider not registered

**Fix**: 
```bash
az provider register --namespace Microsoft.Bing --wait
```

---

## Part 5: Complete Bootstrap Script

Run this script once to set up everything:

```powershell
# bootstrap-azure.ps1
# Run this ONCE before first deployment

param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubRepoOwner,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubRepoName,
    
    [string]$ServicePrincipalName = "sp-bing-grounding-mcp-cicd"
)

Write-Host "=== Bootstrap Azure for Bing Grounding MCP ===" -ForegroundColor Cyan

# Set subscription
az account set --subscription $SubscriptionId

# 1. Create Service Principal
Write-Host "`n1. Creating Service Principal..." -ForegroundColor Yellow
$sp = az ad sp create-for-rbac --name $ServicePrincipalName --skip-assignment | ConvertFrom-Json
$appId = $sp.appId
$tenantId = $sp.tenant
$spObjectId = az ad sp show --id $appId --query id -o tsv
$appObjectId = az ad app show --id $appId --query id -o tsv

Write-Host "   App ID: $appId"
Write-Host "   Tenant ID: $tenantId"
Write-Host "   SP Object ID: $spObjectId"

# 2. Create Federated Credentials
Write-Host "`n2. Creating Federated Credentials..." -ForegroundColor Yellow

$environments = @("prod", "production-primary", "production-secondary")
foreach ($env in $environments) {
    $cred = @{
        name = "github-$env"
        issuer = "https://token.actions.githubusercontent.com"
        subject = "repo:${GitHubRepoOwner}/${GitHubRepoName}:environment:$env"
        audiences = @("api://AzureADTokenExchange")
    } | ConvertTo-Json
    
    az ad app federated-credential create --id $appObjectId --parameters $cred 2>$null
    Write-Host "   Created credential for environment: $env"
}

# Main branch credential
$mainCred = @{
    name = "github-main-branch"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:${GitHubRepoOwner}/${GitHubRepoName}:ref:refs/heads/main"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json

az ad app federated-credential create --id $appObjectId --parameters $mainCred 2>$null
Write-Host "   Created credential for main branch"

# 3. Assign Subscription Roles
Write-Host "`n3. Assigning Subscription Roles..." -ForegroundColor Yellow

az role assignment create --role "Contributor" --assignee-object-id $spObjectId --assignee-principal-type ServicePrincipal --scope "/subscriptions/$SubscriptionId" 2>$null
Write-Host "   Assigned: Contributor"

az role assignment create --role "User Access Administrator" --assignee-object-id $spObjectId --assignee-principal-type ServicePrincipal --scope "/subscriptions/$SubscriptionId" 2>$null
Write-Host "   Assigned: User Access Administrator"

# 4. Register Providers
Write-Host "`n4. Registering Resource Providers..." -ForegroundColor Yellow
$providers = @("Microsoft.CognitiveServices", "Microsoft.Bing", "Microsoft.Web", "Microsoft.Storage", "Microsoft.ManagedIdentity")
foreach ($provider in $providers) {
    az provider register --namespace $provider 2>$null
    Write-Host "   Registered: $provider"
}

# 5. Output GitHub Configuration
Write-Host "`n=== GitHub Configuration ===" -ForegroundColor Green
Write-Host "Add these SECRETS to your GitHub repository:"
Write-Host "  AZURE_CLIENT_ID: $appId"
Write-Host "  AZURE_TENANT_ID: $tenantId"
Write-Host "  AZURE_SUBSCRIPTION_ID: $SubscriptionId"
Write-Host ""
Write-Host "Add these VARIABLES to your GitHub repository:"
Write-Host "  AZURE_LOCATION_PRIMARY: eastus2"
Write-Host "  AZURE_LOCATION_SECONDARY: westus2"
Write-Host ""
Write-Host "Create these ENVIRONMENTS in GitHub:"
Write-Host "  - prod"
Write-Host "  - production-primary"
Write-Host "  - production-secondary"
Write-Host ""
Write-Host "=== Bootstrap Complete ===" -ForegroundColor Green
```

**Usage:**
```powershell
.\bootstrap-azure.ps1 `
  -SubscriptionId "your-subscription-id" `
  -GitHubRepoOwner "your-github-username" `
  -GitHubRepoName "ai-bing-grounding-mcp-appservice"
```

---

## Quick Reference

### What to do manually (once):
1. ✅ Create service principal
2. ✅ Create federated credentials for OIDC
3. ✅ Assign Contributor role (subscription)
4. ✅ Assign User Access Administrator role (subscription)
5. ✅ Register resource providers
6. ✅ Configure GitHub secrets/variables/environments

### What the workflow does automatically:
1. ✅ Create resource groups
2. ✅ Deploy all Azure resources (AI Foundry, App Service, etc.)
3. ✅ Create Bing Grounding resources
4. ✅ Assign Azure AI Developer role (AI Foundry + Project)
5. ✅ Assign Cognitive Services User role (AI Foundry)
6. ✅ Deploy models and create Bing connections
7. ✅ Create AI agents with Bing Grounding tool
