#!/usr/bin/env pwsh
# Monitor deployment progress

Write-Host "`n⏳ MONITORING DEPLOYMENT..." -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Gray

$lastPrimaryAgents = -1
$lastSecondaryAgents = -1
$lastPrimaryModels = -1
$lastSecondaryModels = -1

while ($true) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    # Check apps
    try {
        $p = Invoke-WebRequest -Uri "https://app-52hltr3kdvkvo.azurewebsites.net/health" -UseBasicParsing -TimeoutSec 5
        $primary = $p.Content | ConvertFrom-Json
    } catch {
        $primary = @{agents_loaded = -1}
    }
    
    try {
        $s = Invoke-WebRequest -Uri "https://app-qvzh4onheat32.azurewebsites.net/health" -UseBasicParsing -TimeoutSec 5
        $secondary = $s.Content | ConvertFrom-Json
    } catch {
        $secondary = @{agents_loaded = -1}
    }
    
    # Check Azure models
    try {
        $primaryModels = (az cognitiveservices account deployment list -g "rg-bing-grounding-mcp-prod" -n "ai-foundry-52hltr3kdvkvo" --query "length([])" -o tsv 2>$null)
        if (-not $primaryModels) { $primaryModels = 0 }
    } catch {
        $primaryModels = -1
    }
    
    try {
        $secondaryModels = (az cognitiveservices account deployment list -g "rg-bing-grounding-mcp-prod-secondary" -n "ai-foundry-qvzh4onheat32" --query "length([])" -o tsv 2>$null)
        if (-not $secondaryModels) { $secondaryModels = 0 }
    } catch {
        $secondaryModels = -1
    }
    
    # Only print if something changed
    if ($primary.agents_loaded -ne $lastPrimaryAgents -or 
        $secondary.agents_loaded -ne $lastSecondaryAgents -or
        $primaryModels -ne $lastPrimaryModels -or
        $secondaryModels -ne $lastSecondaryModels) {
        
        Write-Host "[$timestamp]" -ForegroundColor Gray
        Write-Host "  PRIMARY   - Models: $primaryModels, Agents: $($primary.agents_loaded)" -ForegroundColor $(if ($primary.agents_loaded -gt 0) {"Green"} else {"Yellow"})
        Write-Host "  SECONDARY - Models: $secondaryModels, Agents: $($secondary.agents_loaded)" -ForegroundColor $(if ($secondary.agents_loaded -gt 0) {"Green"} else {"Yellow"})
        
        if ($primary.agents_loaded -gt 0 -and $secondary.agents_loaded -gt 0) {
            Write-Host "`n🎉 DEPLOYMENT COMPLETE! Both regions have agents!" -ForegroundColor Green
            Write-Host "===========================================" -ForegroundColor Green
            break
        }
        
        $lastPrimaryAgents = $primary.agents_loaded
        $lastSecondaryAgents = $secondary.agents_loaded
        $lastPrimaryModels = $primaryModels
        $lastSecondaryModels = $secondaryModels
    }
    
    Start-Sleep -Seconds 30
}

Write-Host "`nRun .\test_deployment.ps1 for full details" -ForegroundColor Cyan
