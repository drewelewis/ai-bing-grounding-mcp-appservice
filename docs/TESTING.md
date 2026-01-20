# Testing Guide: Semantic Kernel with APIM MCP Server

This guide walks through testing the Semantic Kernel agent that uses the APIM-hosted MCP server for Bing Grounding.

## Prerequisites

1. **Deployed Azure Resources** via `azd up`:
   - Azure API Management instance
   - Container Apps with Bing Grounding API
   - Azure AI Foundry project
   - Azure OpenAI deployment

2. **Python Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **APIM MCP Server Configured**:
   - REST API exposed as MCP server in APIM
   - MCP endpoint URL available
   - Subscription key (if required)

## Setup

### 1. Get APIM MCP Server URL

After `azd up` completes, find your APIM MCP server URL:

**Option A: Azure Portal**
1. Navigate to your API Management instance
2. Go to **APIs** > **MCP Servers**
3. Find your MCP server in the list
4. Copy the **Server URL** (format: `https://<apim-name>.azure-api.net/<api-name>-mcp/mcp`)

**Option B: From azd outputs**
```bash
azd env get-values | grep APIM
```

### 2. Configure Environment Variables

Copy the sample environment file:
```bash
copy .env.test.sample .env
```

Edit `.env` with your actual values:

```dotenv
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-aoai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# APIM MCP Server Configuration
APIM_MCP_SERVER_URL=https://apim-bingground-dev.azure-api.net/bing-grounding-mcp/mcp
APIM_SUBSCRIPTION_KEY=your-apim-subscription-key
```

#### How to Get These Values

**Azure OpenAI**:
```bash
# Get from azd environment
azd env get-values | grep AZURE_OPENAI
```

**APIM Subscription Key**:
1. Azure Portal > API Management > **Subscriptions**
2. Find subscription (e.g., "Built-in all-access subscription")
3. Click **...** > **Show/hide keys**
4. Copy **Primary key**

### 3. Verify Configuration

Test that your configuration is correct:

```bash
# Activate virtual environment if not already activated
.venv\Scripts\activate

# Run test script
python test.py
```

## Test Modes

### Mode 1: Predefined Queries (Default)

Runs three predefined test queries automatically:

```bash
python test.py
```

**Expected Output**:
```
================================================================================
Semantic Kernel Agent with MCP Server Tools
================================================================================

[Config] Azure OpenAI Endpoint: https://your-aoai.openai.azure.com/
[Config] Deployment: gpt-4o
[Config] APIM MCP Server: https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp

[1/5] Initializing Semantic Kernel...
[2/5] Configuring Azure OpenAI service...
[3/5] Connecting to APIM MCP server...
[4/5] Loading MCP tools...
[MCP] Connected to server with 1 tools:
  - bing_grounding: Search the web using Bing...

[5/5] Running test queries...

Query 1/3: What are the latest developments in Azure AI as of December 2025?

[MCP Tool] Calling bing_grounding tool...
[MCP Tool] Query: What are the latest developments in Azure AI as of December 2025?
[MCP Tool] Success! Received response

Agent Response:
[Response with citations from Bing search results]

================================================================================
```

### Mode 2: Interactive Mode

Chat with the agent interactively:

```bash
python test.py --interactive
```

**Example Session**:
```
================================================================================
Interactive Mode - Semantic Kernel Agent with MCP Tools
================================================================================

Type your queries below. Type 'exit' or 'quit' to stop.

You: What is the current weather in Seattle?

[Agent] Thinking...

Agent: Based on current weather data from Bing, Seattle is experiencing...
[Citations included]

--------------------------------------------------------------------------------

You: Compare Azure AI Foundry vs AWS Bedrock

[Agent] Thinking...

Agent: Here's a comparison based on recent information...
[Citations included]

--------------------------------------------------------------------------------

You: exit

Exiting interactive mode...
```

## Validation Checklist

### ✅ Configuration Valid

- [ ] Azure OpenAI endpoint responds (check in Azure Portal)
- [ ] APIM MCP server URL is correct format: `https://<apim>.azure-api.net/<api>-mcp/mcp`
- [ ] APIM subscription key is valid (test in APIM portal)
- [ ] Environment variables loaded (check with `echo %APIM_MCP_SERVER_URL%`)

### ✅ MCP Connection Works

- [ ] Test script connects to APIM MCP server (step 3/5)
- [ ] MCP tools are discovered (step 4/5 shows "1 tools")
- [ ] Tool name is `bing_grounding`

### ✅ Tool Execution Works

