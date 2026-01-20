param location string
param tags object
param apimServiceName string
param foundryName string
param projectName string

// Model pool sizes from .env (passed via main.bicep)
param agentPoolSizeGpt41 int = 0
param agentPoolSizeGpt5 int = 0
param agentPoolSizeGpt5Mini int = 0
param agentPoolSizeGpt5Nano int = 0
param agentPoolSizeGpt4o int = 0
param agentPoolSizeGpt4 int = 0
param agentPoolSizeGpt35Turbo int = 0

// Storage Account for AI Hub
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Key Vault for AI Hub
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Microsoft Foundry Resource (replaces AI Hub + Azure OpenAI)
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: foundryName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// Foundry Project
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: projectName
  parent: foundry
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// Model Deployments - Deploy each model conditionally based on pool size
// GPT-4.1
resource deploymentGpt41 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt41 > 0) {
  parent: foundry
  name: 'gpt-4.1'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

// GPT-5
resource deploymentGpt5 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt5 > 0) {
  parent: foundry
  name: 'gpt-5'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5'
      version: '2025-08-07'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [
    deploymentGpt41
  ]
}

// GPT-5-mini
resource deploymentGpt5Mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt5Mini > 0) {
  parent: foundry
  name: 'gpt-5-mini'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5-mini'
      version: '2025-08-07'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [
    deploymentGpt5
  ]
}

// GPT-5-nano
resource deploymentGpt5Nano 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt5Nano > 0) {
  parent: foundry
  name: 'gpt-5-nano'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5-nano'
      version: '2025-08-07'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [
    deploymentGpt5Mini
  ]
}

// GPT-4o
resource deploymentGpt4o 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt4o > 0) {
  parent: foundry
  name: 'gpt-4o'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [
    deploymentGpt5Nano
  ]
}

// GPT-4
resource deploymentGpt4 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt4 > 0) {
  parent: foundry
  name: 'gpt-4'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4'
      version: 'turbo-2024-04-09'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [
    deploymentGpt4o
  ]
}

// GPT-3.5-turbo
resource deploymentGpt35Turbo 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (agentPoolSizeGpt35Turbo > 0) {
  parent: foundry
  name: 'gpt-35-turbo'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-35-turbo'
      version: '0125'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [
    deploymentGpt4
  ]
}

// API Management Service
resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimServiceName
  location: location
  tags: tags
  sku: {
    name: 'Developer'
    capacity: 1
  }
  properties: {
    publisherEmail: 'admin@contoso.com'
    publisherName: 'Contoso'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Outputs
output apimName string = apim.name
output apimGatewayUrl string = apim.properties.gatewayUrl
output foundryName string = foundry.name
output projectName string = project.name
output projectEndpoint string = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
output projectResourceId string = project.id
output gpt4oDeploymentName string = agentPoolSizeGpt4o > 0 ? 'gpt-4o' : (agentPoolSizeGpt41 > 0 ? 'gpt-4.1' : 'gpt-4o')
output deployedModels array = concat(
  agentPoolSizeGpt41 > 0 ? ['gpt-4.1'] : [],
  agentPoolSizeGpt5 > 0 ? ['gpt-5'] : [],
  agentPoolSizeGpt5Mini > 0 ? ['gpt-5-mini'] : [],
  agentPoolSizeGpt5Nano > 0 ? ['gpt-5-nano'] : [],
  agentPoolSizeGpt4o > 0 ? ['gpt-4o'] : [],
  agentPoolSizeGpt4 > 0 ? ['gpt-4'] : [],
  agentPoolSizeGpt35Turbo > 0 ? ['gpt-35-turbo'] : []
)
