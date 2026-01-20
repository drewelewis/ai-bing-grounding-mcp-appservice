"""
MCP Server Reliability Test - Multiple test runs
"""

import asyncio
import os
import time
from dotenv import load_dotenv
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()


async def run_single_test(test_num, query):
    """Run a single MCP test"""
    url = os.getenv("APIM_MCP_SERVER_URL")
    subscription_key = os.getenv("APIM_SUBSCRIPTION_KEY")
    
    # Display question first
    print(f"\n{'='*70}")
    print(f"Test {test_num}: {query}")
    print(f"{'='*70}")
    
    start_time = time.time()
    try:
        # Create headers with subscription key
        headers = {}
        if subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = subscription_key
        
        async with httpx.AsyncClient(timeout=150.0, headers=headers) as client:  # Increased timeout
            async with streamable_http_client(url, http_client=client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    
                    # Initialize
                    await session.initialize()
                    
                    # Call bingGrounding
                    print("Calling MCP endpoint...")
                    response = await asyncio.wait_for(
                        session.call_tool(
                            "bingGrounding",
                            arguments={
                                "model": "gpt-4o",
                                "query": query
                            }
                        ),
                        timeout=90.0  # Increased from 60s to 90s for complex queries
                    )
                    
                    elapsed = time.time() - start_time
                    
                    # Debug: Check response structure
                    if not response.content:
                        print(f"RESULT: FAILED ({elapsed:.1f}s) - Empty response.content")
                        print(f"  Response type: {type(response)}")
                        print(f"  Response: {response}")
                        return False
                    
                    # Parse response
                    for content in response.content:
                        print(f"DEBUG: content type={type(content)}, hasattr text={hasattr(content, 'text')}")
                        if hasattr(content, 'text'):
                            print(f"DEBUG: content.text length={len(content.text)}, preview={content.text[:200]}")
                            import json
                            try:
                                data = json.loads(content.text)
                            except json.JSONDecodeError as e:
                                print(f"RESULT: FAILED ({elapsed:.1f}s) - JSON Parse Error")
                                print(f"  Error: {e}")
                                print(f"  Raw Response: {content.text[:500]}")
                                return False
                            
                            # Metadata is always in the same place now
                            metadata = data.get('metadata', {})
                            agent_route = metadata.get('agent_route', 'unknown')
                            agent_id = metadata.get('agent_id', 'unknown')
                            model = metadata.get('model', 'unknown')
                            region = metadata.get('region', 'unknown')
                            
                            # Check if this is an error response from the API
                            error = data.get('error', '')
                            error_msg = data.get('message', '')
                            citations = data.get('citations', [])
                            content_text = data.get('content', '')
                            debug_info = data.get('debug', {})
                            
                            if error:
                                print(f"RESULT: FAILED ({elapsed:.1f}s) - API Error: {error}")
                                print(f"  Region: {region}")
                                print(f"  Model: {model}")
                                print(f"  Agent Route: {agent_route}")
                                print(f"  Agent ID: {agent_id}")
                                print(f"  Error Message: {error_msg[:200]}")
                                if debug_info:
                                    print(f"  Debug Info:")
                                    print(f"    Run Status: {debug_info.get('run_status')}")
                                    print(f"    Run Error: {debug_info.get('run_error')}")
                                    print(f"    Message Count: {debug_info.get('message_count')}")
                                    print(f"    Has Assistant Msg: {debug_info.get('has_assistant_message')}")
                                    if debug_info.get('raw_response'):
                                        print(f"    Raw Response: {debug_info.get('raw_response')[:100]}")
                                return False
                            
                            # Check if this is a valid response
                            is_valid = (
                                content_text and 
                                len(content_text) > 50 and 
                                not content_text.startswith("I'm sorry") and
                                not content_text.startswith("I cannot")
                            )
                            
                            if not is_valid:
                                print(f"RESULT: FAILED ({elapsed:.1f}s) - No valid response")
                                print(f"  Region: {region}")
                                print(f"  Model: {model}")
                                print(f"  Agent Route: {agent_route}")
                                print(f"  Agent ID: {agent_id}")
                                print(f"  Response: {content_text[:100]}")
                                if debug_info:
                                    print(f"  Debug Info:")
                                    print(f"    Run Status: {debug_info.get('run_status')}")
                                    if debug_info.get('run_error'):
                                        print(f"    Run Error: {debug_info.get('run_error')}")
                                    print(f"    Message Count: {debug_info.get('message_count')}")
                                    print(f"    Has Assistant Msg: {debug_info.get('has_assistant_message')}")
                                    print(f"    Annotations: {debug_info.get('annotations_count')}")
                                return False
                            
                            print(f"RESULT: OK ({elapsed:.1f}s)")
                            print(f"  Region: {region}")
                            print(f"  Model: {model}")
                            print(f"  Agent Route: {agent_route}")
                            print(f"  Agent ID: {agent_id}")
                            print(f"  Citations: {len(citations)}")
                            if citations:
                                for i, cite in enumerate(citations, 1):
                                    print(f"    [{i}] {cite.get('title', 'N/A')[:80]}")
                            else:
                                print("    WARNING: No citations returned")
                            print(f"  Response: {content_text[:150]}...")
                            return True
                    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"RESULT: TIMEOUT ({elapsed:.1f}s)")
        print(f"  Query: {query}")
        print(f"  URL: {url}")
        return False
    except ExceptionGroup as eg:
        elapsed = time.time() - start_time
        print(f"RESULT: FAILED ({elapsed:.1f}s) - ExceptionGroup")
        print(f"  Number of exceptions: {len(eg.exceptions)}")
        for i, exc in enumerate(eg.exceptions, 1):
            print(f"  Exception {i}: {type(exc).__name__}")
            print(f"    Message: {str(exc)[:300]}")
            # Print traceback info for better debugging
            import traceback
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
            print(f"    Traceback (last 5 lines):")
            for line in tb_lines[-5:]:
                print(f"      {line.strip()}")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"RESULT: FAILED ({elapsed:.1f}s) - {type(e).__name__}")
        print(f"  Error: {str(e)[:300]}")
        print(f"  Query: {query}")
        print(f"  URL: {url}")
        # Print full traceback for debugging
        import traceback
        print(f"  Traceback:")
        tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
        for line in tb_lines[-10:]:
            print(f"    {line.strip()}")
        return False


