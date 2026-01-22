# bootstrap-azure.ps1
# 
# One-time setup script for Bing Grounding MCP project
# Run this BEFORE your first GitHub Actions deployment
#
# Usage:
#   .\bootstrap-azure.ps1 `
#     -SubscriptionId "your-subscription-id" `
#     -GitHubRepoOwner "your-github-username" `
#     -GitHubRepoName "ai-bing-grounding-mcp-appservice"
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Permissions to create service principals in Azure AD
#   - Owner or User Access Administrator on the subscription

param(
    [Parameter(Mandatory=$true, HelpMessage="Azure Subscription ID")]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true, HelpMessage="GitHub repository owner (username or org)")]
    [string]$GitHubRepoOwner,
    
    [Parameter(Mandatory=$true, HelpMessage="GitHub repository name")]
    [string]$GitHubRepoName,
    
    [Parameter(HelpMessage="Service principal display name")]
    [string]$ServicePrincipalName = "sp-bing-grounding-mcp-cicd",
    
    [Parameter(HelpMessage="Skip provider registration")]
    [switch]$SkipProviderRegistration
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n$Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  ⚠️  $Message" -ForegroundColor DarkYellow
}

# Header
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       Bootstrap Azure for Bing Grounding MCP                  ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verify Azure CLI is logged in
Write-Step "0. Verifying Azure CLI login..."
try {
    $account = az account show | ConvertFrom-Json
    Write-Success "Logged in as: $($account.user.name)"
} catch {
    Write-Host "  ❌ Not logged in to Azure CLI. Run 'az login' first." -ForegroundColor Red
    exit 1
}

# Set subscription
Write-Step "1. Setting subscription..."
az account set --subscription $SubscriptionId
$subName = (az account show --query name -o tsv)
Write-Success "Using subscription: $subName ($SubscriptionId)"

# Check if service principal already exists
Write-Step "2. Creating Service Principal..."
$existingSp = az ad sp list --display-name $ServicePrincipalName --query "[0]" 2>$null | ConvertFrom-Json

if ($existingSp) {
    Write-Warning "Service principal '$ServicePrincipalName' already exists"
    $appId = $existingSp.appId
    $spObjectId = $existingSp.id
    $tenantId = (az account show --query tenantId -o tsv)
    Write-Info "App ID: $appId"
    Write-Info "Object ID: $spObjectId"
} else {
    $sp = az ad sp create-for-rbac --name $ServicePrincipalName --skip-assignment | ConvertFrom-Json
    $appId = $sp.appId
    $tenantId = $sp.tenant
    $spObjectId = az ad sp show --id $appId --query id -o tsv
    Write-Success "Created service principal"
    Write-Info "App ID: $appId"
    Write-Info "Tenant ID: $tenantId"
    Write-Info "SP Object ID: $spObjectId"
}

# Get App Object ID (for federated credentials)
$appObjectId = az ad app show --id $appId --query id -o tsv

# Create Federated Credentials
Write-Step "3. Creating Federated Credentials for OIDC..."

$credentials = @(
    @{
        name = "github-prod"
        subject = "repo:${GitHubRepoOwner}/${GitHubRepoName}:environment:prod"
        description = "Infrastructure deployment (prod environment)"
    },
    @{
        name = "github-production-primary"
        subject = "repo:${GitHubRepoOwner}/${GitHubRepoName}:environment:production-primary"
        description = "Primary region app deployment"
    },
    @{
        name = "github-production-secondary"
        subject = "repo:${GitHubRepoOwner}/${GitHubRepoName}:environment:production-secondary"
        description = "Secondary region app deployment"
    },
    @{
        name = "github-main-branch"
        subject = "repo:${GitHubRepoOwner}/${GitHubRepoName}:ref:refs/heads/main"
        description = "Main branch push triggers"
    }
)

foreach ($cred in $credentials) {
    # Check if credential already exists
    $existing = az ad app federated-credential list --id $appObjectId --query "[?name=='$($cred.name)']" 2>$null | ConvertFrom-Json
    
    if ($existing -and $existing.Count -gt 0) {
        Write-Warning "Credential '$($cred.name)' already exists - skipping"
    } else {
        $credJson = @{
            name = $cred.name
            issuer = "https://token.actions.githubusercontent.com"
            subject = $cred.subject
            audiences = @("api://AzureADTokenExchange")
            description = $cred.description
        } | ConvertTo-Json -Compress
        
        az ad app federated-credential create --id $appObjectId --parameters $credJson 2>$null | Out-Null
        Write-Success "Created: $($cred.name) ($($cred.description))"
    }
}

