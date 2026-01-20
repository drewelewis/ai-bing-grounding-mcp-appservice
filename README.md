# Bing Grounding API

A FastAPI-based REST API and Model Context Protocol (MCP) server for Azure AI Agent Service with Bing grounding capabilities. Provides grounded AI responses with automatic citation extraction through both REST and MCP interfaces.

## Features

✅ **REST API** wrapper for Azure AI Agent with Bing grounding  
✅ **Model Context Protocol (MCP) server** via Azure API Management  
✅ Structured JSON responses with citations  
✅ Region tracking metadata for multi-region deployments  
✅ Docker containerization for easy deployment  
✅ Health check endpoint  
✅ Azure Container Apps ready  
✅ Thread management and cleanup  
✅ **APIM load balancing with circuit breaker pattern**  
✅ **Session affinity (sticky sessions)**  
✅ **Automatic failover and recovery**  
✅ **Automated deployment with Azure Developer CLI (azd)**  
✅ **12 AI agents created automatically during provisioning**  
✅ **MCP endpoint for standardized AI tool integration**

---

## Quick Start: Provision & Deploy to Azure

The fastest way to get started is with Azure Developer CLI:

```bash
# 1. Login to Azure
azd auth login

# 2. Create environment (first time only)
azd env new <environment-name>

# 3. Provision and deploy everything
azd up
```

That's it! **One command does everything:**
- ✅ Provisions all Azure resources (Container Apps, AI Foundry, APIM, etc.)
- ✅ Automatically creates 12 GPT-4o AI agents with Bing grounding (new API)
- ✅ Builds and deploys the Docker container
- ✅ Configures managed identities and RBAC
- ✅ Sets up API Management with load balancing

**The entire process takes approximately 8-15 minutes.**

Your API will be available at the endpoint shown in the output.

### Common Commands

| Command | What It Does | When to Use |
|---------|-------------|-------------|
| `azd up` | Provision + Deploy everything | **Use this for initial setup and updates** |
| `azd deploy` | Deploy code only (skip provisioning) | Quick code updates to existing resources |
| `azd down` | Delete all Azure resources | Clean up / tear down environment |
| `azd env list` | Show available environments | Check which environments exist |

