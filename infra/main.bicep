// ==============================================================================
// OmniPitch - Azure Cloud Native Infrastructure as Code (Bicep)
// Targeted Categories:
//  - Best Azure Cloud Native Integration
//  - Best Enterprise Solution
// ==============================================================================

@description('Azure location for all resources')
param location string = resourceGroup().location

@description('Environment name prefix (e.g., dev, prod)')
param environmentName string = 'dev'

@description('Unique application suffix')
param appSuffix string = uniqueString(resourceGroup().id)

@description('Container image for the OmniPitch app (e.g. <registry>.azurecr.io/omnipitch:latest)')
param containerImage string

@description('Microsoft Foundry / Azure OpenAI endpoint used by the commentator and recap agents (optional)')
param foundryEndpoint string = ''

@secure()
@description('Microsoft Foundry / Azure OpenAI API key (optional)')
param foundryApiKey string = ''

@description('Model deployment name in Microsoft Foundry')
param foundryDeployment string = 'gpt-4o-mini'

@description('Provision Cosmos DB for match-state persistence (not used by the in-memory demo)')
param deployCosmos bool = false

var appName = 'omnipitch-${environmentName}-${appSuffix}'
var logAnalyticsName = 'log-${appName}'
var appInsightsName = 'appi-${appName}'
var containerAppEnvName = 'cae-${appName}'
var containerAppName = 'app-${appName}'
var eventHubNamespaceName = 'evh-${appName}'
var cosmosDbName = 'cosmos-${appName}'

// 1. Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 2. Application Insights (OpenTelemetry & Agent Tracing)
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// 3. Azure Event Hubs Namespace (High-throughput match event ingestion)
resource eventHubNamespace 'Microsoft.EventHub/namespaces@2023-01-01-preview' = {
  name: eventHubNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
}

resource matchEventHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubNamespace
  name: 'match-events'
  properties: {
    messageRetentionInDays: 1
    partitionCount: 4
  }
}

// 4. Azure Cosmos DB (Distributed Match State & Telemetry)
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = if (deployCosmos) {
  name: cosmosDbName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = if (deployCosmos) {
  parent: cosmosDbAccount
  name: 'omnipitch'
  properties: {
    resource: {
      id: 'omnipitch'
    }
  }
}

// 5. Azure Container Apps Managed Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// 6. Azure Container App (FastAPI Backend & Interactive Dashboard)
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: [
        {
          name: 'foundry-api-key'
          value: empty(foundryApiKey) ? 'not-configured' : foundryApiKey
        }
        {
          name: 'eventhub-connection'
          value: listKeys(resourceId('Microsoft.EventHub/namespaces/authorizationRules', eventHubNamespace.name, 'RootManageSharedAccessKey'), '2023-01-01-preview').primaryConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'omnipitch-api'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            {
              name: 'ENVIRONMENT'
              value: environmentName
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
            {
              name: 'AZURE_EVENT_HUB_NAME'
              value: matchEventHub.name
            }
            {
              name: 'AZURE_EVENT_HUB_CONNECTION_STRING'
              secretRef: 'eventhub-connection'
            }
            {
              name: 'AZURE_AI_FOUNDRY_ENDPOINT'
              value: foundryEndpoint
            }
            {
              name: 'AZURE_AI_FOUNDRY_API_KEY'
              secretRef: 'foundry-api-key'
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
              value: foundryDeployment
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/health'
                port: 8000
              }
            }
          ]
        }
      ]
      // Match sessions live in memory, so one replica keeps SSE and REST on the same state.
      // Moving sessions to Cosmos DB / Redis is what unlocks horizontal scale.
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output eventHubName string = matchEventHub.name
