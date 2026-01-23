// APIM API and Operations for Bing Grounding MCP Server
// Deployed via CI/CD pipeline

param apimName string
param primaryBackendUrl string
param secondaryBackendUrl string = ''

resource apim 'Microsoft.ApiManagement/service@2022-08-01' existing = {
  name: apimName
}

// Primary Backend
resource primaryBackend 'Microsoft.ApiManagement/service/backends@2022-08-01' = {
  parent: apim
  name: 'primary-backend'
  properties: {
    url: primaryBackendUrl
    protocol: 'http'
    title: 'Primary App Service'
    description: 'Primary backend in East US 2'
  }
}

// Secondary Backend (optional)
resource secondaryBackend 'Microsoft.ApiManagement/service/backends@2022-08-01' = if (!empty(secondaryBackendUrl)) {
  parent: apim
  name: 'secondary-backend'
  properties: {
    url: secondaryBackendUrl
    protocol: 'http'
    title: 'Secondary App Service'
    description: 'Secondary backend in West US 2'
  }
}

// Backend Pool with failover
resource backendPool 'Microsoft.ApiManagement/service/backends@2023-09-01-preview' = {
  parent: apim
  name: 'multi-region-pool'
  properties: {
    type: 'Pool'
    pool: {
      services: !empty(secondaryBackendUrl) ? [
        {
          id: primaryBackend.id
          priority: 1
          weight: 1
        }
        {
          id: secondaryBackend.id
          priority: 2
          weight: 1
        }
      ] : [
        {
          id: primaryBackend.id
          priority: 1
          weight: 1
        }
      ]
    }
  }
}

// REST API - provides the actual backend operations
resource restApi 'Microsoft.ApiManagement/service/apis@2022-08-01' = {
  parent: apim
  name: 'bing-grounding-api'
  properties: {
    displayName: 'Bing Grounding REST API'
    description: 'REST API for Bing Grounding operations'
    path: 'bing-grounding'
    protocols: ['https']
    subscriptionRequired: false
  }
}

// REST API Policy - route to backend pool
resource restApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2022-08-01' = {
  parent: restApi
  name: 'policy'
  properties: {
    format: 'xml'
    value: '<policies><inbound><base /><set-backend-service backend-id="multi-region-pool" /></inbound><backend><forward-request timeout="120" /></backend><outbound><base /></outbound><on-error><base /></on-error></policies>'
  }
}

// REST API Operations
resource bingGroundingOperation 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: restApi
  name: 'bing-grounding'
  properties: {
    displayName: 'Bing Grounding'
    method: 'POST'
    urlTemplate: '/chat'
    description: 'Send chat completion request with Bing grounding'
  }
}

resource healthOperationRest 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: restApi
  name: 'health'
  properties: {
    displayName: 'Health Check'
    method: 'GET'
    urlTemplate: '/health'
    description: 'Check API and backend health status'
  }
}

resource agentsOperationRest 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: restApi
  name: 'agents'
  properties: {
    displayName: 'List Agents'
    method: 'GET'
    urlTemplate: '/agents'
    description: 'List all available agents from all regions'
  }
}

// Agents operation policy - aggregate from both regions
// Two versions: one for single region, one for multi-region
// Note: &lt; and &gt; are used to escape < and > in C# generics within XML
var singleRegionPolicyXml = '''<policies>
  <inbound>
    <base />
    <send-request mode="new" response-variable-name="primaryResponse" timeout="30" ignore-error="true">
      <set-url>PRIMARY_URL/agents</set-url>
      <set-method>GET</set-method>
    </send-request>
    <return-response>
      <set-status code="200" reason="OK" />
      <set-header name="Content-Type" exists-action="override">
        <value>application/json</value>
      </set-header>
      <set-body>@{
        var primaryBody = ((IResponse)context.Variables["primaryResponse"])?.Body?.As&lt;JObject&gt;();
        if (primaryBody == null) {
          return new JObject(new JProperty("total", 0), new JProperty("regions", new JArray()), new JProperty("agents", new JArray())).ToString();
        }
        var primaryRegion = primaryBody["region"]?.ToString() ?? "primary";
        var agents = primaryBody["agents"] as JArray ?? new JArray();
        var allAgents = new JArray();
        foreach (var agent in agents) {
          var agentObj = (JObject)agent.DeepClone();
          agentObj["region"] = primaryRegion;
          allAgents.Add(agentObj);
        }
        return new JObject(
          new JProperty("total", allAgents.Count),
          new JProperty("regions", new JArray(primaryRegion)),
          new JProperty("agents", allAgents)
        ).ToString();
      }</set-body>
    </return-response>
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>'''

