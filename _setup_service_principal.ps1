# Setup Service Principal for Bing Grounding API
# This script creates a service principal and grants it access to your AI Project

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Service Principal Setup" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Check if logged in to Azure
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "ERROR: Not logged in to Azure" -ForegroundColor Red
    Write-Host "Please run: az login" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✓ Logged in to Azure" -ForegroundColor Green
Write-Host "  Subscription: $($account.name)" -ForegroundColor Gray
Write-Host "  Tenant: $($account.tenantId)" -ForegroundColor Gray
Write-Host ""

# Step 1: Create Service Principal
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Step 1: Create Service Principal" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Creating service principal 'bing-grounding-api-sp'..." -ForegroundColor Yellow
$spJson = az ad sp create-for-rbac --name "bing-grounding-api-sp" --role Contributor 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to create service principal" -ForegroundColor Red
    Write-Host $spJson -ForegroundColor Red
    Write-Host ""
    Write-Host "Note: If the service principal already exists, delete it first with:" -ForegroundColor Yellow
    Write-Host "az ad sp delete --id `$(az ad sp list --display-name 'bing-grounding-api-sp' --query [0].appId -o tsv)" -ForegroundColor Yellow
    pause
    exit 1
}

# Parse the JSON output
$sp = $spJson | ConvertFrom-Json

Write-Host ""
Write-Host "✓ Service Principal Created Successfully!" -ForegroundColor Green
Write-Host ""

# Display credentials
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Credentials (copy to .env file):" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "AZURE_CLIENT_ID=$($sp.appId)" -ForegroundColor White
Write-Host "AZURE_CLIENT_SECRET=$($sp.password)" -ForegroundColor White
Write-Host "AZURE_TENANT_ID=$($sp.tenant)" -ForegroundColor White
Write-Host ""

# Copy to clipboard
$envVars = @"
AZURE_CLIENT_ID=$($sp.appId)
AZURE_CLIENT_SECRET=$($sp.password)
AZURE_TENANT_ID=$($sp.tenant)
"@

try {
    $envVars | Set-Clipboard
    Write-Host "✓ Credentials copied to clipboard!" -ForegroundColor Green
} catch {
    Write-Host "⚠ Could not copy to clipboard" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ""

# Step 2: Grant Access to AI Project
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Step 2: Grant Access to AI Project" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Prompt for AI Project details
Write-Host "Enter your AI Project details:" -ForegroundColor Yellow
Write-Host ""

$subscriptionId = Read-Host "Subscription ID (press Enter to use current: $($account.id))"
if ([string]::IsNullOrWhiteSpace($subscriptionId)) {
    $subscriptionId = $account.id
}

$resourceGroup = Read-Host "Resource Group name"
if ([string]::IsNullOrWhiteSpace($resourceGroup)) {
    Write-Host "ERROR: Resource Group name is required" -ForegroundColor Red
    pause
    exit 1
}

$aiProjectName = Read-Host "AI Project name"
if ([string]::IsNullOrWhiteSpace($aiProjectName)) {
    Write-Host "ERROR: AI Project name is required" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "Granting 'Cognitive Services User' role to service principal..." -ForegroundColor Yellow

# Build the scope
$scope = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.CognitiveServices/accounts/$aiProjectName"

# Grant access
$result = az role assignment create `
    --assignee $sp.appId `
    --role "Cognitive Services User" `
    --scope $scope 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to create role assignment" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    Write-Host ""
    Write-Host "Please verify:" -ForegroundColor Yellow
    Write-Host "  - Subscription ID: $subscriptionId" -ForegroundColor Gray
    Write-Host "  - Resource Group: $resourceGroup" -ForegroundColor Gray
    Write-Host "  - AI Project Name: $aiProjectName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "You can manually grant access later with:" -ForegroundColor Yellow
    Write-Host "az role assignment create ``" -ForegroundColor White
    Write-Host "  --assignee $($sp.appId) ``" -ForegroundColor White
    Write-Host "  --role `"Cognitive Services User`" ``" -ForegroundColor White
    Write-Host "  --scope `"$scope`"" -ForegroundColor White
    pause
    exit 1
}

Write-Host ""
Write-Host "✓ Access Granted Successfully!" -ForegroundColor Green
Write-Host ""
Write-Host ""

# Summary
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your service principal:" -ForegroundColor Yellow
Write-Host "  App ID: $($sp.appId)" -ForegroundColor Gray
Write-Host "  Name: bing-grounding-api-sp" -ForegroundColor Gray
Write-Host "  Role: Cognitive Services User on $aiProjectName" -ForegroundColor Gray
Write-Host ""
Write-Host ""

# Print formatted credentials for easy copy/paste
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Copy/Paste to .env file:" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "AZURE_CLIENT_ID=`"$($sp.appId)`""
Write-Host "AZURE_CLIENT_SECRET=`"$($sp.password)`""
Write-Host "AZURE_TENANT_ID=`"$($sp.tenant)`""
Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Copy the lines above and paste into your .env file" -ForegroundColor White
Write-Host "  2. Verify your .env has AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_AGENT_ID" -ForegroundColor White
Write-Host "  3. Run the server: .\\_run_server.bat" -ForegroundColor White
Write-Host ""

pause
