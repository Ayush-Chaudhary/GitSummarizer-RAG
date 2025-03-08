import os
from typing import Dict, List, Any, Optional, Union
import time

from openai import OpenAI
from langchain.schema import Document

import config

class LLMInterface:
    """
    Interface for Language Models to answer queries.
    """
    
    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the LLM interface.
        
        Args:
            model_name: Name of the language model to use. If None, uses default from config.
            api_key: API key for the language model provider. If None, uses config or env vars.
        """
        self.model_name = model_name or config.DEFAULT_LLM_MODEL
        
        # Set API key based on model provider
        if "openai" in self.model_name.lower() or self.model_name in config.LLM_MODELS and config.LLM_MODELS[self.model_name]["provider"] == "openai":
            self.api_key = api_key or config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            self.provider = "openai"
        else:
            # Default to OpenAI if provider not specified
            self.api_key = api_key or config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            self.provider = config.LLM_MODELS.get(self.model_name, {}).get("provider", "openai")
        
        # Initialize clients based on provider
        if self.provider == "openai":
            self.client = OpenAI(api_key=self.api_key)
    
    def available_models(self) -> List[str]:
        """
        Get a list of available models.
        
        Returns:
            List of available model names.
        """
        return list(config.LLM_MODELS.keys())
    
    def query(self, query: str, context: Optional[List[Document]] = None, temperature: Optional[float] = None) -> str:
        """
        Query the language model with context from retrieved documents.
        
        Args:
            query: The query to answer.
            context: Optional list of retrieved documents to provide as context.
            temperature: Control the randomness of the output. If None, uses config default.
            
        Returns:
            The language model's response.
        """
        # Format context from documents if provided
        context_str = ""
        if context:
            context_str = "Context information:\n"
            for i, doc in enumerate(context):
                # Format with document content and metadata
                file_info = doc.metadata.get('repo_url', 'Unknown repo')
                line_info = f"(Lines {doc.metadata.get('start_line', '?')}-{doc.metadata.get('end_line', '?')})"
                context_str += f"\n---\nDocument {i+1} from {file_info} {line_info}:\n{doc.page_content}\n---\n"
        
        # Set temperature based on input or config
        if temperature is None:
            temperature = config.LLM_MODELS.get(self.model_name, {}).get("temperature", 0.3)
            
        # Get max_tokens from config
        max_tokens = config.LLM_MODELS.get(self.model_name, {}).get("max_tokens", 1000)
        
        # Formulate the prompt
        system_prompt = (
            "You are a helpful assistant that provides accurate and detailed information about code repositories. "
            "You specialize in explaining code, architecture, and concepts from GitHub repositories. "
            "Be concise but thorough in your responses. If you don't know the answer, say so."
        )
        
        user_prompt = f"{context_str}\n\nQuestion: {query}\n\nAnswer:"
        
        # Call the appropriate provider
        if self.provider == "openai":
            return self._query_openai(system_prompt, user_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _query_openai(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
        """
        Query OpenAI model.
        
        Args:
            system_prompt: System prompt to control assistant behavior.
            user_prompt: User prompt with context and query.
            temperature: Control randomness of output.
            max_tokens: Maximum number of tokens to generate.
            
        Returns:
            The model's response.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error querying OpenAI: {e}")
            return f"Error: Unable to get a response from the language model. Please try again later. ({str(e)})"
    
    def generate_summary(self, repo_url: str, context: List[Document]) -> str:
        """
        Generate a summary of the repository.
        
        Args:
            repo_url: URL of the repository to summarize.
            context: List of key documents from the repository to inform the summary.
            
        Returns:
            Generated summary of the repository.
        """
        system_prompt = (
            "You are an expert software developer tasked with summarizing a GitHub repository. "
            "Focus on the overall architecture, main components, and how they interact. "
            "Keep your summary concise but informative, highlighting key design patterns and technologies used."
        )
        
        # Prepare context from documents
        context_str = f"Repository: {repo_url}\n\nCode snippets to analyze:\n"
        for i, doc in enumerate(context):
            context_str += f"\n---\nSnippet {i+1}:\n{doc.page_content}\n---\n"
            
        user_prompt = f"{context_str}\n\nPlease provide a comprehensive summary of this repository, including:\n"
        user_prompt += "1. The main purpose of the project\n"
        user_prompt += "2. Key components and their relationships\n"
        user_prompt += "3. Technologies and libraries used\n"
        user_prompt += "4. Overall architecture pattern (if identifiable)\n\nSummary:"
        
        # Use higher temperature for more creative summary
        temperature = 0.7
        max_tokens = 1500
        
        return self._query_openai(system_prompt, user_prompt, temperature, max_tokens) 