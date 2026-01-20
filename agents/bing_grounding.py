import os
import re
import json
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from agents.base_agent import BaseAgent

class BingGroundingAgent(BaseAgent):
    """Agent that uses Azure AI Agent with Bing grounding capabilities"""
    
    def __init__(self, endpoint: str = None, agent_id: str = None):
        # Initialize base class with configuration from environment or parameters
        endpoint = endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        agent_id = agent_id or os.getenv("AZURE_AI_AGENT_ID")
        
        super().__init__(endpoint=endpoint, agent_id=agent_id)
        
        # Initialize Azure AI Project Client
        self.project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=self.endpoint
        )
        
        self.agent = self.project.agents.get_agent(self.agent_id)
    
    def chat(self, message: str) -> str:
        """Process a single message using Azure AI Agent with Bing grounding"""
        thread = None
        debug_info = {
            "run_status": None,
            "run_error": None,
            "message_count": 0,
            "has_assistant_message": False,
            "raw_response": None,
            "annotations_count": 0
        }
        
        try:
            # Create a new thread for this conversation
            thread = self.project.agents.threads.create()
            debug_info["thread_id"] = thread.id
            
            # Add the user message
            self.project.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            # Run the agent
            run = self.project.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self.agent.id
            )
            
            debug_info["run_status"] = run.status
            debug_info["run_id"] = run.id
            
            if run.status == "failed":
                debug_info["run_error"] = str(run.last_error) if run.last_error else "Unknown error"
                return json.dumps({
                    "content": "",
                    "citations": [],
                    "debug": debug_info
                }, indent=2)
            
            # Get the response messages
            response_messages = self.project.agents.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING
            )
            
            messages_list = list(response_messages)
            debug_info["message_count"] = len(messages_list)
            
            # Get the last assistant message with citations
            for msg in reversed(messages_list):
                if msg.role == "assistant" and msg.text_messages:
                    debug_info["has_assistant_message"] = True
                    text_message = msg.text_messages[-1]
                    response_text = text_message.text.value
                    debug_info["raw_response"] = response_text[:200] + "..." if len(response_text) > 200 else response_text
                    
                    # Remove inline citation markers like 【3:0†source】
                    response_text = re.sub(r'【\d+:\d+†[^】]+】', '', response_text)
                    
                    # Extract and format citations if available
                    citations = []
                    if hasattr(text_message.text, 'annotations') and text_message.text.annotations:
                        debug_info["annotations_count"] = len(text_message.text.annotations)
                        for idx, annotation in enumerate(text_message.text.annotations, 1):
                            citation = {}
                            
                            # Try different annotation types
                            if hasattr(annotation, 'file_citation') and annotation.file_citation:
                                citation = {
                                    "id": idx,
                                    "type": "file",
                                    "quote": annotation.file_citation.quote
                                }
                            elif hasattr(annotation, 'url_citation') and annotation.url_citation:
                                citation = {
                                    "id": idx,
                                    "type": "url",
                                    "url": annotation.url_citation.url,
                                    "title": getattr(annotation.url_citation, 'title', annotation.url_citation.url)
                                }
                            elif hasattr(annotation, 'url'):
                                citation = {
                                    "id": idx,
                                    "type": "url",
                                    "url": annotation.url
                                }
                            
                            if citation:
                                citations.append(citation)
                    
                    # Return JSON response with debug info
                    result = {
                        "content": response_text.strip(),
                        "citations": citations,
                        "debug": debug_info
                    }
                    
                    return json.dumps(result, indent=2)
            
            # No assistant message found
            debug_info["no_response_reason"] = "No assistant message in thread"
            return json.dumps({
                "content": "",
                "citations": [],
                "debug": debug_info
            }, indent=2)
            
        except Exception as e:
            debug_info["exception"] = str(e)
            debug_info["exception_type"] = type(e).__name__
            return json.dumps({
                "content": "",
                "citations": [],
                "error": "processing_error",
                "message": str(e),
                "debug": debug_info
            }, indent=2)
        finally:
            # Clean up the thread after processing
            if thread:
                try:
                    self.project.agents.threads.delete(thread.id)
                except Exception as cleanup_error:
                    # Log but don't fail the request if cleanup fails
                    print(f"Warning: Failed to delete thread {thread.id}: {cleanup_error}")


# Create singleton instance
_agent_instance = None

def get_agent() -> BingGroundingAgent:
    """Get or create the BingGroundingAgent singleton instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BingGroundingAgent()
    return _agent_instance


def chat(message: str) -> str:
    """Convenience function for chat endpoint"""
    agent = get_agent()
    return agent.chat(message)