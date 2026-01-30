# Azure Deployment Instructions - CRITICAL

## ⚠️ NEVER use manual Azure CLI commands for deployments

This project uses **GitHub Actions workflows** for ALL deployments. Manual changes will be overwritten on next deployment.

### Infrastructure Changes (Bicep files) → Use `deploy-infra.yml`

**When:** Changes to `infra/**/*.bicep`, App Service settings, timeouts, resources

**How:**
```bash
gh workflow run deploy-infra.yml --field action=provision --field environment=prod
```

**NEVER:**
- ❌ `az webapp config appsettings set ...`
- ❌ `az deployment group create ...`
- ❌ Any manual `az` commands that modify resources

### Application Code Changes → Use `deploy.yml` (automatic)

**When:** Changes to `app/`, `agents/`, `ai/`, `scripts/`, Python code

**How:**
```bash
git add .
git commit -m "Your changes"
git push origin main  # Triggers automatically
```

### Agent Weights → Use `agent-weights.yml`

**When:** Blue/green deployments, A/B testing

**How:**
```bash
gh workflow run agent-weights.yml --field region=primary --field agent_route=gpt4o_2 --field weight=50
```

## Common Mistakes to Avoid

❌ User reports timeout → DO NOT run `az webapp config appsettings set ...`
✅ Edit `infra/appservice.bicep` → commit → run `deploy-infra.yml`

❌ Need to update agents → DO NOT run `python scripts/postprovision_create_agents.py`
✅ Edit `agents.config.yaml` → commit → push (auto deploys)

❌ Want to change environment variable → DO NOT use `az` commands
✅ Edit `infra/appservice.bicep` → commit → run `deploy-infra.yml`

## Why This Matters

- **Infrastructure as Code:** All config in Git, no manual drift
- **Reproducibility:** Anyone can redeploy from commits
- **Audit trail:** All changes tracked
- **No surprises:** Next deployment won't overwrite manual changes

## When `az` Commands Are OK

✅ **Read-only operations:**
- `az webapp log tail ...` - View logs
- `az webapp list ...` - List resources
- `curl https://app.../health` - Test endpoints
- `gh run list` - Check workflow status

❌ **NEVER for modifications:**
- Any `az ... create/update/set/delete`
- Any `az deployment ...`

## Remember

> "If you're typing `az` to modify resources, STOP. Use the workflows."

1. Edit Bicep/code files
2. Commit to Git
3. Run appropriate workflow
4. Verify deployment

No shortcuts. No exceptions.