📚 **For detailed provisioning steps**, see [Deployment to Azure](#deployment-to-azure) below.

> **💡 MCP Server via APIM**: Azure API Management natively converts your REST API into a Model Context Protocol (MCP) server. MCP clients (like GitHub Copilot, Semantic Kernel, or Azure OpenAI Responses API) connect to APIM's MCP endpoint via HTTP/SSE transport to access your API as standardized tools. See [APIM as MCP Server](docs/APIM_MCP_SERVER.md) for details.
> 
> **⚠️ Manual Step Required After Deployment**: The `azd deploy` postdeploy hook will display instructions for creating the MCP server in APIM Portal (1-2 minutes). This step is currently manual because MCP server resources are not yet available in ARM/Bicep templates.

---  

## Architecture

### Current Architecture: Single Project with Agent Pool

```mermaid
graph TB
    subgraph External["External Clients"]
        Client[LLM Suite / MCP Client]
    end
    
    subgraph APIM["Azure API Management"]
        Gateway[API Gateway<br/>• Circuit Breaker<br/>• Rate Limiting<br/>• Session Affinity]
    end
    
    subgraph ContainerApps["Container Apps Environment"]
        CA1[Container App 1<br/>12 Agent Endpoints]
        CA2[Container App 2<br/>12 Agent Endpoints]
        CA3[Container App 3<br/>12 Agent Endpoints]
    end
    
    subgraph Foundry["Azure AI Foundry (Single Project)"]
        Project[AI Project]
        GPT4O[GPT-4o Deployment<br/>10K TPM Capacity]
        subgraph Agents["Agent Pool (12 Agents)"]
            Agent1[Agent 1]
            Agent2[Agent 2]
            Agent12[Agent 12]
        end
        Bing[Bing Grounding<br/>Connection]
    end
    
    Client -->|HTTPS Requests| Gateway
    Gateway -->|Load Balance| CA1
    Gateway -->|Load Balance| CA2
    Gateway -->|Load Balance| CA3
    
    CA1 & CA2 & CA3 -->|Managed Identity| Project
    Project --> Agents
    Agent1 & Agent2 & Agent12 -->|Use| GPT4O
    Agent1 & Agent2 & Agent12 -->|Search| Bing
    
    style Gateway fill:#0078d4,color:#fff
    style CA1 fill:#00bcf2,color:#000
    style CA2 fill:#00bcf2,color:#000
    style CA3 fill:#00bcf2,color:#000
    style Project fill:#50e6ff,color:#000
    style GPT4O fill:#ff6b6b,color:#fff
    style Bing fill:#00b294,color:#fff
```

**Characteristics:**
- ✅ **TPM Capacity:** 10K TPM (shared across all agents)
- ✅ **Agent Pool:** 12 agents for load distribution
- ✅ **High Availability:** 3 Container App instances
- ✅ **APIM Load Balancing:** Across Container Apps only
- ⚠️ **Single TPM Quota:** All agents share same GPT-4o deployment

**Use Case:** Development, pilot projects, moderate production workloads (up to ~300K queries/month)

**Monthly Cost:** ~$2,000 (See [Cost Analysis](#cost-analysis) below)

---

## Scale-Out Strategies

As your workload grows beyond 10K TPM capacity, you have several options to scale. Each strategy has different trade-offs in terms of complexity, cost, and LLM Suite integration.

### Strategy 1: Vertical Scale (Increase TPM per Project)

```mermaid
graph TB
    subgraph External["External Clients"]
        Client[LLM Suite / MCP Client]
    end
    
    subgraph APIM["Azure API Management"]
        Gateway[API Gateway]
    end
    
    subgraph ContainerApps["Container Apps (3 instances)"]
        CA[Container Apps<br/>12 Agent Endpoints]
    end
    
    subgraph Foundry["Azure AI Foundry (Single Project)"]
        Project[AI Project]
        GPT4O[GPT-4o Deployment<br/>⬆️ 100K TPM<br/>Provisioned Throughput]
        Agents[Agent Pool<br/>12 Agents]
        Bing[Bing Grounding]
    end
    
    Client -->|HTTPS| Gateway
    Gateway -->|Load Balance| CA
    CA -->|Managed Identity| Project
    Project --> Agents
    Agents -->|Use| GPT4O
    Agents -->|Search| Bing
    
    style Gateway fill:#0078d4,color:#fff
    style CA fill:#00bcf2,color:#000
    style GPT4O fill:#ff6b6b,color:#fff
    style Project fill:#50e6ff,color:#000
```

**Implementation:**
- Increase GPT-4o deployment from 10K to 100K TPM (or higher)
- Use Provisioned Throughput Units (PTU) for guaranteed capacity
- No architecture changes required

**Characteristics:**
- ✅ **Simplest approach** - No code changes
- ✅ **Single endpoint** for LLM Suite
- ✅ **Up to 1M TPM** with PTU
- ⚠️ **Higher cost** - PTU pricing (~$540/PTU/month)
- ⚠️ **Single point of failure** (one project)

**LLM Suite Integration:**
- **No changes required** - Same endpoint structure
- Continue using `/bing-grounding/gpt4o_{1-12}` endpoints

**Monthly Cost:** ~$5K-50K depending on PTU allocation

**When to use:** When you need quick scaling without architectural changes

---

### Strategy 2: Horizontal Scale with Multiple Projects (APIM Managed)

```mermaid
graph TB
    subgraph External["External Clients"]
        Client[LLM Suite / MCP Client<br/>Single Endpoint]
    end
    
    subgraph APIM["Azure API Management - Backend Pool"]
        Gateway[API Gateway<br/>Round-Robin LB<br/>Circuit Breaker]
    end
    
    subgraph Backend1["Environment 1"]
        CA1[Container Apps<br/>12 Agents]
        Project1[AI Project 1<br/>GPT-4o: 10K TPM]
    end
    
    subgraph Backend2["Environment 2"]
        CA2[Container Apps<br/>12 Agents]
        Project2[AI Project 2<br/>GPT-4o: 10K TPM]
    end
    
    subgraph Backend3["Environment 3"]
        CA3[Container Apps<br/>12 Agents]
        Project3[AI Project 3<br/>GPT-4o: 10K TPM]
    end
    
    Client -->|HTTPS| Gateway
    Gateway -->|Route 33%| CA1
    Gateway -->|Route 33%| CA2
    Gateway -->|Route 34%| CA3
    
    CA1 --> Project1
    CA2 --> Project2
    CA3 --> Project3
    
    style Gateway fill:#0078d4,color:#fff
    style CA1 fill:#00bcf2,color:#000
    style CA2 fill:#00bcf2,color:#000
    style CA3 fill:#00bcf2,color:#000
    style Project1 fill:#50e6ff,color:#000
    style Project2 fill:#50e6ff,color:#000
    style Project3 fill:#50e6ff,color:#000
```

**Implementation:**

1. **Deploy multiple environments:**
   ```bash
   # Create 3 separate environments
   azd env new prod-foundry-1
   azd up
   
   azd env new prod-foundry-2
   azd up
   
   azd env new prod-foundry-3
   azd up
   ```

2. **Configure APIM backend pool:**
   ```xml
   <backends>
     <backend id="foundry-pool">
       <backend>
         <url>https://ca-foundry1.azurecontainerapps.io</url>
       </backend>
       <backend>
         <url>https://ca-foundry2.azurecontainerapps.io</url>
       </backend>
       <backend>
         <url>https://ca-foundry3.azurecontainerapps.io</url>
       </backend>
     </backend>
   </backends>
   
   <inbound>
     <set-backend-service backend-id="foundry-pool" />
   </inbound>
   ```

**Characteristics:**
- ✅ **Linear capacity scaling** (3 projects × 10K = 30K TPM)
- ✅ **Fault tolerance** - Project failures don't affect others
- ✅ **Cost efficient** - Pay-per-use pricing
- ✅ **Single endpoint** for LLM Suite (APIM handles routing)
- ⚠️ **More infrastructure** to manage (3 environments)
- ⚠️ **Requires APIM configuration** update

**LLM Suite Integration:**
- **No changes required** - LLM Suite sees single APIM endpoint
- APIM transparently routes to available Foundry projects
- Maintains same `/bing-grounding/gpt4o_{1-12}` endpoint structure

**Monthly Cost:** ~$6K (3 environments × $2K each)

**When to use:** 
- Need 20K-50K TPM capacity
- Want fault tolerance across projects
- Prefer pay-per-use over PTU pricing

---

### Strategy 3: Horizontal Scale with Client-Side Load Balancing

```mermaid
graph TB
    subgraph External["External Clients"]
        Client[LLM Suite / MCP Client<br/>⬆️ Client-Side LB Logic]
    end
    
    subgraph APIM["Azure API Management"]
        Gateway[API Gateway<br/>Shared Policies]
    end
    
    subgraph Backend1["Environment 1"]
        CA1[Container Apps<br/>12 Agents]
        Project1[AI Project 1<br/>GPT-4o: 10K TPM]
    end
    
    subgraph Backend2["Environment 2"]
        CA2[Container Apps<br/>12 Agents]
        Project2[AI Project 2<br/>GPT-4o: 10K TPM]
    end
    
    subgraph Backend3["Environment 3"]
        CA3[Container Apps<br/>12 Agents]
        Project3[AI Project 3<br/>GPT-4o: 10K TPM]
    end
    
    Client -->|33% Traffic| Gateway
    Client -->|33% Traffic| Gateway
    Client -->|34% Traffic| Gateway
    
    Gateway -->|/project1/*| CA1
    Gateway -->|/project2/*| CA2
    Gateway -->|/project3/*| CA3
    
    CA1 --> Project1
    CA2 --> Project2
    CA3 --> Project3
    
    style Client fill:#ffa500,color:#fff
    style Gateway fill:#0078d4,color:#fff
    style CA1 fill:#00bcf2,color:#000
    style CA2 fill:#00bcf2,color:#000
    style CA3 fill:#00bcf2,color:#000
    style Project1 fill:#50e6ff,color:#000
    style Project2 fill:#50e6ff,color:#000
    style Project3 fill:#50e6ff,color:#000
```

**Implementation:**

1. **Deploy multiple environments with distinct paths:**
   ```bash
   azd env new prod-foundry-1
   azd up
   # Endpoint: https://apim.azure-api.net/project1/bing-grounding
   
   azd env new prod-foundry-2
   azd up
   # Endpoint: https://apim.azure-api.net/project2/bing-grounding
   
   azd env new prod-foundry-3
   azd up
   # Endpoint: https://apim.azure-api.net/project3/bing-grounding
   ```

2. **Configure APIM routing:**
   ```xml
   <choose>
     <when condition="@(context.Request.Url.Path.StartsWith("/project1"))">
       <set-backend-service base-url="https://ca-foundry1.azurecontainerapps.io" />
     </when>
     <when condition="@(context.Request.Url.Path.StartsWith("/project2"))">
       <set-backend-service base-url="https://ca-foundry2.azurecontainerapps.io" />
     </when>
     <when condition="@(context.Request.Url.Path.StartsWith("/project3"))">
       <set-backend-service base-url="https://ca-foundry3.azurecontainerapps.io" />
     </when>
   </choose>
   ```

3. **Update LLM Suite configuration:**
   ```yaml
   # LLM Suite config
   foundry_endpoints:
     - url: https://apim.azure-api.net/project1/bing-grounding
       weight: 33
       capacity: 10000  # TPM
     - url: https://apim.azure-api.net/project2/bing-grounding
       weight: 33
       capacity: 10000
     - url: https://apim.azure-api.net/project3/bing-grounding
       weight: 34
       capacity: 10000
   
   load_balancing:
     strategy: round-robin  # or weighted, least-connections
     health_check_interval: 30s
   ```

**Characteristics:**
- ✅ **Full control** over routing logic in LLM Suite
- ✅ **Project-specific routing** for workload segregation
- ✅ **Custom failover** logic possible
- ✅ **Cost visibility** per project endpoint
- ⚠️ **LLM Suite changes required** (configuration + logic)
- ⚠️ **More complex** client implementation
- ⚠️ **Manual endpoint management**

**LLM Suite Integration:**
- **Configuration changes required** - Multiple endpoints
- **Load balancing logic required** - Client-side round-robin/weighted
- **Health monitoring recommended** - Check endpoint availability
- **Per-agent endpoints:**
  - Project 1: `/project1/bing-grounding/gpt4o_{1-12}`
  - Project 2: `/project2/bing-grounding/gpt4o_{1-12}`
  - Project 3: `/project3/bing-grounding/gpt4o_{1-12}`

**Monthly Cost:** ~$6K (3 environments × $2K each)

**When to use:**
- Need advanced routing logic (tenant isolation, workload prioritization)
- Want fine-grained control over traffic distribution
- LLM Suite already has load balancing capabilities
- Need per-project cost tracking

---

### Strategy 4: Hybrid - PTU + Multi-Project

```mermaid
graph TB
    subgraph External["External Clients"]
        Client[LLM Suite / MCP Client]
    end
    
    subgraph APIM["Azure API Management - Weighted LB"]
        Gateway[API Gateway<br/>80% to PTU<br/>20% to Standard]
    end
    
    subgraph PrimaryProject["Primary Project - PTU"]
        CA_PTU[Container Apps<br/>12 Agents]
        Project_PTU[AI Project<br/>GPT-4o PTU<br/>100K TPM<br/>Guaranteed]
    end
    
    subgraph FallbackProjects["Fallback Projects - Standard"]
        CA_STD1[Container Apps<br/>12 Agents]
        Project_STD1[AI Project 1<br/>GPT-4o: 10K TPM]
        
        CA_STD2[Container Apps<br/>12 Agents]
        Project_STD2[AI Project 2<br/>GPT-4o: 10K TPM]
    end
    
    Client -->|HTTPS| Gateway
    Gateway -->|80% Primary| CA_PTU
    Gateway -->|10% Spillover| CA_STD1
    Gateway -->|10% Spillover| CA_STD2
    
    CA_PTU --> Project_PTU
    CA_STD1 --> Project_STD1
    CA_STD2 --> Project_STD2
    
    style Gateway fill:#0078d4,color:#fff
    style CA_PTU fill:#4caf50,color:#fff
    style Project_PTU fill:#ff6b6b,color:#fff
    style CA_STD1 fill:#00bcf2,color:#000
    style CA_STD2 fill:#00bcf2,color:#000
```

**Implementation:**

1. **Deploy primary PTU project:**
   ```bash
   # Modify infra/resources.bicep to use PTU
   param openAiDeploymentType string = 'ProvisionedThroughput'
   param openAiCapacity int = 100  # 100 PTUs
   
   azd env new prod-primary
   azd up
   ```

2. **Deploy fallback standard projects:**
   ```bash
   azd env new prod-fallback-1
   azd up
   
   azd env new prod-fallback-2
   azd up
   ```

3. **Configure weighted APIM routing:**
   ```xml
   <set-variable name="backendIndex" value="@{
       var rand = new Random().Next(100);
       if (rand < 80) return "ptu";      // 80% to PTU
       if (rand < 90) return "std1";     // 10% to Standard 1
       return "std2";                     // 10% to Standard 2
   }" />
   
   <choose>
     <when condition="@(context.Variables["backendIndex"] == "ptu")">
       <set-backend-service base-url="https://ca-ptu.azurecontainerapps.io" />
     </when>
     <when condition="@(context.Variables["backendIndex"] == "std1")">
       <set-backend-service base-url="https://ca-std1.azurecontainerapps.io" />
     </when>
     <otherwise>
       <set-backend-service base-url="https://ca-std2.azurecontainerapps.io" />
     </otherwise>
   </choose>
   ```

**Characteristics:**
- ✅ **Guaranteed capacity** (100K TPM from PTU)
- ✅ **Burst capacity** (additional 20K TPM from standard)
- ✅ **Cost optimized** - PTU for baseline, pay-per-use for spikes
- ✅ **High availability** - Multiple fallback projects
- ⚠️ **Complex configuration** - Weighted routing + health checks
- ⚠️ **Higher base cost** - PTU commitment

**LLM Suite Integration:**
- **No changes required** - Single APIM endpoint
- APIM handles weighted routing automatically
- Transparent failover to standard projects

**Monthly Cost:** ~$25K (PTU: $21K + 2 standard projects: $4K)

**When to use:**
- Need guaranteed baseline capacity (100K TPM)
- Expect traffic spikes beyond PTU allocation
- Want cost predictability with burst capability
- Mission-critical workloads requiring SLA

---

### Comparison Matrix

| Strategy | Max TPM | HA | Cost/Month | LLM Suite Changes | Complexity | Best For |
|----------|---------|-----|-----------|-------------------|------------|----------|
| **Strategy 1: Vertical (PTU)** | 1M+ | Medium | $5K-50K | None | Low | Quick scaling, predictable load |
| **Strategy 2: Horizontal (APIM LB)** | 50K+ | High | $6K+ | None | Medium | Cost efficiency, fault tolerance |
| **Strategy 3: Horizontal (Client LB)** | 50K+ | High | $6K+ | Configuration + Logic | High | Advanced routing, tenant isolation |
| **Strategy 4: Hybrid (PTU + Multi)** | 120K+ | Very High | $25K+ | None | High | Mission-critical, guaranteed capacity |

---

### Recommendation by Workload

**Pilot / Development (< 10K TPM):**
- Use current single-project architecture
- Cost: ~$2K/month
- Scale strategy: None needed

**Production - Light (10K-30K TPM):**
- **Recommended:** Strategy 2 (Horizontal with APIM LB)
- Deploy 2-3 projects
- Cost: ~$4K-6K/month
- LLM Suite: No changes

**Production - Medium (30K-100K TPM):**
- **Recommended:** Strategy 1 (Vertical PTU)
- Single project with 50-100 PTUs
- Cost: ~$27K-54K/month
- LLM Suite: No changes

**Production - Heavy (100K+ TPM):**
- **Recommended:** Strategy 4 (Hybrid PTU + Multi-Project)
- PTU baseline + standard fallbacks
- Cost: ~$25K+ /month
- LLM Suite: No changes

**Enterprise - Mission Critical:**
- **Recommended:** Strategy 4 + Multi-region
- Deploy across 2-3 Azure regions
- Cost: ~$75K+/month
- LLM Suite: Optional geo-routing

---

## Multi-Region Deployment

Deploy your Bing Grounding API across multiple Azure regions for geographic load distribution, disaster recovery, and reduced latency for global users.

### Benefits

✅ **Geographic Load Distribution** - Spread traffic across regions  
✅ **Disaster Recovery** - Automatic failover if one region is down  
✅ **Lower Latency** - Users connect to nearest region  
✅ **Better Quota Utilization** - Separate TPM quotas per region  
✅ **Region Tracking** - Know which region served each request

### Architecture

```mermaid
graph TB
    subgraph Clients["Global Clients"]
        USClient[US Clients]
        EUClient[EU Clients]
    end
    
    subgraph APIM["Azure API Management (Global Gateway)"]
        Gateway[API Gateway<br/>• Geo-routing<br/>• Health Checks<br/>• Circuit Breaker]
    end
    
    subgraph EastUS["East US Region"]
        CA_East[Container App<br/>eastus]
        Foundry_East[AI Foundry<br/>5 Agents]
        Bing_East[Bing Grounding]
    end
    
    subgraph WestUS["West US Region"]
        CA_West[Container App<br/>westus]
        Foundry_West[AI Foundry<br/>5 Agents]
        Bing_West[Bing Grounding]
    end
    
    subgraph WestEU["West Europe Region"]
        CA_EU[Container App<br/>westeurope]
        Foundry_EU[AI Foundry<br/>5 Agents]
        Bing_EU[Bing Grounding]
    end
    
    USClient --> Gateway
    EUClient --> Gateway
    
    Gateway -->|Geo-routing| CA_East
    Gateway -->|Load balance| CA_West
    Gateway -->|Geo-routing| CA_EU
    
    CA_East --> Foundry_East
    CA_West --> Foundry_West
    CA_EU --> Foundry_EU
    
    Foundry_East --> Bing_East
    Foundry_West --> Bing_West
    Foundry_EU --> Bing_EU
    
    style Gateway fill:#0078d4,color:#fff
    style CA_East fill:#00bcf2,color:#000
    style CA_West fill:#00bcf2,color:#000
    style CA_EU fill:#00bcf2,color:#000
```

### Region Tracking

Each response includes metadata showing which region served the request:

```json
{
  "content": "AI-generated response...",
  "citations": [...],
  "metadata": {
    "agent_route": "gpt4o_2",
    "model": "gpt-4o",
    "agent_id": "asst_abc123...",
    "region": "westus"  ← Region identifier
  }
}
```

This enables:
- **Monitoring** - Track regional traffic distribution
- **Debugging** - Identify region-specific issues
- **Compliance** - Audit data residency requirements
- **Analytics** - Measure regional performance

### Deployment Steps

#### 1. Deploy Additional Region

```bash
# Create new environment for westus
azd env new westus
azd env set AZURE_LOCATION westus

# Deploy (creates full stack: Foundry, agents, Container App, etc.)
azd up

# Get the Container App URL
azd env get-values | Select-String "CONTAINER_APP"
```

**Output:** Container App URL like `ca-abc123.westus.azurecontainerapps.io`

#### 2. Configure APIM Multi-Region Backend

**Option A: Random Load Balancing (Simplest)**

Edit your APIM API operation policy (`/bing-grounding` or `/bing-grounding-mcp`):

```xml
<policies>
  <inbound>
    <set-variable name="backendUrl" value="@{
        var backends = new[] {
            "https://ca-vw5lt6yc7noze.eastus.azurecontainerapps.io",
            "https://ca-abc123.westus.azurecontainerapps.io"
        };
        var random = new Random();
        return backends[random.Next(backends.Length)];
    }" />
    <set-backend-service base-url="@((string)context.Variables["backendUrl"])" />
  </inbound>
</policies>
```

**Option B: Geo-Routing (User Location-Based)**

```xml
<policies>
  <inbound>
    <set-variable name="backendUrl" value="@{
        // Get client location from X-Forwarded-For or request headers
        string clientLocation = context.Request.Headers.GetValueOrDefault("X-Forwarded-For", "");
        
        // Route based on geography
        if (clientLocation.Contains("Europe") || clientLocation.Contains("EU"))
            return "https://ca-eu.westeurope.azurecontainerapps.io";
        else if (clientLocation.Contains("West") || clientLocation.Contains("Pacific"))
            return "https://ca-west.westus.azurecontainerapps.io";
        else
            return "https://ca-east.eastus.azurecontainerapps.io";
    }" />
    <set-backend-service base-url="@((string)context.Variables["backendUrl"])" />
  </inbound>
</policies>
```

**Option C: Health Check with Circuit Breaker (Production)**

```xml
<policies>
  <inbound>
    <base />
    <set-variable name="healthyBackends" value="@{
        var allBackends = new[] { 
            "https://ca-east.eastus.azurecontainerapps.io",
            "https://ca-west.westus.azurecontainerapps.io",
            "https://ca-eu.westeurope.azurecontainerapps.io"
        };
        var healthyList = new List<string>();
        
        // Check cached health status
        foreach (var backend in allBackends)
        {
            string cacheKey = "backend-health-" + backend;
            string healthStatus;
            
            if (context.Cache.TryGetValue(cacheKey, out healthStatus))
            {
                if (healthStatus == "healthy")
                    healthyList.Add(backend);
            }
            else
            {
                healthyList.Add(backend); // Assume healthy if no data
            }
        }
        
        return healthyList.Count > 0 ? healthyList : allBackends;
    }" />
    
    <!-- Random selection from healthy backends -->
    <set-backend-service base-url="@{
        var backends = (List<string>)context.Variables["healthyBackends"];
        var random = new Random();
        return backends[random.Next(0, backends.Count)];
    }" />
  </inbound>
  
  <outbound>
    <base />
    <!-- Cache health status based on response -->
    <choose>
      <when condition="@(context.Response.StatusCode >= 500)">
        <cache-store-value 
          key="@("backend-health-" + context.Request.Url.Host)" 
          value="unhealthy" 
          duration="60" />
      </when>
      <otherwise>
        <cache-store-value 
          key="@("backend-health-" + context.Request.Url.Host)" 
          value="healthy" 
          duration="300" />
      </otherwise>
    </choose>
  </outbound>
</policies>
```

#### 3. Test Multi-Region Setup

Run your test suite and observe region rotation:

```bash
python test_mcp.py
```

**Expected Output:**
```
Test 1: Region: eastus
Test 2: Region: westus
Test 3: Region: eastus
Test 4: Region: westus
...
```

### Required Resources Per Region

Each regional deployment needs:

| Resource | Required | Notes |
|----------|----------|-------|
| **AI Foundry Hub + Project** | ✅ Yes | New instance per region |
| **Bing Grounding** | ✅ Yes | Must be in same resource group as Foundry |
| **Container App** | ✅ Yes | This is the endpoint APIM routes to |
| **Container App Environment** | ✅ Yes | Required for Container Apps |
| **Log Analytics** | ✅ Yes | For Container App logging |
| **Storage Account** | Recommended | Better for region isolation |
| **Key Vault** | Recommended | Better availability |
| **Container Registry** | Optional | Can reuse from primary region |
| **APIM** | ❌ No | Single global gateway, reused across regions |

### Cost Considerations

**Per Additional Region:**
- AI Foundry Project: ~$0 (pay-per-use)
- GPT-4o deployment (10K TPM): ~$800/month
- Container App: ~$50-100/month
- Container Environment: ~$50/month
- Bing Grounding (Free tier): $0
- Storage + Key Vault + Logs: ~$50/month

**Total per region:** ~$950-1,000/month

**3-Region Setup (East US, West US, West Europe):**
- **Total:** ~$3,000/month
- **Benefits:** 30K TPM total capacity + geo-distribution + disaster recovery

### Best Practices

1. **Start with 2 regions** - Primary + failover
2. **Use health checks** - Implement circuit breaker pattern
3. **Monitor region distribution** - Track `metadata.region` field
4. **Set region-specific alerts** - Azure Monitor per region
5. **Test failover** - Regularly verify automatic failover works
6. **Cache DNS** - Consider Azure Front Door for advanced geo-routing

### Monitoring Multi-Region

**Azure Monitor Query (Log Analytics):**

```kusto
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| extend region = tostring(parse_json(Log_s).metadata.region)
| summarize count() by region, bin(TimeGenerated, 5m)
| render timechart
```

**APIM Analytics:**

Track backend distribution in APIM → Analytics → Custom Dimensions

---

## Prerequisites

### For Local Development
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Azure CLI** - [Install Guide](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Docker Desktop** (optional, for Docker Compose) - [Download](https://www.docker.com/products/docker-desktop)
- **Azure subscription** with access to:
  - Azure AI Foundry
  - Azure Container Apps
  - Azure API Management (optional, for production)

### For Azure Deployment
- **Azure Developer CLI (azd)** - [Install Guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- **Docker** (for building container images) - [Download](https://www.docker.com/products/docker-desktop)
- **Azure CLI** - [Install Guide](https://learn.microsoft.com/cli/azure/install-azure-cli)

### Azure Permissions Required
- **Subscription Contributor** or **Owner** role (to create resource groups and resources)
- **Azure AI Developer** or **Cognitive Services Contributor** (to create AI Foundry projects)

---

## Getting Started

### Local Development

1. **Create virtual environment**
   ```bash
   _env_create.bat
   ```

2. **Activate virtual environment**
   ```bash
   _env_activate.bat
   ```

3. **Install dependencies**
   ```bash
   _install.bat
   ```

4. **Configure environment variables**
   - Copy `env.sample` to `.env`
   - Fill in your Azure AI Agent credentials:
     ```env
     AZURE_AI_PROJECT_ENDPOINT="https://your-project.services.ai.azure.com/api/projects/yourProject"
     AZURE_AI_AGENT_ID="asst_xxxxxxxxxxxxx"
     ```

5. **Start the server**
   ```bash
   _run_server.bat
   ```

The API will be available at `http://localhost:8989`

### Docker Development

1. **Start with Docker Compose**
   ```bash
   _up.bat
   ```

2. **Stop Docker Compose**
   ```bash
   _down.bat
   ```

## API Endpoints

### GET /health

Health check endpoint that verifies the service is running.

**Example:**
```bash
curl http://localhost:8989/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "bing-grounding-api",
  "region": "eastus",
  "agents_loaded": 5
}
```

### POST /bing-grounding

Azure AI Agent wrapper endpoint with Bing grounding and citation support.

**Parameters:**
- `query` (string, required) - The user query to process

**Example:**
```bash
curl -X POST "http://localhost:8989/bing-grounding?query=What+happened+in+finance+today?"
```

**Success Response:**
```json
{
  "content": "Today in finance, the U.S. stock market saw a sharp decline, with the Dow Jones Industrial Average plunging almost 800 points (down 1.6%), and both the Nasdaq and S&P 500 also posting significant losses...",
  "citations": [
    {
      "id": 1,
      "type": "url",
      "url": "https://www.marketwatch.com/...",
      "title": "Stock Market News Today"
    },
    {
      "id": 2,
      "type": "url",
      "url": "https://www.cnbc.com/...",
      "title": "Federal Reserve Commentary"
    }
  ],
  "metadata": {
    "agent_route": "gpt4o_1",
    "model": "gpt-4o",
    "agent_id": "asst_abc123...",
    "region": "eastus"
  }
}
```

**Error Response:**
```json
{
  "error": "processing_error",
  "message": "Error details...",
  "metadata": {
    "agent_route": "gpt4o_1",
    "model": "gpt-4o",
    "agent_id": "asst_abc123...",
    "region": "eastus"
  }
}
```

**Features:**
- ✅ Grounded responses using Bing search
- ✅ Automatic citation extraction and formatting
- ✅ Clean content (inline citation markers removed)
- ✅ Structured JSON response
- ✅ Region tracking in metadata

### Response Metadata (Debugging Information)

Every API response includes a `metadata` object with debugging information:

| Field | Type | Description | Example | Purpose |
|-------|------|-------------|---------|---------|
| `region` | string | Azure region serving the request | `"eastus"`, `"westus"` | Track multi-region load balancing; identify regional issues |
| `model` | string | AI model used for generation | `"gpt-4o"`, `"gpt-4o-mini"` | Verify correct model deployment; compare model performance |
| `agent_route` | string | Agent pool identifier | `"gpt4o_1"`, `"gpt4o_5"` | Load balancing verification; identify agent-specific issues |
| `agent_id` | string | Azure AI Agent instance ID | `"asst_ElHsNtK1PSFxwha7..."` | Track specific agent behavior; troubleshoot agent errors |

**Why Metadata Matters for Debugging:**

1. **Multi-Region Deployments** - Know which region handled the request to diagnose latency or regional outages
2. **Load Balancing Verification** - Confirm APIM is distributing across agent pools (`gpt4o_1` through `gpt4o_5`)
3. **Performance Analysis** - Compare response times/quality across regions, models, or agents
4. **Error Troubleshooting** - Identify if errors are isolated to specific agents, regions, or models
5. **Compliance & Auditing** - Track data residency and model usage for regulatory requirements

**Example Success Response with Metadata:**
```json
{
  "content": "Azure AI Foundry is a comprehensive platform for building, deploying, and managing AI applications...",
  "citations": [
    {
      "id": 1,
      "type": "url",
      "url": "https://azure.microsoft.com/products/ai-studio",
      "title": "Azure AI Foundry Documentation"
    }
  ],
  "metadata": {
    "agent_route": "gpt4o_3",      // ← Agent pool #3 (load balanced)
    "model": "gpt-4o",              // ← Using GPT-4o model
    "agent_id": "asst_ElHsNtK1PSFxwha7tLWIFM7T",  // ← Specific agent instance
    "region": "eastus"              // ← Request served from East US
  }
}
```

**Example Error Response with Metadata:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Model deployment TPM limit exceeded. Please retry.",
  "metadata": {
    "agent_route": "gpt4o_2",      // ← Identifies which agent hit rate limit
    "model": "gpt-4o",
    "agent_id": "asst_abc123xyz",
    "region": "westus"              // ← Regional capacity issue
  }
}
```

**Debugging Use Case Examples:**

| Issue | What to Check | Solution |
|-------|---------------|----------|
| Slow responses from some requests | `region` field | May indicate one region is overloaded; add capacity or adjust APIM routing |
| Intermittent 429 errors | `agent_route` + `agent_id` | Specific agent may have lower TPM quota; increase quota or redistribute load |
| Quality variations | `model` + `agent_id` | Compare responses across agents; one may need prompt tuning |
| Regional compliance violation | `region` field | Audit logs show data processed in wrong region; update geo-routing policy |
| All requests to one agent | `agent_route` distribution | APIM load balancing broken; check backend pool configuration |

**How Metadata is Added (Implementation):**

The metadata is populated in [`app/main.py`](app/main.py):

```python
# Environment variable set by Bicep deployment
AZURE_REGION = os.getenv("AZURE_REGION", "unknown")

# On successful response (line ~133)
result["metadata"] = {
    "agent_route": agent_route,      # From URL path (gpt4o_1, gpt4o_2, etc.)
    "model": model,                  # From agent configuration
    "agent_id": AGENTS[agent_route]["agent_id"],  # From agent pool
    "region": AZURE_REGION           # From container environment
}

# On error response (line ~147)
"metadata": {
    "agent_route": agent_route,
    "model": model,
    "agent_id": AGENTS.get(agent_route, {}).get("agent_id", "unknown"),
    "region": AZURE_REGION
}
```

The `AZURE_REGION` environment variable is automatically set during deployment via Bicep ([`infra/resources.bicep`](infra/resources.bicep) line ~258):

```bicep
{
  name: 'AZURE_REGION'
  value: location  // Resolves to deployment region (eastus, westus, etc.)
}
```

---

## Testing the API

### Testing Direct API Endpoints

**Prerequisites:**
- Deployed service (local or Azure)
- Endpoint URL from deployment or `http://localhost:8989` for local

**Basic Health Check:**
```bash
# Local
curl http://localhost:8989/health

# Azure (Container App)
curl https://ca-vw5lt6yc7noze.eastus.azurecontainerapps.io/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "service": "bing-grounding-api",
  "region": "eastus",
  "agents_loaded": 5
}
```

**Test Query:**
```bash
# Local
curl -X POST "http://localhost:8989/bing-grounding/gpt4o_1?query=What+is+Azure+AI+Foundry?"

# Azure (Container App)
curl -X POST "https://ca-vw5lt6yc7noze.eastus.azurecontainerapps.io/bing-grounding/gpt4o_1?query=What+is+Azure+AI+Foundry?"
```

**Expected Response:**
```json
{
  "content": "Azure AI Foundry is Microsoft's unified platform...",
  "citations": [
    {
      "id": 1,
      "type": "url",
      "url": "https://azure.microsoft.com/products/ai-studio",
      "title": "Azure AI Foundry Overview"
    }
  ],
  "metadata": {
    "agent_route": "gpt4o_1",
    "model": "gpt-4o",
    "agent_id": "asst_ElHsNtK1PSFxwha7tLWIFM7T",
    "region": "eastus"
  }
}
```

---

### Testing MCP Endpoints (Model Context Protocol)

The MCP endpoint provides a standardized interface for AI model consumption through Azure API Management.

#### Prerequisites

1. **APIM Deployment** - API Management must be deployed (included in `azd up`)
2. **Subscription Key** - Required for APIM authentication

**Get Your Subscription Key:**

```bash
# Option 1: Azure Portal
# Navigate to: APIM → Subscriptions → "Built-in all-access subscription" → Show keys

# Option 2: Azure CLI
az apim subscription show \
  --resource-group rg-bing-grounding-mcp-dev \
  --service-name apim-xxxxxx \
  --sid master \
  --query primaryKey -o tsv
```

#### Configure Environment Variables

Add these to your `.env` file:

```bash
# MCP Server URL (from APIM)
APIM_MCP_SERVER_URL=https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp

# Subscription Key (from APIM portal or CLI)
APIM_SUBSCRIPTION_KEY=70f2c804e2ee4f749cea4b8ab3246e7e
```

#### Run MCP Tests

**Using the Test Script:**

```bash
# Activate virtual environment
_env_activate.bat

# Run tests
python test_mcp.py
```

**Expected Output:**

```
=== Testing MCP Endpoint ===
MCP Server URL: https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp

Test 1: What are the latest developments in AI?
RESULT: OK (10.6s)
  Region: eastus                              ← Azure region that processed request
  Model: gpt-4o                               ← AI model used for generation
  Agent Route: gpt4o_2                        ← Agent pool identifier (load balanced)
  Agent ID: asst_ElHsNtK1PSFxwha7tLWIFM7T     ← Specific agent instance ID
  Citations: 3                                ← Number of Bing grounding citations
    [1] AI News December 2025: In-Depth and Concise
    [2] Recent Developments in Generative AI Research
    [3] OpenAI Announces GPT-4.5

  Response: During December 2025, several notable advancements have been made in artificial intelligence...

Test 2: What happened in the stock market today?
RESULT: OK (8.2s)
  Region: westus                              ← Different region (multi-region load balancing)
  Model: gpt-4o
  Agent Route: gpt4o_3                        ← Different agent (load balanced across 5 agents)
  Agent ID: asst_xyz789...
  Citations: 4
    [1] Market Watch - December 17, 2025
    [2] CNBC Stock Market Update
    [3] Bloomberg Markets Summary
    [4] S&P 500 Daily Close

  Response: Today's stock market showed mixed performance, with the S&P 500 closing up 0.3%...

Test 3: Explain quantum computing
RESULT: OK (12.1s)
  Region: eastus                              ← Back to eastus (round-robin balancing)
  Model: gpt-4o
  Agent Route: gpt4o_1                        ← Cycling through agent pool
  Agent ID: asst_def456...
  Citations: 5
    [1] Quantum Computing Basics - Nature
    [2] IBM Quantum - Overview
    [3] Google Quantum AI Research
    [4] Quantum Algorithms Explained
    [5] Introduction to Qubits

  Response: Quantum computing is a revolutionary approach to computation that leverages quantum mechanics...

===========================
Tests completed: 5
Success: 5 (100%)
Failed: 0 (0%)
Average response time: 9.4s
===========================
```

**What to Look For in Test Output:**

| Field | What It Tells You | Good ✅ | Bad ❌ |
|-------|-------------------|---------|--------|
| **Region** | Geographic distribution | Rotating across regions (eastus, westus) | Always same region; "unknown" |
| **Agent Route** | Load balancing across agents | Cycling through gpt4o_1 to gpt4o_5 | Always same agent route |
| **Response Time** | Performance consistency | 5-15 seconds typical | >30 seconds; high variance |
| **Success Rate** | Overall reliability | 90%+ success | <80% success; frequent failures |
| **Citations** | Bing grounding quality | 3-5 citations per response | 0 citations; generic answers |

**Example Failed Test (for debugging):**

```
Test 4: What are the benefits of cloud computing?
RESULT: FAILED (2.5s) - rate_limit_exceeded
  Region: westus                              ← Helps isolate regional capacity issues
  Model: gpt-4o
  Agent Route: gpt4o_4                        ← This specific agent hit rate limit
  Agent ID: asst_ghi789...
  Error: Model deployment TPM limit exceeded  ← Error message

  Action: Increase TPM quota for westus deployment or adjust load balancing
```

#### Manual MCP Testing with cURL

**Test with Subscription Key Header:**

```bash
curl -X POST "https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp" \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "bing_grounding",
      "arguments": {
        "query": "What is the weather like today?"
      }
    },
    "id": 1
  }'
```

**Expected Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Today's weather varies by location. For specific weather information, please check your local forecast. As of December 17, 2025, many regions are experiencing seasonal winter conditions..."
      }
    ],
    "metadata": {
      "agent_route": "gpt4o_1",               // ← Which agent pool handled request
      "model": "gpt-4o",                      // ← Model used
      "agent_id": "asst_ElHsNtK1PSFxwha7tLWIFM7T",  // ← Specific agent instance
      "region": "eastus"                      // ← Region that processed request
    }
  }
}
```

**Pretty-Formatted for Debugging:**

```bash
# Add -v flag to see full request/response headers
curl -v -X POST "https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding-mcp/mcp" \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "bing_grounding",
      "arguments": {
        "query": "What is Azure AI Foundry?"
      }
    },
    "id": 1
  }' | jq '.'
```

**Expected Verbose Output (with debugging info):**

```
< HTTP/2 200
< content-type: application/json
< ocp-apim-trace-location: https://apimst...  ← APIM trace URL (if tracing enabled)
< x-backend-server: ca-vw5lt6yc7noze         ← Which Container App served request

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Azure AI Foundry is Microsoft's comprehensive platform for building, deploying, and managing AI applications. It provides a unified experience for developing custom AI solutions, integrating with Azure OpenAI Service, and leveraging pre-built AI models..."
      }
    ],
    "citations": [
      {
        "id": 1,
        "type": "url",
        "url": "https://azure.microsoft.com/en-us/products/ai-studio",
        "title": "Azure AI Foundry - Microsoft Azure"
      },
      {
        "id": 2,
        "type": "url",
        "url": "https://learn.microsoft.com/azure/ai-studio/",
        "title": "Azure AI Foundry documentation"
      }
    ],
    "metadata": {
      "agent_route": "gpt4o_2",
      "model": "gpt-4o",
      "agent_id": "asst_xyz789abc123def456",
      "region": "eastus"
    }
  }
}
```

**Debugging Checklist Using Metadata:**

✅ **Region is correct** - `"eastus"` or expected region (not `"unknown"`)  
✅ **Agent route is valid** - One of `gpt4o_1` through `gpt4o_5`  
✅ **Model is expected** - Should be `"gpt-4o"` for all agents  
✅ **Agent ID is populated** - Long string starting with `asst_`  
✅ **Citations exist** - Array with Bing search results  
✅ **Response time acceptable** - Typically 5-15 seconds  

❌ **Region shows "unknown"** - Container App missing AZURE_REGION env var  
❌ **Same agent every time** - APIM load balancing not working  
❌ **No citations** - Bing grounding not configured on agent  
❌ **Agent ID is "unknown"** - Agent pool configuration error

#### Common Testing Issues

**Issue 1: 401 Access Denied**

```json
{
  "statusCode": 401,
  "message": "Access denied due to missing subscription key"
}
```

**Solution:** Add subscription key to request headers:
```bash
-H "Ocp-Apim-Subscription-Key: YOUR_KEY_HERE"
```

**Issue 2: Empty Response / No Content**

**Solution:** 
1. Check MCP server URL is correct
2. Verify subscription key is valid
3. Check APIM backend is healthy:
   ```bash
   curl https://ca-vw5lt6yc7noze.eastus.azurecontainerapps.io/health
   ```

**Issue 3: Region Shows "unknown"**

**Solution:** Ensure `AZURE_REGION` environment variable is set in Container App configuration:
```bash
azd deploy  # Redeploy to update environment variables
```

#### Multi-Region Testing

When testing multi-region deployments, observe the `region` field to verify load balancing:

```bash
# Run multiple tests to see region rotation
for i in {1..10}; do
  echo "Test $i:"
  curl -s -X POST "https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp" \
    -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bing_grounding","arguments":{"query":"test"}},"id":'$i'}' \
    | jq -r '.result.metadata.region'
