param projectResourceId string
param webAppPrincipalId string
param foundryName string
param projectName string

// Reference the existing foundry and project
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: foundryName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  name: projectName
  parent: foundry
}

// Grant Web App managed identity access to Foundry Project
// Use Azure AI User role which has Microsoft.CognitiveServices/* dataActions (includes agents/read)
// Use unique GUID including 'webapp' to avoid conflicts with Container App role assignment
resource roleAssignmentWebApp 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(projectResourceId, webAppPrincipalId, 'AzureAIUser', 'webapp')
  scope: project
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d') // Azure AI User
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}
