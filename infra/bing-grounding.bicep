// Bing Grounding Search resource for AI Agents
param bingResourceName string
param location string = 'global'
param tags object = {}

resource bingGrounding 'Microsoft.Bing/accounts@2020-06-10' = {
  name: bingResourceName
  location: location
  kind: 'Bing.Grounding'
  sku: {
    name: 'F0'
  }
  properties: {}
  tags: tags
}

output bingResourceId string = bingGrounding.id
output bingResourceName string = bingGrounding.name
