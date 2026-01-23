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
  dependsOn: [
    primaryBackend
    secondaryBackend
  ]
}

// MCP API with MCP Protocol enabled
resource mcpApi 'Microsoft.ApiManagement/service/apis@2024-06-01-preview' = {
  parent: apim
  name: 'bing-grounding-mcp'
  properties: {
    displayName: 'Bing Grounding MCP API'
    description: 'Multi-region Bing Grounding MCP Server API with automatic failover'
    path: 'mcp'
    protocols: ['https']
    subscriptionRequired: false
    type: 'mcp'
    mcpProperties: {
      backendId: backendPool.id
    }
  }
  dependsOn: [
    backendPool
  ]
}

// API Policy - route to backend pool
resource mcpApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2022-08-01' = {
  parent: mcpApi
  name: 'policy'
  properties: {
    format: 'xml'
    value: '<policies><inbound><base /><set-backend-service backend-id="multi-region-pool" /></inbound><backend><forward-request timeout="120" /></backend><outbound><base /></outbound><on-error><base /></on-error></policies>'
  }
  dependsOn: [
    backendPool
  ]
}

// Operations
resource healthOperation 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: mcpApi
  name: 'health'
  properties: {
    displayName: 'Health Check'
    method: 'GET'
    urlTemplate: '/health'
    description: 'Check API and backend health status'
  }
}

resource agentsOperation 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: mcpApi
  name: 'agents'
  properties: {
    displayName: 'List Agents'
    method: 'GET'
    urlTemplate: '/agents'
    description: 'List all available agents and their configurations'
  }
}

resource chatOperation 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: mcpApi
  name: 'chat'
  properties: {
    displayName: 'Chat Completions'
    method: 'POST'
    urlTemplate: '/chat'
    description: 'Send chat completion request to an agent'
  }
}

resource mcpMessageOperation 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: mcpApi
  name: 'mcp-message'
  properties: {
    displayName: 'MCP Message'
    method: 'POST'
    urlTemplate: '/mcp/message'
    description: 'Send MCP protocol message'
  }
}

resource adminRefreshOperation 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  parent: mcpApi
  name: 'admin-refresh'
  properties: {
    displayName: 'Admin Refresh'
    method: 'POST'
    urlTemplate: '/admin/refresh'
    description: 'Refresh agent configuration from Azure AI Foundry'
  }
}

output apiId string = mcpApi.id
output apiPath string = mcpApi.properties.path
output backendPoolId string = backendPool.id
