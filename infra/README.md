# OmniPitch Azure Cloud-Native Infrastructure

This directory contains Infrastructure as Code (IaC) written in **Bicep** to deploy OmniPitch on **Microsoft Azure**, fulfilling the requirements for the **Best Azure Cloud Native Integration** and **Best Enterprise Solution** awards.

---

## 🏗️ Architecture Components Deployed

1. **Azure Container Apps**: Serverless hosting for the OmniPitch FastAPI backend and real-time dashboard with horizontal autoscale (1-5 replicas).
2. **Azure Event Hubs**: Scalable event streaming platform for ingesting high-frequency synthetic football match events.
3. **Azure Cosmos DB**: Globally distributed NoSQL database for match state, rolling analytics, and telemetry persistence.
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
  --parameters main.parameters.json
```
