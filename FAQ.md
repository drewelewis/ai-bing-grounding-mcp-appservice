# Azure AI Agent Implementation - FAQ

## 1. Where is the OpenAI model configured?

**Q: There is no OpenAI model used for the agent definition in the code.**

**A:** The OpenAI model IS configured, but it's done at the **Azure AI Foundry portal level**, not in the code. The agent is retrieved by ID (`AZURE_AI_AGENT_ID`) in the code, and this agent already has its model configuration (GPT-4, GPT-4o, etc.) set up in Azure AI Foundry.

**How it works:**
- The agent definition in Azure AI Foundry includes the model selection (e.g., `gpt-4`, `gpt-4o`)
- The code simply references this pre-configured agent: `self.agent = self.project.agents.get_agent(self.agent_id)`
- This is the **recommended pattern** - infrastructure configuration stays in Azure, code stays clean

**To verify:**
1. Navigate to Azure AI Foundry portal
2. Find the agent with the ID from `AZURE_AI_AGENT_ID`
3. View the model configuration in the agent settings

---

## 2. Where are agent instructions and configurations?

**Q: There are no agent instructions, agent name, or other configurations to avoid hallucinations.**

**A:** These configurations are also set in the **Azure AI Foundry agent definition**, not in code:
- **Agent name** - Set in the portal
- **Agent instructions** (system prompt) - Set in the portal to control behavior and reduce hallucinations
- **Tools enabled** (Bing grounding) - Set in the portal
- **Model parameters** (temperature, top_p, etc.) - Set in the portal

**Benefits of this approach:**
- Follows **Infrastructure as Code principles**
- Agent is a reusable resource defined once, referenced many times
- Instructions can be updated without code changes or redeployment
- Separates configuration from application logic

**Alternative - Code-level control:**
If you need to create/configure agents programmatically, you can do so:

```python
agent = self.project.agents.create_agent(
    model="gpt-4o",
    name="Customer Support Agent",
    instructions="You are a helpful assistant that provides accurate information...",
    tools=[{"type": "bing_grounding"}],
    temperature=0.7
)
```

---

## 3. Does every API call create a new agent?

**Q: It seems like every call creates a new agent {default}, which defeats the purpose of state maintenance.**

**A:** This is **incorrect**. The code does NOT create a new agent per call:

- The agent is retrieved once: `self.agent = self.project.agents.get_agent(self.agent_id)`
- The agent is created **once** in Azure AI Foundry and **reused** for all requests
- The singleton pattern ensures one agent instance per application lifecycle:

```python
_agent_instance = None

def get_agent() -> BingGroundingAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BingGroundingAgent()
    return _agent_instance
```

**What IS created per call:** A new **thread** (conversation context), which is intentional for the current stateless API design.

---

## 4. How does thread management affect state maintenance?

**Q: New threads are created for each API invocation - doesn't this break state maintenance?**

**A:** This is **by design for a stateless REST API wrapper**. 

**Current architecture:**
- ✅ **Pro:** Each API call is independent (RESTful, scalable, no session management)
- ✅ **Pro:** No server-side state = easier to scale horizontally
- ✅ **Pro:** No cleanup needed for abandoned conversations
- ❌ **Con:** No conversation history across requests

**If you need stateful conversations, here are three options:**

### Option A - Client manages thread IDs (Recommended)

The client stores and sends the thread ID with each request:

```python
def chat(self, message: str, thread_id: str = None) -> dict:
    # Reuse existing thread or create new one
    if thread_id:
        thread = self.project.agents.threads.retrieve(thread_id)
    else:
        thread = self.project.agents.threads.create()
    
    # Add message and process
    self.project.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=message
    )
    
    # Return thread_id for next request
    return {
        "thread_id": thread.id,
        "content": response_text,
        "citations": citations
    }
```

**Client usage:**
```json
// First request
{"message": "What is Azure?"}
// Response includes: {"thread_id": "thread_abc123", "content": "..."}

// Subsequent requests
{"message": "Tell me more", "thread_id": "thread_abc123"}
```