done
```

**Expected Output (with 2 regions):**
```
Test 1: eastus           ← First request to East US
Test 2: westus           ← Load balanced to West US
Test 3: eastus           ← Round-robin back to East US
Test 4: westus
Test 5: eastus
Test 6: westus
Test 7: eastus
Test 8: westus
Test 9: eastus
Test 10: westus
```

**Extract Full Metadata for Analysis:**

```bash
# Get complete metadata from multiple requests
for i in {1..5}; do
  echo "=== Request $i ==="
  curl -s -X POST "https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp" \
    -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bing_grounding","arguments":{"query":"test query"}},"id":'$i'}' \
    | jq '.result.metadata'
  echo ""
done
```

**Expected Output:**
```json
=== Request 1 ===
{
  "agent_route": "gpt4o_1",                    ← Agent pool #1
  "model": "gpt-4o",
  "agent_id": "asst_ElHsNtK1PSFxwha7tLWIFM7T",
  "region": "eastus"                           ← East US region
}

=== Request 2 ===
{
  "agent_route": "gpt4o_3",                    ← Different agent (load balanced)
  "model": "gpt-4o",
  "agent_id": "asst_Abc123Xyz789Def456Ghi",
  "region": "westus"                           ← West US region
}

=== Request 3 ===
{
  "agent_route": "gpt4o_2",                    ← Third agent
  "model": "gpt-4o",
  "agent_id": "asst_Qrs789Tuv012Wxy345Zab",
  "region": "eastus"                           ← Back to East US
}