async def main():
    url = os.getenv("APIM_MCP_SERVER_URL")
    if not url:
        print("ERROR: Set APIM_MCP_SERVER_URL in .env")
        return
    
    print(f"MCP Server Reliability Test")
    print(f"Testing: {url}\n")
    
    # Test queries - diverse topics with relative time terms to force Bing grounding
    queries = [
        "What are the top news headlines today?",
        "What happened in France today?",
        "What tech products were announced in the last 3 days?",
        "What movies are trending this week?",
        "What breaking US news happened in the last 24 hours?",
        "What interest rates changed recently?",
        "What is the weather forecast for this weekend in New York City?",
        "What AI advancements were made this month?",
        "What xbox news has come out recently?",
        "How did the us stock market perform today?",
        "What new music albums dropped this week?",
        "What scientific discoveries were announced recently?",
        "What cybersecurity threats emerged in the past few days?",
        "What environmental news came out this week?",
        "What major business deals were announced yesterday?"
    ]
    
    print(f"Running {len(queries)} tests...\n")
    
    results = []
    for i, query in enumerate(queries, 1):
        success = await run_single_test(i, query)
        results.append(success)
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Summary
    print(f"\n{'='*50}")
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    success_rate = sum(results)/len(results)*100 if results else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Count tests with citations
    if success_rate < 100:
        print(f"\n⚠️  Some tests failed - check responses above")
    
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
