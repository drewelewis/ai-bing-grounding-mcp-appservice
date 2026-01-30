#!/usr/bin/env pwsh
# Test deployment results for both regions

$primary = "app-52hltr3kdvkvo"
$secondary = "app-qvzh4onheat32"

Write-Host "`n🧪 TESTING DEPLOYMENT RESULTS" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

foreach ($region in @(
    @{name="Primary (eastus2)"; app=$primary},
    @{name="Secondary (westus2)"; app=$secondary}
)) {
    Write-Host "`n📍 Testing $($region.name)" -ForegroundColor Cyan
    Write-Host "-------------------------------------------"
    
    # Health check
    Write-Host "  Health: " -NoNewline
    $health = curl -s "https://$($region.app).azurewebsites.net/health" | ConvertFrom-Json
    if ($health.agents_loaded -gt 0) {
        Write-Host "✅ $($health.agents_loaded) agents loaded" -ForegroundColor Green
    } else {
        Write-Host "❌ 0 agents loaded" -ForegroundColor Red
    }
    
    # Models
    Write-Host "  Models: " -NoNewline
    $models = curl -s "https://$($region.app).azurewebsites.net/models" | ConvertFrom-Json
    Write-Host "$($models.total) deployed" -ForegroundColor $(if ($models.total -gt 0) {"Green"} else {"Red"})
    
    # Agents
    Write-Host "  Agents: " -NoNewline
    $agents = curl -s "https://$($region.app).azurewebsites.net/agents" | ConvertFrom-Json
    $agentCount = ($agents.agents | Measure-Object).Count
    Write-Host "$agentCount configured" -ForegroundColor $(if ($agentCount -gt 0) {"Green"} else {"Red"})
    
    if ($agentCount -gt 0) {
        Write-Host "`n  Agent breakdown:" -ForegroundColor Yellow
        $agents.agents | ForEach-Object {
            Write-Host "    - $($_.agent_route): weight=$($_.weight)" -ForegroundColor Gray
        }
    }
}

Write-Host "`n===========================================" -ForegroundColor Green
Write-Host "💡 Run this script after deployment completes" -ForegroundColor Yellow