=== Request 4 ===
{
  "agent_route": "gpt4o_5",                    ← Fifth agent
  "model": "gpt-4o",
  "agent_id": "asst_Mno456Pqr789Stu012Vwx",
  "region": "westus"                           ← Back to West US
}

=== Request 5 ===
{
  "agent_route": "gpt4o_4",                    ← Fourth agent
  "model": "gpt-4o",
  "agent_id": "asst_Cde345Fgh678Ijk901Lmn",
  "region": "eastus"                           ← East US again
}
```

**What This Shows:**
- ✅ **Region distribution** - Requests are being balanced across eastus and westus
- ✅ **Agent distribution** - Different agent routes (gpt4o_1 through gpt4o_5)
- ✅ **Unique agents** - Each agent_id is different
- ✅ **Consistent model** - All using gpt-4o

**Track Distribution Over Time:**

```bash
# Run 50 requests and count region distribution
echo "Testing 50 requests across regions..."
for i in {1..50}; do
  curl -s -X POST "https://apim-xxx.azure-api.net/bing-grounding-mcp/mcp" \
    -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bing_grounding","arguments":{"query":"test"}},"id":'$i'}' \
    | jq -r '.result.metadata.region'
done | sort | uniq -c
```

**Expected Output:**
```
     25 eastus          ← 50% of requests (good distribution)
     25 westus          ← 50% of requests (good distribution)