var multiRegionPolicyXml = '''<policies>
  <inbound>
    <base />
    <send-request mode="new" response-variable-name="primaryResponse" timeout="30" ignore-error="true">
      <set-url>PRIMARY_URL/agents</set-url>
      <set-method>GET</set-method>
    </send-request>
    <send-request mode="new" response-variable-name="secondaryResponse" timeout="30" ignore-error="true">
      <set-url>SECONDARY_URL/agents</set-url>
      <set-method>GET</set-method>
    </send-request>
    <return-response>
      <set-status code="200" reason="OK" />
      <set-header name="Content-Type" exists-action="override">
        <value>application/json</value>
      </set-header>
      <set-body>@{
        var primaryBody = ((IResponse)context.Variables["primaryResponse"])?.Body?.As&lt;JObject&gt;();
        var secondaryBody = ((IResponse)context.Variables["secondaryResponse"])?.Body?.As&lt;JObject&gt;();
        
        var regions = new JArray();
        var allAgents = new JArray();
        
        if (primaryBody != null) {
          var region = primaryBody["region"]?.ToString() ?? "primary";
          regions.Add(region);
          var agents = primaryBody["agents"] as JArray;
          if (agents != null) {
            foreach (var agent in agents) {
              var obj = (JObject)agent.DeepClone();
              obj["region"] = region;
              allAgents.Add(obj);
            }
          }
        }
        
        if (secondaryBody != null) {
          var region = secondaryBody["region"]?.ToString() ?? "secondary";
          regions.Add(region);
          var agents = secondaryBody["agents"] as JArray;
          if (agents != null) {
            foreach (var agent in agents) {
              var obj = (JObject)agent.DeepClone();
              obj["region"] = region;
              allAgents.Add(obj);
            }
          }
        }
        
        return new JObject(
          new JProperty("total", allAgents.Count),
          new JProperty("regions", regions),
          new JProperty("agents", allAgents)
        ).ToString();
      }</set-body>
    </return-response>
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>'''

var hasSecondaryRegion = !empty(secondaryBackendUrl)
var agentsPolicyTemplate = hasSecondaryRegion ? multiRegionPolicyXml : singleRegionPolicyXml
var agentsPolicyWithPrimary = replace(agentsPolicyTemplate, 'PRIMARY_URL', primaryBackendUrl)
var agentsPolicyFinal = hasSecondaryRegion ? replace(agentsPolicyWithPrimary, 'SECONDARY_URL', secondaryBackendUrl) : agentsPolicyWithPrimary

resource agentsOperationPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2022-08-01' = {
  parent: agentsOperationRest
  name: 'policy'
  properties: {
    format: 'xml'
    value: agentsPolicyFinal
  }
}

// MCP API - exposes tools via MCP protocol
// Note: mcpTools must be configured via Azure Portal or REST API after deployment
// as Bicep doesn't fully support the mcpTools property yet
resource mcpApi 'Microsoft.ApiManagement/service/apis@2024-06-01-preview' = {
  parent: apim
  name: 'bing-grounding-mcp'
  properties: {
    displayName: 'Bing Grounding MCP'
    description: 'MCP Server for Bing Grounding with multi-region failover'
    path: 'mcp'
    protocols: ['https']
    subscriptionRequired: false
    type: 'mcp'
  }
}

output restApiId string = restApi.id
output mcpApiId string = mcpApi.id
output apiPath string = mcpApi.properties.path
output backendPoolId string = backendPool.id