- [ ] Agent calls `bing_grounding_search` function
- [ ] MCP tool receives query
- [ ] Response includes citations
- [ ] No errors in output

### ✅ End-to-End Flow

- [ ] Agent uses Bing search for current information
- [ ] Responses include source citations
- [ ] Multiple queries work sequentially
- [ ] Interactive mode responds correctly

## Troubleshooting

### Error: Missing required environment variables

**Problem**: 
```
[ERROR] Missing required environment variables
Required: AZURE_OPENAI_ENDPOINT, APIM_MCP_SERVER_URL
```

**Solution**:
1. Verify `.env` file exists in project root
2. Check environment variables are set:
   ```bash
   type .env
   ```
3. Reload environment:
   ```bash
   .venv\Scripts\activate
   ```

### Error: 401 Unauthorized from APIM

**Problem**:
```
[ERROR] HTTP 401: Unauthorized
```

**Solution**:
1. Verify APIM subscription key is correct:
   - Azure Portal > APIM > **Subscriptions**
   - Copy **Primary key** exactly
2. Check key is set in `.env`:
   ```dotenv
   APIM_SUBSCRIPTION_KEY=your-actual-key-here
   ```

### Error: Connection timeout to APIM

**Problem**:
```
[ERROR] Connection timeout
```

**Solution**:
1. Verify APIM endpoint is accessible:
   ```bash
   curl https://apim-xxx.azure-api.net/health
   ```
2. Check firewall/VPN settings
3. Verify APIM is deployed and running (Azure Portal)

### Error: MCP tool not found

**Problem**:
```
[MCP] Connected to server with 0 tools
```

**Solution**:
1. Verify MCP server is created in APIM:
   - Azure Portal > APIM > **APIs** > **MCP Servers**
2. Check API operations are exposed as tools:
   - Select MCP server > **Tools** blade
   - Ensure operations are listed

### Error: Azure OpenAI quota exceeded

**Problem**:
```
Error code: 429 - Rate limit reached
```

**Solution**:
1. Wait for quota reset (usually 1 minute)
2. Reduce number of test queries
3. Check Azure OpenAI quotas in portal:
   - Azure OpenAI > **Quotas**

### Error: ModuleNotFoundError: No module named 'mcp'

**Problem**:
```
ModuleNotFoundError: No module named 'mcp'
```

**Solution**:
```bash
# Ensure virtual environment is activated
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify mcp package is installed
pip show mcp
```

## Advanced Testing

### Test with curl (Direct MCP Protocol)

List available tools:
```bash
curl -X POST https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: your-key" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}"
```

Call a tool directly:
```bash
curl -X POST https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: your-key" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"bing_grounding\",\"arguments\":{\"query\":\"Azure AI news\"}}}"
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector@0.9.0 \
  --url https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp \
  --header "Ocp-Apim-Subscription-Key: your-key"
```

### Test in Visual Studio Code

1. Open Command Palette (`Ctrl+Shift+P`)
2. Run: **MCP: Add Server**
3. Select: **HTTP (HTTP or Server Sent Events)**
4. Enter server URL: `https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp`
5. Configure header in `.vscode/mcp.json`:
   ```json
   {
     "mcpServers": {
       "bing-grounding": {
         "url": "https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp",
         "headers": {
           "Ocp-Apim-Subscription-Key": "your-key"
         }
       }
     }
   }
   ```
6. GitHub Copilot chat > Agent mode > Tools > Select `bing_grounding`
7. Ask: "What's the latest Azure AI news?"

## Performance Testing

### Measure Response Times

Add timing to test.py:
```python
import time

start = time.time()
result = await session.call_tool("bing_grounding", arguments={"query": query})
elapsed = time.time() - start
print(f"Tool execution time: {elapsed:.2f}s")
```

### Load Testing (Multiple Requests)

```python
import asyncio

async def load_test():
    tasks = [
        session.call_tool("bing_grounding", arguments={"query": f"test query {i}"})
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    return results
```

## Next Steps

After successful testing:

1. **Integrate with LLM Suite**: Configure your LLM routing layer to use the APIM MCP endpoint
2. **Monitor Usage**: Check APIM analytics for tool usage patterns
3. **Scale Resources**: Adjust Container Apps instances based on load
4. **Configure Policies**: Add rate limiting, caching, or authentication policies in APIM
5. **Deploy to Production**: Run `azd env new prod && azd up` for production environment

## Resources

- [APIM as MCP Server Documentation](APIM_MCP_SERVER.md)
- [Semantic Kernel Documentation](https://learn.microsoft.com/en-us/semantic-kernel/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Azure API Management MCP Support](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview)