```

**If distribution is uneven:**
```
     45 eastus          ← 90% to one region
      5 westus          ← Only 10% to other region
```

**Possible causes:**
- APIM backend health checks marking one region unhealthy
- Circuit breaker tripped for one region
- Backend pool weights configured unevenly
- DNS caching or sticky sessions

#### Performance Testing

**Load test with multiple concurrent requests:**

```bash
# Install dependencies
pip install aiohttp asyncio

# Run load test (included in test_mcp.py)
python test_mcp.py --concurrent 10 --iterations 100
```

**Monitor:**
- Response times
- Success rate
- Region distribution
- Citation quality

---

## Azure AI Agent Configuration

This service wraps an Azure AI Agent that must be configured with Bing grounding capabilities.

### Setting Up Your Azure AI Agent

1. Create an Azure AI Project
2. Create an AI Agent with Bing grounding enabled
3. Copy the Project Endpoint and Agent ID
4. Set them as environment variables

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Project endpoint | Always | `https://your-project.services.ai.azure.com/api/projects/yourProject` |
| `AZURE_AI_AGENT_ID` | Azure AI Agent ID | Always | `asst_xxxxxxxxxxxxx` |
| `AZURE_CLIENT_ID` | Service Principal App ID | Local testing only | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_SECRET` | Service Principal Secret | Local testing only | `your-secret-value` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | Local testing only | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

### Authentication Setup

#### For Local Testing (Service Principal)

1. **Create a Service Principal**:
   ```bash
   az ad sp create-for-rbac --name "bing-grounding-api-sp" --role Contributor
   ```

   This returns:
   ```json
   {
     "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",          # AZURE_CLIENT_ID
     "password": "your-secret-here",                           # AZURE_CLIENT_SECRET
     "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"         # AZURE_TENANT_ID
   }
   ```

2. **Grant Access to AI Project**:
   ```bash
   # Get your subscription ID and resource group from Azure Portal
   az role assignment create \
     --assignee <appId-from-above> \
     --role "Cognitive Services User" \
     --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<ai-project-name>"
   ```

3. **Update your `.env` file**:
   ```env
   AZURE_AI_PROJECT_ENDPOINT=https://your-region.services.ai.azure.com/api/projects/your-project
   AZURE_AI_AGENT_ID=asst_xxxxxxxxxxxxx
   AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   AZURE_CLIENT_SECRET=your-secret-here
   AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

#### For Production (Managed Identity)

When deploying to Azure Container Apps, use Managed Identity instead:

1. **Enable Managed Identity** on your Container App:
   ```bash
   az containerapp identity assign \
     --name bing-grounding-api \
     --resource-group your-rg \
     --system-assigned
   ```

2. **Grant the Managed Identity access** to your AI Project:
   ```bash
   # Get the principal ID from the output above or:
   PRINCIPAL_ID=$(az containerapp identity show \
     --name bing-grounding-api \
     --resource-group your-rg \
     --query principalId -o tsv)

   # Grant access
   az role assignment create \
     --assignee $PRINCIPAL_ID \
     --role "Cognitive Services User" \
     --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<ai-project-name>"
   ```