### Option B - Session-based storage

Store thread IDs in a database (Redis, Cosmos DB) keyed by session/user ID:

```python
def chat(self, message: str, user_id: str) -> dict:
    # Retrieve or create thread for this user
    thread_id = redis_client.get(f"thread:{user_id}")
    
    if thread_id:
        thread = self.project.agents.threads.retrieve(thread_id)
    else:
        thread = self.project.agents.threads.create()
        redis_client.set(f"thread:{user_id}", thread.id, ex=3600)
    
    # Process message
    # ...
```

### Option C - Avoid agents entirely

Use standard OpenAI Chat Completion API where the client sends full conversation history:

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def chat(messages: list) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,  # Client sends full history
        temperature=0.7
    )
    return {"content": response.choices[0].message.content}
```

**Client usage:**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "What is Azure?"},
    {"role": "assistant", "content": "Azure is Microsoft's cloud platform..."},
    {"role": "user", "content": "Tell me more"}
  ]
}
```

---

## 5. Does this architecture avoid Azure AI Foundry agent framework complexity?

**Q: Even with APIM frontend, this doesn't avoid the AI Foundry agent framework complexity.**

**A:** This is a **valid concern**. The agent framework does add complexity:

**Added complexity:**
- Thread management overhead
- Agent service dependencies
- Citation parsing logic
- Additional API calls (create thread, create message, create run, list messages)
- Error handling for agent-specific failures
- Asynchronous run processing

**When the agent framework is worth it:**
- ✅ Need Bing grounding for real-time web search
- ✅ Need file search/retrieval capabilities
- ✅ Need code interpreter functionality
- ✅ Want Azure to manage conversation state
- ✅ Need built-in citations and source tracking

**When a simple OpenAI API wrapper is better:**
- ✅ Need full control over the conversation flow
- ✅ Client already manages conversation state
- ✅ Want simpler architecture and debugging
- ✅ Don't need specialized tools (Bing, file search, etc.)
- ✅ Want to minimize dependencies

---

## Alternative Implementation: Simple OpenAI API Wrapper

If you want to avoid the Azure AI Agent framework entirely, here's a simpler approach:

```python
import os
from openai import AzureOpenAI
from typing import List, Dict

class SimpleOpenAIWrapper:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: int = 1000) -> dict:
        """
        Process chat completion with message history
        
        Args:
            messages: List of message objects with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        
        Returns:
            Dict with 'content' and usage statistics
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {"error": str(e)}
```

**Benefits:**
- No threads or agents to manage
- Client controls conversation state
- Simpler error handling
- Direct OpenAI API compatibility
- Easier to test and debug

**Trade-offs:**
- No built-in Bing grounding (would need to implement separately)
- No automatic citation tracking
- Client responsible for conversation history management
- No advanced agent features (file search, code interpreter)

---

## Recommendation Summary

Choose your implementation based on requirements:

| Requirement | Recommended Approach |
|------------|---------------------|
| Need Bing grounding with citations | Azure AI Agent (current implementation) |
| Need simple chat completion | OpenAI API wrapper |
| Need stateful conversations | Option A (client manages thread ID) or Option B (server-side session store) |
| Need to avoid framework complexity | OpenAI API wrapper |
| Need file search or code interpreter | Azure AI Agent |
| Need full control and simplicity | OpenAI API wrapper |

---

## Environment Variables Reference

### For Azure AI Agent (current implementation):
```env
AZURE_AI_PROJECT_ENDPOINT=https://<your-project>.api.azureml.ms
AZURE_AI_AGENT_ID=<your-agent-id>
```

### For Simple OpenAI API wrapper:
```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_KEY=<your-api-key>
AZURE_OPENAI_MODEL=gpt-4o
```

---

## Additional Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure OpenAI Service Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Azure AI Agent SDK](https://learn.microsoft.com/python/api/azure-ai-projects/)
