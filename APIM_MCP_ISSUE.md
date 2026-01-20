# APIM MCP Server Issue - Timeout on Initialize

## Summary
Azure API Management's MCP Server feature (Preview) is timing out on MCP protocol `initialize` requests. The backend REST API works perfectly, but the MCP protocol layer in APIM is not responding.

## Environment
- **APIM Service**: `apim-vw5lt6yc7noze.azure-api.net`
- **Resource Group**: `rg-bing-grounding-mcp-dev6`
- **Subscription**: `d201ebeb-c470-4a6f-82d5-c2f95bb0dc1e`
- **Region**: East US
- **APIM Tier**: (check portal)

## MCP Server Configuration
- **MCP Server Name**: `bing-grounding-mcp`
- **MCP Server URL**: `https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp`
- **Type**: Expose API as MCP server
- **Source API**: `bing-grounding-api`
- **Tools Exposed**:
  1. `Bing Grounding` - POST /bing-grounding
  2. `Health Check` - GET /health

## Backend Configuration
- **Backend URL**: `https://ca-vw5lt6yc7noze.bluewater-223e3af1.eastus.azurecontainerapps.io`
- **Backend Type**: Azure Container App
- **Backend Status**: ✅ Working (verified via direct calls and through APIM REST API)

## Test Results

### ✅ WORKING: Direct Container App REST API
```bash
POST https://ca-vw5lt6yc7noze.bluewater-223e3af1.eastus.azurecontainerapps.io/bing-grounding?query=test&model=gpt-4o
Status: 200 OK
Response: {"content":"...","citations":[],...}
```

### ✅ WORKING: APIM REST API
```bash
POST https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding/bing-grounding?query=test&model=gpt-4o
Status: 200 OK
Response: {"content":"...","citations":[],...}
```

### ❌ FAILING: APIM MCP Server
```bash
POST https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp
Headers: Content-Type: application/json, Accept: application/json, text/event-stream
Body: {
  "jsonrpc": "2.0",
  "method": "initialize",
  "id": 1,
  "params": {
    "clientInfo": {"name": "test-client", "version": "1.0"},
    "protocolVersion": "2024-11-05",
    "capabilities": {}
  }
}

Result: TIMEOUT after 60+ seconds (no response from APIM)
```

## Expected Behavior
According to [MCP specification](https://modelcontextprotocol.io/) and [APIM MCP documentation](https://learn.microsoft.com/en-us/azure/api-management/export-rest-mcp-server), the MCP server should:

1. Accept the `initialize` request
2. Return an `initialize` response with server info and capabilities
3. NOT forward the `initialize` method to the backend (it's a protocol handshake)

## Actual Behavior
The MCP endpoint:
- Accepts the TCP connection
- Never returns a response
- Times out after 60+ seconds
- No requests appear in backend Container App logs (indicating APIM is not forwarding)
- No errors in APIM activity logs

## Diagnostic Commands Run
```powershell
# Verified MCP server exists
az apim api list --service-name apim-vw5lt6yc7noze --resource-group rg-bing-grounding-mcp-dev6

# Verified backend is working  
az containerapp logs show --name ca-vw5lt6yc7noze --resource-group rg-bing-grounding-mcp-dev6

# Tested REST API directly
curl https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding/bing-grounding?query=test&model=gpt-4o

# Tested MCP endpoint
python test_mcp_endpoint.py  # Times out
```

## Steps to Reproduce
1. Create APIM instance in Azure
2. Create REST API in APIM with POST operation
3. Configure REST API backend to point to Container App
4. Verify REST API works through APIM
5. Create MCP server: "Expose an API as an MCP server"
6. Select the REST API and all operations
7. Wait for MCP server creation to complete
8. Send MCP `initialize` request to MCP server endpoint
9. Observe: Request times out with no response

## MCP Client Code (Python)
```python
import httpx

response = httpx.post(
    "https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp",
    json={
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
            "clientInfo": {"name": "test-client", "version": "1.0"},
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        }
    },
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    },
    timeout=60.0
)
# Result: httpx.ReadTimeout after 60 seconds
```

## Attempted Fixes
1. ✅ Recreated MCP server multiple times
2. ✅ Verified all API operations are mapped to tools
3. ✅ Verified backend URL is correctly configured in source API
4. ✅ Tested with different MCP protocol versions (2024-10-07, 2024-11-05, 2025-03-26)
5. ✅ Verified no blocking policies in APIM
6. ✅ Verified subscription key requirements (disabled for testing)
7. ✅ Tested with different clients (httpx, MCP Python SDK)

## Conclusion
This appears to be a bug in the APIM MCP server preview feature where the MCP protocol handler in APIM is not correctly processing MCP `initialize` requests. The feature is not production-ready.

## Recommended Actions
1. **Contact Azure Support** with this documentation
2. **Report on Azure/api-management GitHub** if public issue tracker exists
3. **Try alternative**: Use GitHub Copilot's MCP integration to test if different MCP client has workaround
4. **Monitor**: Check Azure updates for APIM MCP server fixes

## Documentation References
- [Expose REST API as MCP server](https://learn.microsoft.com/en-us/azure/api-management/export-rest-mcp-server)
- [MCP Server Overview in APIM](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)

## Last Updated
December 12, 2025