3. **Deploy with only the required variables** (no client secrets):
   ```bash
   az containerapp create \
     --name bing-grounding-api \
     --resource-group your-rg \
     --environment your-env \
     --image your-registry.azurecr.io/bing-grounding-api:latest \
     --target-port 8989 \
     --ingress external \
     --system-assigned \
     --env-vars \
       AZURE_AI_PROJECT_ENDPOINT="your-endpoint" \
       AZURE_AI_AGENT_ID="your-agent-id"
   ```

**Important**: Don't set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, or `AZURE_TENANT_ID` in production. The `DefaultAzureCredential` will automatically use the Managed Identity.

## Project Structure

```
ai-bing-grounding-mcp/
├── agents/                         # AI Agent implementations
│   ├── __init__.py
│   ├── base_agent.py              # Abstract base class
│   └── bing_grounding.py          # Bing grounding agent
├── ai/                             # (Legacy - not used)
│   ├── __init__.py
│   └── azure_openai_client.py
├── app/                            # FastAPI application
│   ├── __init__.py
│   └── main.py                    # API endpoints
├── apim-policy.xml                # Main APIM policy (load balancing + circuit breaker)
├── apim-policy-with-healthcheck.xml  # Enhanced APIM policy with active health checks
├── apim-healthcheck-monitor.xml   # Optional active health monitoring policy
├── docker-compose.yaml            # Local Docker development
├── dockerfile                     # Container image definition
├── env.sample                     # Environment variable template
├── main.py                        # Application entry point
├── requirements.txt               # Python dependencies
├── _env_activate.bat              # Activate virtual environment
├── _env_create.bat                # Create virtual environment
├── _install.bat                   # Install dependencies
├── _run_server.bat                # Run FastAPI server
├── _up.bat                        # Start Docker Compose
├── _down.bat                      # Stop Docker Compose
└── README.md                      # This file
```

## Deployment to Azure

### Option 1: Automated Deployment with Azure Developer CLI (⭐ Recommended)

Azure Developer CLI (`azd`) automates the entire deployment process - from creating infrastructure to deploying applications. **This is the recommended approach** for both development and production deployments.

**What gets deployed automatically:**
- 🏗️ Azure Container Apps Environment + 3 Container App instances
- 🤖 Azure AI Foundry Hub & Project
- 🤖 12 GPT-4o AI agents with Bing grounding (created programmatically!)
- 🔐 Azure Container Registry
- 🔐 Key Vault with managed identities
- 📊 Log Analytics & Application Insights
- 🌐 Azure API Management (with load balancing and circuit breaker)
- 🔒 RBAC role assignments for all resources

**Total deployment time: ~8-15 minutes** ⏱️

---

#### Prerequisites

Before starting, ensure you have:

