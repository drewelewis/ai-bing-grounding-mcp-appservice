"""Test the REST API endpoint directly (bypassing MCP)"""
import httpx

# Test the REST API directly
rest_url = "https://apim-vw5lt6yc7noze.azure-api.net/bing-grounding/bing-grounding"
params = {
    "query": "What are the latest developments in Azure AI?",
    "model": "gpt-4o"
}

print("Testing REST API endpoint (not MCP)")
print(f"URL: {rest_url}")
print(f"Params: {params}")

try:
    response = httpx.post(rest_url, params=params, timeout=60.0)
    print(f"\n✅ Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"\n❌ Error: {e}")
