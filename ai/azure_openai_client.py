import os
import openai

class client:
    def __init__(self):

        # Check if the environment variables are set
        azure_endpoint = os.environ.get("OPENAI_ENDPOINT")
        if azure_endpoint is None:
            raise ValueError("Please set the environment variable 'OPENAI_ENDPOINT' to your Azure OpenAI endpoint.")

        azure_api_key = os.environ.get("OPENAI_API_KEY")
        if azure_api_key is None:
            raise ValueError("Please set the environment variable 'OPENAI_API_KEY' to your Azure OpenAI API key.")
        
        api_version = os.environ.get("OPENAI_API_VERSION")
        if api_version is None:
            raise ValueError("Please set the environment variable 'OPENAI_API_VERSION' to your Azure OpenAI API version.")
        
        model_deployment_name = os.environ.get("OPENAI_MODEL_DEPLOYMENT_NAME")
        if model_deployment_name is None:
            raise ValueError("Please set the environment variable 'OPENAI_MODEL_DEPLOYMENT_NAME' to your Azure OpenAI model deployment name.")
        
        self.model_deployment_name = model_deployment_name
        
        self.client = openai.AzureOpenAI(
                api_key=azure_api_key,  
                api_version=api_version,
                azure_endpoint=azure_endpoint
        )

    def completion(self, messages: list, max_tokens: int = 40000):
        response = self.client.chat.completions.create(
            model=self.model_deployment_name,
            messages=messages,
            max_completion_tokens=max_tokens
        )
        return response

    def embedding(self, input: str, model: str):
        response = self.client.embeddings.create(
            input=input,
            model=model
        )
        return response