# Assign Subscription Roles
Write-Step "4. Assigning Subscription-Level Roles..."

$roles = @(
    @{ name = "Contributor"; purpose = "Create and manage resources" },
    @{ name = "User Access Administrator"; purpose = "Assign roles to resources" }
)

foreach ($role in $roles) {
    # Check if role is already assigned
    $existing = az role assignment list `
        --assignee $spObjectId `
        --role $role.name `
        --scope "/subscriptions/$SubscriptionId" `
        --query "[0]" 2>$null | ConvertFrom-Json
    
    if ($existing) {
        Write-Warning "$($role.name) already assigned - skipping"
    } else {
        az role assignment create `
            --role $role.name `
            --assignee-object-id $spObjectId `
            --assignee-principal-type ServicePrincipal `
            --scope "/subscriptions/$SubscriptionId" 2>$null | Out-Null
        Write-Success "$($role.name) - $($role.purpose)"
    }
}

# Register Resource Providers
if (-not $SkipProviderRegistration) {
    Write-Step "5. Registering Resource Providers..."
    
    $providers = @(
        @{ namespace = "Microsoft.CognitiveServices"; purpose = "AI Foundry, Azure OpenAI" },
        @{ namespace = "Microsoft.Bing"; purpose = "Bing Grounding resources" },
        @{ namespace = "Microsoft.Web"; purpose = "App Service" },
        @{ namespace = "Microsoft.Storage"; purpose = "Storage accounts" },
        @{ namespace = "Microsoft.ManagedIdentity"; purpose = "Managed identities" }
    )
    
    foreach ($provider in $providers) {
        $state = az provider show --namespace $provider.namespace --query registrationState -o tsv 2>$null
        if ($state -eq "Registered") {
            Write-Warning "$($provider.namespace) already registered"
        } else {
            az provider register --namespace $provider.namespace 2>$null | Out-Null
            Write-Success "$($provider.namespace) - $($provider.purpose)"
        }
    }
    
    Write-Info "Provider registration may take a few minutes to complete"
} else {
    Write-Step "5. Skipping Resource Provider Registration (--SkipProviderRegistration)"
}

# Output GitHub Configuration
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  GitHub Configuration                         ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "1. Add these SECRETS to your GitHub repository:" -ForegroundColor White
Write-Host "   (Settings → Secrets and variables → Actions → New repository secret)" -ForegroundColor Gray
Write-Host ""
Write-Host "   AZURE_CLIENT_ID:       $appId" -ForegroundColor Cyan
Write-Host "   AZURE_TENANT_ID:       $tenantId" -ForegroundColor Cyan
Write-Host "   AZURE_SUBSCRIPTION_ID: $SubscriptionId" -ForegroundColor Cyan
Write-Host ""

Write-Host "2. Add these VARIABLES to your GitHub repository:" -ForegroundColor White
Write-Host "   (Settings → Secrets and variables → Actions → Variables → New repository variable)" -ForegroundColor Gray
Write-Host ""
Write-Host "   AZURE_LOCATION_PRIMARY:   eastus2       (or your preferred region)" -ForegroundColor Cyan
Write-Host "   AZURE_LOCATION_SECONDARY: westus2       (optional, for multi-region)" -ForegroundColor Cyan
Write-Host ""

Write-Host "3. Create these ENVIRONMENTS in your GitHub repository:" -ForegroundColor White
Write-Host "   (Settings → Environments → New environment)" -ForegroundColor Gray
Write-Host ""
Write-Host "   • prod                 - Infrastructure deployment" -ForegroundColor Cyan
Write-Host "   • production-primary   - Primary region app deployment" -ForegroundColor Cyan
Write-Host "   • production-secondary - Secondary region app deployment" -ForegroundColor Cyan
Write-Host ""

Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Bootstrap Complete!                        ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Configure GitHub secrets and variables as shown above"
Write-Host "  2. Create GitHub environments"
Write-Host "  3. Run the 'Deploy Infrastructure' workflow"
Write-Host "  4. Run the 'Deploy to Azure App Service' workflow"
Write-Host ""
