<#
.SYNOPSIS
    Deploy to Azure App Service environment

.DESCRIPTION
    Switches to App Service configuration and deploys using azd.
    Creates a separate azd environment to avoid conflicts with Container Apps deployment.

.PARAMETER EnvironmentName
    Name of the azd environment (default: bing-grounding-appservice)

.EXAMPLE
    .\deploy-appservice.ps1
    .\deploy-appservice.ps1 -EnvironmentName my-custom-env
#>

param(
    [string]$EnvironmentName = "bing-grounding-appservice"
)

$ErrorActionPreference = "Stop"

Write-Host "`n🚀 Deploying to Azure App Service..." -ForegroundColor Cyan

# Backup current azure.yaml if it's the Container Apps version
$azureYaml = "azure.yaml"
$backupYaml = "azure-containerapp-backup.yaml"
$appServiceYaml = "azure-appservice.yaml"

# Check if azure-appservice.yaml exists
if (-not (Test-Path $appServiceYaml)) {
    Write-Host "❌ $appServiceYaml not found!" -ForegroundColor Red
    exit 1
}

# Check current azure.yaml to see if it's Container Apps
$currentContent = Get-Content $azureYaml -Raw
$isContainerApp = $currentContent -match "host:\s*containerapp"

if ($isContainerApp) {
    Write-Host "📦 Backing up Container Apps config..." -ForegroundColor Yellow
    Copy-Item $azureYaml $backupYaml -Force
}

# Copy App Service config
Write-Host "📝 Switching to App Service config..." -ForegroundColor Yellow
Copy-Item $appServiceYaml $azureYaml -Force

try {
    # Select or create environment
    Write-Host "🔧 Setting up environment: $EnvironmentName" -ForegroundColor Yellow
    azd env select $EnvironmentName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Creating new environment..." -ForegroundColor Gray
        azd env new $EnvironmentName
    }

    # Deploy
    Write-Host "`n🚀 Running azd up..." -ForegroundColor Cyan
    azd up

    Write-Host "`n✅ App Service deployment complete!" -ForegroundColor Green
}
finally {
    # Restore original if we backed it up
    if ($isContainerApp -and (Test-Path $backupYaml)) {
        Write-Host "`n🔄 Restoring Container Apps config..." -ForegroundColor Yellow
        Copy-Item $backupYaml $azureYaml -Force
        Remove-Item $backupYaml -Force
    }
}

Write-Host "`n📋 To switch environments later:" -ForegroundColor Gray
Write-Host "   Container Apps: azd env select <your-aca-env>" -ForegroundColor Gray
Write-Host "   App Service:    azd env select $EnvironmentName" -ForegroundColor Gray
