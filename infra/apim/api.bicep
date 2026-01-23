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
    description: 'List all available agents'
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
