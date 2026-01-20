// Creates Bing Grounding connection in AI Foundry account
param foundryName string
param bingResourceId string
param bingResourceName string
param bingResourceGroup string

// Get existing AI Foundry account
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

// Get existing Bing resource to retrieve keys
resource bingResource 'Microsoft.Bing/accounts@2020-06-10' existing = {
  name: bingResourceName
  scope: resourceGroup(bingResourceGroup)
}

// Create Bing Grounding connection with actual Bing API key
resource bingConnection 'Microsoft.CognitiveServices/accounts/connections@2025-10-01-preview' = {
  parent: aiFoundry
  name: 'default-bing'
  properties: {
    category: 'GroundingWithBingSearch'
    target: 'https://api.bing.microsoft.com/'
    authType: 'ApiKey'
    credentials: {
      key: bingResource.listKeys().key1
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: bingResourceId
      type: 'bing_grounding'
    }
  }
}

output connectionId string = bingConnection.id
output connectionName string = bingConnection.name
