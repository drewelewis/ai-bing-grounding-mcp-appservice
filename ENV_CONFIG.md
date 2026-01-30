# Environment Configuration

**IMPORTANT:** These files are **local-only** configuration sources. They are synced to GitHub Environments and should NOT be committed to git.

## Workflow

1. **Create** `.env.{environment}` files locally with configuration
2. **Sync** to GitHub Environments using `sync_github_env_simple.py`
3. **Workflows** pull variables from GitHub Environments (not files)
4. **Do not commit** `.env.*` files to git (they're gitignored)

## Environment Files (Local Only)

Each environment has its own `.env.{environment}` file:

- `.env.production_primary` - Production primary region (eastus2)
- `.env.production_secondary` - Production secondary region (westus2)
- `.env.qa_primary` - QA primary region (eastus2)
- `.env.qa_secondary` - QA secondary region (westus3)

These files exist only on your local machine to make syncing easier.

## File Format

Each file contains 5 required variables:

```bash
WEBAPP_NAME=app-name-here
AI_PROJECT_ENDPOINT=https://ai-foundry-name.cognitiveservices.azure.com/
AI_PROJECT_NAME=ai-proj-name
REGION=eastus2
RESOURCE_GROUP=rg-name
```

## Syncing to GitHub

### Option 1: REST API (Recommended - No CLI needed)

Uses GitHub REST API with a Personal Access Token:

```bash
# Set token (one-time setup)
# PowerShell:
$env:GITHUB_TOKEN="ghp_xxxxx"

# Linux/Mac:
export GITHUB_TOKEN=ghp_xxxxx

# Sync all environments
python sync_github_env_api.py --environment all

# Sync specific environment
python sync_github_env_api.py --environment production_primary
```

**Create token:** https://github.com/settings/tokens/new (needs `repo` and `admin:org` scopes)

### Option 2: GitHub CLI

```bash
# Sync all environments
python sync_github_env.py --environment all
```

### Option 3: PowerShell

```powershell
.\sync-github-env.ps1 -Environment all
```

## Prerequisites

**Option 1 (REST API):**
- GitHub Personal Access Token
- Python 3.11+ (already installed)
- No additional tools needed

**Option 2 (GitHub CLI):**
- Install [GitHub CLI](https://cli.github.com/): `winget install GitHub.cli`
- Authenticate: `gh auth login`

**Option 3 (PowerShell):**
- GitHub CLI (same as Option 2)

## How It Works

1. Edit local `.env.{environment}` file with your values
2. Run `python sync_github_env_simple.py --environment all` to push to GitHub Environments
3. Workflows use `${{ vars.VARIABLE_NAME }}` to pull from GitHub Environments
4. Files stay local - never committed to git

## Adding a New Environment

1. Create `.env.new_environment` file
2. Add environment to workflow matrix in `.github/workflows/deploy.yml`
3. Update `sync_github_env.py` choices list
4. Run: `python sync_github_env.py --environment new_environment`

## Verification

Check variables are set correctly:

```powershell
gh variable list --env production_primary
gh variable list --env production_secondary
gh variable list --env qa_primary
gh variable list --env qa_secondary
```
