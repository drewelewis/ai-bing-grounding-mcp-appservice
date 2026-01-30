#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Sync environment variables from .env files to GitHub Environments
    
.DESCRIPTION
    Reads .env.{environment} files and creates/updates variables in GitHub environments.
    Uses GitHub CLI (gh) to set environment variables.
    
.PARAMETER Environment
    Which environment to sync. If not specified, syncs all environments.
    Valid values: production_primary, production_secondary, qa_primary, qa_secondary, all
    
.EXAMPLE
    .\sync-github-env.ps1 -Environment production_primary
    
.EXAMPLE
    .\sync-github-env.ps1 -Environment all
#>

param(
    [Parameter()]
    [ValidateSet("production_primary", "production_secondary", "qa_primary", "qa_secondary", "all")]
    [string]$Environment = "all"
)

$ErrorActionPreference = "Stop"

# Get repository info
$repo = gh repo view --json nameWithOwner -q .nameWithOwner
if (-not $repo) {
    Write-Error "Could not determine repository. Make sure you're in a git repository with GitHub remote."
    exit 1
}

Write-Host "`n🔄 GitHub Environment Variable Sync" -ForegroundColor Cyan
Write-Host "Repository: $repo`n" -ForegroundColor Gray

function Sync-Environment {
    param(
        [string]$EnvName
    )
    
    $envFile = ".env.$EnvName"
    
    if (-not (Test-Path $envFile)) {
        Write-Warning "⚠️  $envFile not found - skipping"
        return
    }
    
    Write-Host "📁 Processing $EnvName..." -ForegroundColor Yellow
    
    # Check if environment exists, create if not
    $envExists = gh api "repos/$repo/environments/$EnvName" 2>$null
    if (-not $envExists) {
        Write-Host "   Creating environment $EnvName..." -ForegroundColor Gray
        # Create environment by setting a dummy variable (gh CLI limitation)
        gh api --method PUT "repos/$repo/environments/$EnvName" -f "prevent_self_review=false" | Out-Null
    }
    
    # Read .env file
    $content = Get-Content $envFile
    $varsSet = 0
    
    foreach ($line in $content) {
        # Skip comments and empty lines
        if ($line -match '^\s*#' -or $line -match '^\s*$') {
            continue
        }
        
        # Parse KEY=VALUE
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            Write-Host "   Setting $key..." -ForegroundColor Gray
            
            # Set environment variable using gh CLI
            gh variable set $key --body $value --env $EnvName
            
            if ($LASTEXITCODE -eq 0) {
                $varsSet++
            } else {
                Write-Warning "   Failed to set $key"
            }
        }
    }
    
    Write-Host "   ✅ Set $varsSet variables in $EnvName`n" -ForegroundColor Green
}

# Determine which environments to sync
$environments = if ($Environment -eq "all") {
    @("production_primary", "production_secondary", "qa_primary", "qa_secondary")
} else {
    @($Environment)
}

# Sync each environment
foreach ($env in $environments) {
    Sync-Environment -EnvName $env
}

Write-Host "✅ Sync complete!`n" -ForegroundColor Green
Write-Host "To verify, run: gh variable list --env <environment_name>" -ForegroundColor Gray
