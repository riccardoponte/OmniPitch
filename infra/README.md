# OmniPitch Azure Cloud-Native Infrastructure

This directory contains Infrastructure as Code (IaC) written in **Bicep** to deploy OmniPitch on **Microsoft Azure**, fulfilling the requirements for the **Best Azure Cloud Native Integration** and **Best Enterprise Solution** awards.

---

## 🏗️ Architecture Components Deployed

1. **Azure Container Apps**: Hosting for the OmniPitch FastAPI backend, dashboard and MCP endpoint (single replica: match sessions are in memory). Foundry and Event Hubs credentials are injected as secrets.
2. **Azure Event Hubs**: Scalable event streaming platform for ingesting high-frequency synthetic football match events.
3. **Azure Cosmos DB** (optional, `deployCosmos=true`): reserved for persisting match sessions, which is what enables horizontal scale.
4. **Azure Application Insights & Log Analytics**: Full-stack observability, request tracing, and latency monitoring for multi-agent handoffs.

---

## 🚀 Quick Deployment with Azure CLI

### Prerequisites
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login`).

### Steps
```bash
# 1. Create a Resource Group
az group create --name rg-omnipitch-prod --location westeurope

# 2. Deploy the Bicep template
az deployment group create \
  --resource-group rg-omnipitch-prod \
  --template-file main.bicep \
  --parameters main.parameters.json \
  --parameters containerImage=<registry>.azurecr.io/omnipitch:latest foundryEndpoint=<endpoint> foundryApiKey=<key>
```

Build and push the image first (from the repository root):
```bash
az acr build --registry <registry> --image omnipitch:latest .
```

Fastest alternative for a demo URL (builds from source, no registry setup):
```bash
az containerapp up --name omnipitch --resource-group rg-omnipitch-prod --location westeurope --source . --ingress external --target-port 8000
```
