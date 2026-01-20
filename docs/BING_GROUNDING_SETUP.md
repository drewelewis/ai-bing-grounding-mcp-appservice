# Bing Grounding Setup

**⚠️ IMPORTANT: Manual Setup Required**

Due to Azure API limitations, the Bing Grounding resource **cannot** be deployed via Bicep/ARM templates.  
You must create it manually through the Azure Portal.

## Setup Instructions

### 1. Create the Bing Grounding Resource

1. **Open the Azure Portal creation page:**
   ```
   https://portal.azure.com/#create/Microsoft.BingGroundingSearch
   ```

2. **Fill in the creation form:**
   - **Subscription**: Select your Azure subscription
   - **Resource Group**: Select the same resource group as your AI Foundry project  
     (e.g., `rg-bing-grounding-mcp-dev2`)
   - **Resource Name**: `bing-grounding-<env>` (e.g., `bing-grounding-dev2`)
   - **Pricing Tier**: `F0 (Free)` - Provides 1,000 transactions per month

3. **Review and Create:**
   - Click **"Review + Create"**
   - Review the settings
   - Click **"Create"**

4. **Wait for deployment** (usually takes < 1 minute)

### 2. Verify the Resource

After creation, verify the resource exists:

```bash
az resource list \
  --resource-group rg-bing-grounding-mcp-dev2 \
  --resource-type "Microsoft.Bing/accounts" \
  --output table
```

You should see output like:
```
Name                    ResourceGroup                   Location    Type
----------------------  -----------------------------  ----------  ---------------------
bing-grounding-dev2     rg-bing-grounding-mcp-dev2     global      Microsoft.Bing/accounts
```

### 3. Test the Agents

Once the Bing resource is created, your AI agents will automatically use it.

The agents are already configured with the `BingGroundingToolDefinition` and will:
1. Automatically detect the Bing resource in the same resource group
2. Create a connection at runtime when first invoked
3. Use Bing Search to ground responses with real-time web data

## How It Works

### Agent Configuration

The agents (`scripts/postprovision_create_agents.py`) are created with:

```python
bing_tool = BingGroundingToolDefinition(
    bing_grounding=BingGroundingSearchToolParameters(
        search_configurations=[BingGroundingSearchConfiguration(
            connection_id=bing_connection_id
        )]
    )
)

agent = project_client.agents.create_agent(
    model="gpt-4o",
    name=f"agent_bing_gpt4o_{i}",
    instructions="You are a helpful AI assistant with access to real-time web search.",
    tools=[bing_tool.definitions[0]],
    ...
)
```

### Runtime Connection

- When an agent is **first invoked** with a query requiring web search
- Azure AI Foundry **automatically creates** a connection to the Bing resource
- The connection is named `default-bing` in the project
- No manual connection setup is needed!

### Example Usage

```python
# The agent will automatically use Bing when needed
response = agent.run(
    thread_id=thread_id,
    message="What are the latest AI developments in December 2025?"
)

# Response will include:
# - AI-generated answer using current web data
# - Citations with URLs to source websites
# - Bing search query URL
```

## Troubleshooting

### Error: "missing_required_parameter: AML connections are required for Bing Grounding"

**Cause**: The Bing Grounding resource doesn't exist in the resource group.

**Solution**:
1. Verify the resource exists:
   ```bash
   az resource list --resource-group rg-bing-grounding-mcp-dev2 --resource-type "Microsoft.Bing/accounts"
   ```

2. If missing, create it via the Portal (see step 1 above)

3. Re-run the agent creation if needed:
   ```bash
   python scripts/postprovision_create_agents.py
   ```

### Error: "InternalServerError" when deploying via Bicep

**Cause**: The Bing Grounding resource API doesn't support programmatic deployment yet.

**Solution**: This is expected. Always create via Azure Portal.

## References

- [Official Microsoft Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding?view=foundry-classic)
- [Bing Grounding Pricing](https://www.microsoft.com/en-us/bing/apis/grounding-pricing)
- [Bing Grounding Terms](https://www.microsoft.com/en-us/bing/apis/grounding-legal)

## Pricing

- **F0 (Free Tier)**: 1,000 transactions/month
- **Transactions** = Number of tool calls per agent run
- Each Bing search query = 1 transaction
- An agent may make multiple searches per run

See the [pricing page](https://www.microsoft.com/en-us/bing/apis/grounding-pricing) for current rates.
