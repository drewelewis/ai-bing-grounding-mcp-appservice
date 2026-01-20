param location string
param tags object
param appServicePlanName string
param webAppName string
param foundryEndpoint string
param projectName string
param containerRegistryName string = ''
param pythonVersion string = '3.11'

// App Service location - use East US 2 where quota exists
var appServiceLocation = 'eastus2'

// App Service Plan (Linux)
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: appServiceLocation
  tags: tags
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true // Required for Linux
  }
}

// Web App for FastAPI
resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: webAppName
  location: appServiceLocation
  tags: union(tags, {
    'azd-service-name': 'appservice'
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      appCommandLine: 'uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          name: 'AZURE_AI_PROJECT_ENDPOINT'
          value: foundryEndpoint
        }
        {
          name: 'AZURE_AI_PROJECT_NAME'
          value: projectName
        }
      ]
    }
  }
}

// Output the web app details
output webAppName string = webApp.name
output webAppHostName string = webApp.properties.defaultHostName
output webAppEndpoint string = 'https://${webApp.properties.defaultHostName}'
output webAppPrincipalId string = webApp.identity.principalId