**Required:**
- Azure subscription with Contributor or Owner role
- Azure Developer CLI (`azd`) - [Install Guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- Azure CLI (`az`) - [Install Guide](https://learn.microsoft.com/cli/azure/install-azure-cli)
- Docker Desktop - [Download](https://www.docker.com/products/docker-desktop)

**Optional (for local development):**
- Python 3.11+ - [Download](https://www.python.org/downloads/)

**Quick install commands:**

```bash
# Windows (PowerShell)
powershell -ex AllSigned -c "Invoke-RestMethod 'https://aka.ms/install-azd.ps1' | Invoke-Expression"

# macOS/Linux
curl -fsSL https://aka.ms/install-azd.sh | bash
```

---

#### Step 1: Login to Azure

```bash
azd auth login
```

This opens a browser for authentication. Once authenticated, you're ready to deploy.

---

#### Step 2: Deploy Everything (One Command)

The simplest approach is to use `azd up`, which creates the environment, provisions infrastructure, and deploys the application in one step:

```bash
azd up
```

**You'll be prompted for:**
- **Environment name**: e.g., `dev`, `staging`, `prod`
  - Creates resource group: `rg-bing-grounding-mcp-{env-name}`
- **Azure subscription**: Select from your subscriptions
- **Azure location**: e.g., `eastus2`, `westus2`
- **Resource group confirmation**: If it already exists, confirm to continue

**What happens during `azd up`:**

1. **Preprovision Hooks** (~30 seconds)
   - ✅ Check resource group status
   - ✅ Register Microsoft.Bing resource provider

2. **Infrastructure Provisioning** (~5-10 minutes)
   - 🏗️ Create Container Registry
   - 🏗️ Create Container Apps Environment
   - 🏗️ Create AI Foundry Hub & Project
   - 🏗️ Deploy GPT-4o model
   - 🏗️ Create Key Vault, Storage, Log Analytics
   - 🏗️ Create API Management
   - 🏗️ Configure managed identities and RBAC

3. **Postprovision Hooks** (~2-3 minutes)
   - 🤖 **Create 12 GPT-4o AI agents with Bing grounding**
   - 📝 Save agent IDs to environment

4. **Application Deployment** (~3-5 minutes)
   - 🐳 Build Docker image
   - 📤 Push to Azure Container Registry
   - 🚀 Deploy to all 3 Container App instances

5. **Postdeploy Hooks** (~1 minute)
   - 🔄 Update additional container instances

**After completion**, you'll see:
```
SUCCESS: Your application was provisioned and deployed to Azure in X minutes.

You can view the application at https://ca-xxxxxx.eastus2.azurecontainerapps.io
```

That's it! Your API is live with 12 AI agents ready to serve requests.

---

#### Step 2 (Alternative): Separate Provision and Deploy

If you prefer more control, you can separate the steps:

**A. Create environment:**
   ```bash
   azd env new <environment-name>
   ```
   
   Examples:
   - `azd env new dev` → Creates `rg-bing-grounding-mcp-dev`
   - `azd env new prod` → Creates `rg-bing-grounding-mcp-prod`

**B. Provision infrastructure:**
   ```bash
   azd provision
   ```
   
   This creates all Azure resources and runs the postprovision hook to create AI agents.

**C. Deploy application:**
   ```bash
   azd deploy
   ```
   
   This builds and deploys the Docker container to all instances.

---

#### Step 3: Test Your Deployment

**Get your endpoint:**
```bash
azd env get-values | grep AZURE_CONTAINER_APP_ENDPOINT
# or
azd env get-values | findstr AZURE_CONTAINER_APP_ENDPOINT  # Windows
```

**Test the API:**
```bash
# Health check
curl https://ca-xxxxxx.eastus2.azurecontainerapps.io/health

# List agents
curl https://ca-xxxxxx.eastus2.azurecontainerapps.io/agents

# Query with Bing grounding
curl -X POST "https://ca-xxxxxx.eastus2.azurecontainerapps.io/bing-grounding/gpt4o_1?query=What+is+Azure+AI+Foundry?"
```

---

### Advanced Configuration

#### Pre-Configure Environment (Optional)

For CI/CD pipelines or scripted deployments, you can pre-configure values to avoid interactive prompts:
```bash
# Create environment
azd env new <env-name>

# Set subscription (find with: az account list -o table)
azd env set AZURE_SUBSCRIPTION_ID "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Set location
azd env set AZURE_LOCATION "eastus2"

# Now provision and deploy without prompts
azd up
```

**When to pre-configure:**
- ✅ CI/CD pipelines (GitHub Actions, Azure DevOps)
- ✅ Automated/scripted deployments
- ✅ Enforcing team standards
- ✅ Multi-environment deployments (dev/staging/prod)

#### View Environment Configuration

```bash
# Show all environment variables and outputs
azd env get-values

# Show deployment status and endpoints
azd show
```

---

### Common Workflows

#### Update Application Code

When you change Python code:

```bash
azd deploy
```

This rebuilds the Docker image and updates all Container App instances with zero downtime (~3-5 min).

#### Update Infrastructure

When you modify Bicep templates in `infra/`:

```bash
azd provision
```

This applies infrastructure changes without redeploying the application (~2-5 min).

#### View Logs

```bash
# Get resource group from environment
RG=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')

# Get Container App name
CA_NAME=$(azd env get-values | grep AZURE_CONTAINER_APP_NAME | cut -d'=' -f2 | tr -d '"')

# Stream logs
az containerapp logs show --name $CA_NAME --resource-group $RG --follow
```

#### Multiple Environments (Dev/Staging/Prod)

```bash
# Create and deploy dev environment
azd env new dev
azd env set AZURE_LOCATION "eastus2"
azd up

# Create and deploy prod environment
azd env new prod
azd env set AZURE_LOCATION "eastus"
azd up

# Switch between environments
azd env select dev
azd env select prod

# List all environments
azd env list
```

Each environment gets:
- Separate resource group: `rg-bing-grounding-mcp-{env}`
- Isolated Azure resources
- Local configuration in `.azure/{env}/`

#### Tear Down Resources

```bash
# Delete all Azure resources (with confirmation)
azd down

# Delete without prompts
azd down --force --purge
```

⚠️ **Warning**: This deletes the entire resource group and all resources.

---

### What Gets Created Automatically

When you run `azd up`, the following resources are provisioned:

| Resource | Purpose | Details |
|----------|---------|---------|
| **Resource Group** | Logical container | `rg-bing-grounding-mcp-{env}` |
| **Container Registry** | Docker images | Private registry for app images |
| **Container Apps (×3)** | Application hosting | 3 instances for load balancing |
| **AI Foundry Hub** | AI infrastructure | Hub for AI projects |
| **AI Foundry Project** | AI agent management | Contains GPT-4o deployment |
| **12 AI Agents** | Bing grounding agents | Created programmatically via API |
| **API Management** | API gateway | Load balancing + circuit breaker |
| **Key Vault** | Secrets management | Stores sensitive configuration |
| **Storage Account** | Data storage | For AI Hub and logs |
| **Log Analytics** | Monitoring | Centralized logging |
| **Application Insights** | APM | Performance monitoring |
| **Managed Identities** | Authentication | Secure service-to-service auth |

**Total cost estimate**: ~$200-400/month depending on usage and SKUs.

---

### Automated Hooks Explained

The solution uses `azd` hooks to automate setup tasks:

**Preprovision Hooks** (before infrastructure):
1. **Check resource group** - Prompts if RG already exists
2. **Register providers** - Registers `Microsoft.Bing` provider

**Postprovision Hooks** (after infrastructure):
1. **Create AI agents** - Programmatically creates 12 GPT-4o agents with Bing grounding
2. **Save agent IDs** - Stores IDs as environment variables

**Postdeploy Hooks** (after deployment):
1. **Update container instances** - Updates additional instances with latest image

These hooks are defined in `azure.yaml` and run automatically - **no manual intervention required**.

---

### Troubleshooting Deployment

**Issue**: `azd provision` fails with subscription error
- **Fix**: Set subscription explicitly: `azd env set AZURE_SUBSCRIPTION_ID "your-sub-id"`
- **Fix**: Ensure you have Contributor/Owner role on subscription

**Issue**: Container deployment fails with "image not found"
- **Fix**: Ensure Docker is running locally
- **Fix**: Check ACR credentials: `az acr login --name <registry-name>`

**Issue**: AI agents not created
- **Fix**: Check logs: `cat .azure/{env}/.env | grep AZURE_AI_AGENT`
- **Fix**: Manually run: `python scripts/postprovision_create_agents.py`

**Issue**: Authentication errors when accessing AI Project
- **Fix**: Verify managed identity has "Cognitive Services User" role
- **Fix**: Check RBAC assignments in Azure Portal

---

### Best Practices

✅ **Use `azd up`** for first deployment and combined infrastructure+code changes  
✅ **Use `azd deploy`** for code-only changes (faster)  
✅ **Use separate environments** for dev/staging/prod isolation  
✅ **Never commit `.azure/` folder** - it contains environment-specific configs  
✅ **Review outputs** after each deployment with `azd env get-values`  
✅ **Test in dev** before deploying to production  
✅ **Use managed identities** (default) instead of service principals  
✅ **Monitor costs** with Azure Cost Management  

---

📚 **Learn More:**
- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-services/)

---

### Option 2: Manual Deployment with Azure CLI

If you prefer manual control or can't use `azd`:

#### Step 1: Create Infrastructure

1. **Create resource group**:
   ```bash
   az group create --name rg-bing-grounding --location eastus
   ```

2. **Create Azure Container Registry**:
   ```bash
   az acr create \
     --resource-group rg-bing-grounding \
     --name acrbing123 \
     --sku Basic \
     --admin-enabled true
   ```

3. **Create AI Foundry Hub and Project** (via Azure Portal):
   - Go to https://ai.azure.com
   - Create a new Hub
   - Create a new Project within the Hub
   - Note the Project Endpoint

4. **Create Container App Environment**:
   ```bash
   az containerapp env create \
     --name cae-bing-grounding \
     --resource-group rg-bing-grounding \
     --location eastus
   ```

#### Step 2: Build and Push Container Image

1. **Login to ACR**:
   ```bash
   az acr login --name acrbing123
   ```

2. **Build and push image**:
   ```bash
   docker build -t acrbing123.azurecr.io/bing-grounding-api:latest .
   docker push acrbing123.azurecr.io/bing-grounding-api:latest
   ```

#### Step 3: Deploy Container Apps (Multiple Instances)

```bash
# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name acrbing123 --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name acrbing123 --query passwords[0].value -o tsv)

# Deploy instance 1
az containerapp create \
  --name bing-grounding-api-0 \
  --resource-group rg-bing-grounding \
  --environment cae-bing-grounding \
  --image acrbing123.azurecr.io/bing-grounding-api:latest \
  --target-port 8989 \
  --ingress external \
  --registry-server acrbing123.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --system-assigned \
  --env-vars \
    AZURE_AI_PROJECT_ENDPOINT="https://eastus.services.ai.azure.com/api/projects/yourProject" \
    AZURE_AI_AGENT_ID="asst_xxxxxxxxxxxxx"

# Repeat for instances 1 and 2
az containerapp create --name bing-grounding-api-1 ... (same parameters)
az containerapp create --name bing-grounding-api-2 ... (same parameters)
```

#### Step 4: Grant Managed Identity Access

```bash
# Get managed identity principal IDs
PRINCIPAL_ID_0=$(az containerapp identity show \
  --name bing-grounding-api-0 \
  --resource-group rg-bing-grounding \
  --query principalId -o tsv)

# Grant access to AI Project (repeat for each instance)
az role assignment create \
  --assignee $PRINCIPAL_ID_0 \
  --role "Cognitive Services User" \
  --scope "/subscriptions/<sub-id>/resourceGroups/rg-bing-grounding/providers/Microsoft.CognitiveServices/accounts/<ai-project-name>"
```

#### Step 5: Update Container App (for code changes)

```bash
# Build and push new image
docker build -t acrbing123.azurecr.io/bing-grounding-api:v2 .
docker push acrbing123.azurecr.io/bing-grounding-api:v2

# Update container apps
az containerapp update \
  --name bing-grounding-api-0 \
  --resource-group rg-bing-grounding \
  --image acrbing123.azurecr.io/bing-grounding-api:v2

# Repeat for other instances
```

---

### Local Development with Docker Compose

For local testing without Azure resources:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Note**: You'll still need valid Azure AI Project credentials in your `.env` file.

---

## Azure API Management Setup

### Load Balancing with Circuit Breaker

The service includes APIM policies for production deployments with multiple backend instances.

#### Architecture Features

```
┌──────────────────────────────────────────┐
│      [AZURE API MANAGEMENT]              │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Load Balancer + Circuit Breaker   │ │
│  │  • Session Affinity (Cookies)      │ │
│  │  • Health-Based Routing            │ │
│  │  • Auto Failover & Recovery        │ │
│  └─────────────────┬──────────────────┘ │
└────────────────────┼────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ... (N instances)
│ ✅ HEALTHY  │ │ ❌ UNHEALTHY│
│ Container   │ │ Container   │
│ App #1      │ │ App #2      │
│ [ACTIVE]    │ │ [REMOVED]   │
└─────────────┘ └─────────────┘
```

#### Features

1. **Session Affinity (Sticky Sessions)** - Clients stick to the same backend via cookies
2. **Circuit Breaker** - Unhealthy backends automatically removed from pool
3. **Auto-Recovery** - Backends rejoin when health is restored
4. **Health-Aware Routing** - Only route to healthy instances

### APIM Policy Files

Three policy files are included:

| File | Description | Use Case |
|------|-------------|----------|
| `apim-policy.xml` | Main load balancing policy with session affinity and circuit breaker | **Recommended** - Production deployments with multiple backends |
| `apim-policy-with-healthcheck.xml` | Enhanced policy with active health monitoring | High availability scenarios requiring proactive health checks |
| `apim-healthcheck-monitor.xml` | Standalone health check monitor | Separate monitoring pipeline |

### Setup Steps

1. **Update Backend URLs**

   In `apim-policy.xml`, replace the placeholder URLs with your Container App URLs:
   
   ```csharp
   var backends = new System.Collections.Generic.Dictionary<string, string> {
       { "0", "https://bing-grounding-api-1.azurecontainerapps.io" },
       { "1", "https://bing-grounding-api-2.azurecontainerapps.io" },
       { "2", "https://bing-grounding-api-3.azurecontainerapps.io" },
       { "3", "https://bing-grounding-api-4.azurecontainerapps.io" },
       { "4", "https://bing-grounding-api-5.azurecontainerapps.io" }
   };
   ```

2. **Apply Policy in Azure Portal**
   - Navigate to your APIM service
   - Go to your API → Design tab
   - Click "All operations" (or specific operations)
   - In "Inbound processing", click the code editor (`</>`)
   - Paste the policy XML from `apim-policy.xml`
   - Click Save

3. **Enable Internal Cache** (Required for circuit breaker)
   - Navigate to APIM → Caching
   - Enable built-in cache

### Circuit Breaker Behavior

#### ❌ UNHEALTHY - Marking Backends Unhealthy

A backend is marked **[UNHEALTHY]** (removed from pool for 30 seconds) when:
- Returns `500`, `502`, `503`, `504` (Server errors)
- Returns `429` (Rate limit exceeded)
- Returns `401` (Authentication failed)
- Connection timeout or failure

#### ✅ HEALTHY - Automatic Recovery

A backend is marked **[HEALTHY]** (rejoins pool) when:
- Returns `200 OK`
- Health status cache expires (after 30 seconds)

### Response Headers for Monitoring

The APIM policy adds headers for monitoring:

| Header | Description | Example |
|--------|-------------|---------|
| `X-APIM-Correlation-Id` | Unique request ID for tracing | `a1b2c3d4-...` |
| `X-Backend-Instance` | Backend that will handle request | `0`, `1`, `2`, `3`, `4` |
| `X-Served-By-Instance` | Backend that served the response | `0`, `1`, `2`, `3`, `4` |
| `X-Error-Backend-Instance` | Backend that caused error (on errors) | `2` |

**Cookies:**
- `APIM-Backend-Instance` - Session affinity cookie (24hr TTL)

### Testing Circuit Breaker

1. **Test Session Affinity**
   ```bash
   # First request - receives backend assignment
   curl -i https://your-apim.azure-api.net/bing-grounding

   # Check Set-Cookie header for: APIM-Backend-Instance=X
   
   # Subsequent requests with cookie go to same backend
   curl -i https://your-apim.azure-api.net/health \
     -H "Cookie: APIM-Backend-Instance=0"
   ```

2. **Test Failover**
   ```bash
   # Stop one Container App instance
   # Requests automatically route to healthy instances
   for i in {1..10}; do
     curl -s https://your-apim.azure-api.net/health | jq '.status'
   done
   ```

3. **Test Recovery**
   ```bash
   # Restart the instance
   # Wait 30 seconds for cache expiration
   # It automatically rejoins on first 200 response
   ```

### Production Checklist

- [ ] Internal cache enabled in APIM
- [ ] Multiple Container Apps deployed and running
- [ ] Health endpoints returning 200 OK
- [ ] Backend URLs updated in APIM policy
- [ ] Policy applied and tested
- [ ] Session affinity tested with cookies
- [ ] Circuit breaker tested with simulated failures
- [ ] Monitoring/alerts configured (Application Insights)
- [ ] Security: APIM subscription keys configured

---

## Agent Architecture

The wrapper uses an Abstract Base Class (ABC) pattern for extensibility:

```
agents/
├── base_agent.py           # Abstract base class for all agents
└── bing_grounding.py       # Bing grounding implementation
```

### BaseAgent (ABC)
```python
class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, endpoint: str = None, agent_id: str = None):
        self.endpoint = endpoint
        self.agent_id = agent_id
    
    @abstractmethod
    def chat(self, message: str) -> str:
        """Process a message and return response"""
        pass
```

### BingGroundingAgent

Concrete implementation that:
- Connects to Azure AI Agent Service
- Creates conversation threads
- Extracts and formats citations from Bing-grounded responses
- Returns structured JSON with content and citations
- Automatically cleans up threads after processing

## Extending with New Agents

To add a new agent type:

1. Create a new agent class that inherits from `BaseAgent`
2. Implement the `chat()` method
3. Add configuration to `.env`
4. Add a new endpoint in `app/main.py`

**Example:**
```python
class CustomAgent(BaseAgent):
    def __init__(self):
        endpoint = os.getenv("CUSTOM_AGENT_ENDPOINT")
        agent_id = os.getenv("CUSTOM_AGENT_ID")
        super().__init__(endpoint=endpoint, agent_id=agent_id)
    
    def chat(self, message: str) -> str:
        # Your custom implementation
        pass
```

## Troubleshooting

**Issue**: "AZURE_AI_PROJECT_ENDPOINT not set" error
- **Fix**: Copy `env.sample` to `.env` and fill in your credentials

**Issue**: Authentication failures with Azure AI Agent
- **Fix**: Ensure you're authenticated with Azure CLI: `az login`
- **Fix**: Verify DefaultAzureCredential has access to the AI Project

**Issue**: No citations in response
- **Fix**: Ensure your Azure AI Agent has Bing grounding enabled
- **Fix**: Check that the agent is configured correctly in Azure AI Studio

**Issue**: Thread cleanup failures
- **Fix**: These are logged but don't affect the response
- **Fix**: Check Azure AI Agent service limits and quotas

## Production Security Best Practices

The default deployment uses public endpoints for simplicity. For production workloads, you should enhance security with private networking and additional controls.

### Current Security Configuration

✅ **Managed Identity** - Container Apps authenticate to AI Project without secrets  
✅ **RBAC** - Role-based access control on all resources  
✅ **HTTPS Only** - All traffic encrypted in transit  
✅ **ACR Authentication** - Secured container registry access  
✅ **Key Vault RBAC** - Role-based Key Vault authorization  

⚠️ **Public Endpoints** - Resources accessible from internet (suitable for dev/test)

### Recommended Production Enhancements

#### 1. Private Networking with Virtual Network Integration

Add VNet integration to isolate resources from the public internet:

```bicep
// Add to resources.bicep

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: 'vnet-${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'subnet-containerapp'
        properties: {
          addressPrefix: '10.0.0.0/23'
          delegations: [
            {
              name: 'Microsoft.App/environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'subnet-privateendpoints'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Update Container App Environment with VNet
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: vnet.properties.subnets[0].id
      internal: true  // Make it internal for production
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}
```

#### 2. Private Endpoints for Azure Services

Secure backend services with private endpoints:

```bicep
// Private DNS Zones (add to resources.bicep)
resource privateDnsZoneStorage 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.core.windows.net'
  location: 'global'
  tags: tags
}

resource privateDnsZoneKeyVault 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
  tags: tags
}

resource privateDnsZoneACR 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.azurecr.io'
  location: 'global'
  tags: tags
}

// Link DNS Zones to VNet
resource privateDnsZoneLinkStorage 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneStorage
  name: 'link-storage'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// Private Endpoint for Storage Account
resource privateEndpointStorage 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-storage-${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[1].id  // Private endpoints subnet
    }
    privateLinkServiceConnections: [
      {
        name: 'storage-connection'
        properties: {
          privateLinkServiceId: storage.id
          groupIds: ['blob']
        }
      }
    ]
  }
}

// Private DNS Zone Group for Storage
resource privateDnsZoneGroupStorage 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: privateEndpointStorage
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config-storage'
        properties: {
          privateDnsZoneId: privateDnsZoneStorage.id
        }
      }
    ]
  }
}

// Update Storage Account to disable public access
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
    publicNetworkAccess: 'Disabled'  // Changed from default
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

// Repeat similar patterns for:
// - Key Vault private endpoint
// - Container Registry private endpoint
// - AI Hub/Project (if supported in your region)
```

#### 3. Network Security Groups (NSG)

Add NSG rules to control traffic:

```bicep
// Network Security Group (add to resources.bicep)
resource nsg 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: 'nsg-containerapp'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPSInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 1000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

// Associate NSG with Container App subnet
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  // ... existing properties
  properties: {
    // ... existing properties
    subnets: [
      {
        name: 'subnet-containerapp'
        properties: {
          addressPrefix: '10.0.0.0/23'
          networkSecurityGroup: {
            id: nsg.id
          }
          delegations: [
            {
              name: 'Microsoft.App/environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
    ]
  }
}
```

#### 4. Azure Front Door or Application Gateway

For production-grade ingress with WAF protection:

```bicep
// Azure Front Door with WAF (add to resources.bicep)
resource frontDoor 'Microsoft.Cdn/profiles@2023-05-01' = {
  name: 'fd-${uniqueString(resourceGroup().id)}'
  location: 'global'
  tags: tags
  sku: {
    name: 'Premium_AzureFrontDoor'  // Premium includes WAF
  }
  properties: {
    originResponseTimeoutSeconds: 60
  }
}

// WAF Policy
resource wafPolicy 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2022-05-01' = {
  name: 'waf${uniqueString(resourceGroup().id)}'
  location: 'global'
  tags: tags
  sku: {
    name: 'Premium_AzureFrontDoor'
  }
  properties: {
    policySettings: {
      enabledState: 'Enabled'
      mode: 'Prevention'
      requestBodyCheck: 'Enabled'
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'Microsoft_DefaultRuleSet'
          ruleSetVersion: '2.1'
        }
        {
          ruleSetType: 'Microsoft_BotManagerRuleSet'
          ruleSetVersion: '1.0'
        }
      ]
    }
  }
}

// Front Door Endpoint
resource fdEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2023-05-01' = {
  parent: frontDoor
  name: 'endpoint-${uniqueString(resourceGroup().id)}'
  location: 'global'
  properties: {
    enabledState: 'Enabled'
  }
}

// Origin Group (Container Apps)
resource originGroup 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = {
  parent: frontDoor
  name: 'containerapp-origins'
  properties: {
    loadBalancingSettings: {
      sampleSize: 4
      successfulSamplesRequired: 3
      additionalLatencyInMilliseconds: 50
    }
    healthProbeSettings: {
      probePath: '/health'
      probeRequestType: 'GET'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 30
    }
    sessionAffinityState: 'Enabled'  // Sticky sessions
  }
}

// Origins (one for each Container App instance)
resource origin0 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = {
  parent: originGroup
  name: 'origin-0'
  properties: {
    hostName: containerApp[0].properties.configuration.ingress.fqdn
    httpPort: 80
    httpsPort: 443
    originHostHeader: containerApp[0].properties.configuration.ingress.fqdn
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}
// Repeat for other instances...

// Route
resource route 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = {
  parent: fdEndpoint
  name: 'api-route'
  properties: {
    originGroup: {
      id: originGroup.id
    }
    supportedProtocols: ['Https']
    patternsToMatch: ['/*']
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
    httpsRedirect: 'Enabled'
  }
  dependsOn: [
    origin0
  ]
}

// Associate WAF with Endpoint
resource wafAssociation 'Microsoft.Cdn/profiles/securityPolicies@2023-05-01' = {
  parent: frontDoor
  name: 'waf-policy'
  properties: {
    parameters: {
      type: 'WebApplicationFirewall'
      wafPolicy: {
        id: wafPolicy.id
      }
      associations: [
        {
          domains: [
            {
              id: fdEndpoint.id
            }
          ]
          patternsToMatch: ['/*']
        }
      ]
    }
  }
}

// Output the Front Door URL
output frontDoorUrl string = 'https://${fdEndpoint.properties.hostName}'
```

#### 5. Diagnostic Settings and Monitoring

Enable comprehensive logging:

```bicep
// Diagnostic Settings for Container Apps (add to resources.bicep)
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = [for i in range(0, containerAppInstances): {
  name: 'diag-containerapp-${i}'
  scope: containerApp[i]
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        category: 'ContainerAppConsoleLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'ContainerAppSystemLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}]

// Alert Rules
resource cpuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-high-cpu'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when CPU usage exceeds 80%'
    severity: 2
    enabled: true
    scopes: [
      containerApp[0].id
      containerApp[1].id
      containerApp[2].id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighCPU'
          metricName: 'UsageNanoCores'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
        }
      ]
    }
    actions: []  // Add action groups here
  }
}
```

### Production Deployment Checklist

Security:
- [ ] VNet integration enabled
- [ ] Private endpoints configured for Storage, Key Vault, ACR
- [ ] Public network access disabled on backend services
- [ ] NSG rules configured and tested
- [ ] Azure Front Door or Application Gateway deployed
- [ ] WAF enabled in Prevention mode
- [ ] Managed identities used (no client secrets)
- [ ] RBAC permissions reviewed and minimized
- [ ] TLS 1.2 minimum enforced

Monitoring:
- [ ] Diagnostic settings enabled on all resources
- [ ] Log Analytics workspace configured
- [ ] Application Insights connected
- [ ] Alert rules configured for critical metrics
- [ ] Action groups created for notifications
- [ ] Workbooks created for dashboards

High Availability:
- [ ] Multiple Container App instances (minimum 3)
- [ ] Health probes configured
- [ ] Session affinity enabled (if stateful)
- [ ] Auto-scaling rules configured
- [ ] Cross-region deployment (optional)

Compliance:
- [ ] Data encryption at rest enabled
- [ ] Data encryption in transit enforced
- [ ] Audit logging enabled
- [ ] Backup and disaster recovery plan
- [ ] Access reviews scheduled
- [ ] Compliance tags applied

### Cost Optimization Tips

The default deployment is suitable for production but can be optimized:

1. **Container App Scaling**
   ```bicep
   scale: {
     minReplicas: 1  // Lower for dev, 2-3 for prod
     maxReplicas: 10
     rules: [
       {
         name: 'http-rule'
         http: {
           metadata: {
             concurrentRequests: '100'
           }
         }
       }
     ]
   }
   ```

2. **API Management SKU**
   - **Developer**: $50/month - Non-production only
   - **Basic**: $150/month - Light production workloads
   - **Standard**: $700/month - Production workloads
   - **Premium**: $3,000/month - Enterprise, multi-region

3. **Container Registry**
   - **Basic**: $5/month - Small projects
   - **Standard**: $20/month - Team projects
   - **Premium**: $50/month - Geo-replication, high throughput

4. **Storage Account**
   - Use lifecycle policies to archive old logs
   - Enable soft delete with shorter retention

## License

MIT

