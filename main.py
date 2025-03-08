#!/usr/bin/env python3
import os
import sys
import argparse
from typing import Dict, List, Any, Optional
import time

from github_retriever import GitHubRetriever
from code_chunker import CodeChunker
from vector_store import VectorStore
from llm_interface import LLMInterface
import utils
import config

class GitSummarizer:
    """
    Main class for GitSummarizer-RAG application.
    Orchestrates repository retrieval, code chunking, vector storage, and query answering.
    """
    
    def __init__(
        self,
        pinecone_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        llm_model: Optional[str] = None
    ):
        """
        Initialize the GitSummarizer.
        
        Args:
            pinecone_api_key: API key for Pinecone. If None, uses config or env vars.
            openai_api_key: API key for OpenAI. If None, uses config or env vars.
            embedding_model: Name of the embedding model to use. If None, uses default from config.
            llm_model: Name of the language model to use. If None, uses default from config.
        """
        # Set API keys from arguments or environment variables
        if pinecone_api_key:
            os.environ["PINECONE_API_KEY"] = pinecone_api_key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            
        # Initialize components
        self.github_retriever = GitHubRetriever()
        self.vector_store = VectorStore(
            embedding_model=embedding_model
        )
        self.llm_interface = LLMInterface(
            model_name=llm_model
        )
        
        # State tracking
        self.current_repo_url = None
        self.current_repo_path = None
        self.loaded_repository = False
    
    def load_repository(self, repo_url: str) -> bool:
        """
        Load a repository, chunk its contents, and store in vector database.
        
        Args:
            repo_url: URL of the GitHub repository.
            
        Returns:
            True if successful, False otherwise.
        """
        print(f"Loading repository: {repo_url}")
        
        # Clone repository
        try:
            repo_path = self.github_retriever.clone_repository(repo_url)
        except Exception as e:
            print(f"Error cloning repository: {e}")
            return False
            
        # Get files
        file_paths = self.github_retriever.get_file_paths(repo_path)
        
        # Process and chunk code files
        all_chunks = []
        for file_path in file_paths:
            # Skip binary and unsupported files
            if utils.is_binary_file(file_path) or not utils.is_supported_file(file_path):
                continue
                
            try:
                # Get file content
                content = self.github_retriever.read_file_content(file_path)
                if not content:
                    continue
                    
                # Get language for chunking
                rel_path = os.path.relpath(file_path, repo_path)
                file_ext = utils.get_file_extension(file_path)
                
                if file_ext:
                    # Create chunker and chunk the file
                    chunker = CodeChunker(file_ext)
                    chunks = chunker.chunk(content)
                    
                    # Add file path info to chunks
                    for chunk in chunks:
                        chunk['file_path'] = rel_path
                        
                    all_chunks.extend(chunks)
                    print(f"Processed {rel_path} - {len(chunks)} chunks")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        # Store chunks in vector store
        if all_chunks:
            try:
                self.vector_store.add_code_chunks(all_chunks, repo_url)
                print(f"Added {len(all_chunks)} chunks to vector store for {repo_url}")
                
                # Update state
                self.current_repo_url = repo_url
                self.current_repo_path = repo_path
                self.loaded_repository = True
                
                return True
            except Exception as e:
                print(f"Error adding chunks to vector store: {e}")
                return False
        else:
            print("No chunks were created. Repository may be empty or contain unsupported file types.")
            return False
    
    def query(self, query_text: str, k: int = 5) -> str:
        """
        Query the repository with a natural language question.
        
        Args:
            query_text: The query text.
            k: Number of results to return.
            
        Returns:
            Answer from the language model.
        """
        if not self.loaded_repository:
            return "Error: No repository loaded. Please load a repository first."
            
        # Perform similarity search
        try:
            results = self.vector_store.similarity_search(
                query_text, 
                namespace=self.current_repo_url,
                k=k
            )
            
            # Query the language model
            response = self.llm_interface.query(query_text, results)
            return response
        except Exception as e:
            return f"Error processing query: {e}"
    
    def get_repo_summary(self, k: int = 10) -> str:
        """
        Generate a summary of the repository.
        
        Args:
            k: Number of key code snippets to use for summarization.
            
        Returns:
            Summary of the repository.
        """
        if not self.loaded_repository:
            return "Error: No repository loaded. Please load a repository first."
            
        # Perform similarity search for key components
        try:
            results = self.vector_store.similarity_search(
                "main components architecture overview", 
                namespace=self.current_repo_url,
                k=k
            )
            
            # Generate summary
            summary = self.llm_interface.generate_summary(self.current_repo_url, results)
            return summary
        except Exception as e:
            return f"Error generating summary: {e}"
    
    def cleanup(self):
        """
        Clean up resources.
        """
        if self.github_retriever:
            self.github_retriever.cleanup()

def interactive_mode():
    """
    Run the application in interactive mode.
    """
    print("=" * 80)
    print("GitSummarizer-RAG - Interactive Mode")
    print("=" * 80)
    
    # Check API keys
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not pinecone_api_key:
        pinecone_api_key = input("Enter your Pinecone API key: ").strip()
        os.environ["PINECONE_API_KEY"] = pinecone_api_key
        
    if not openai_api_key:
        openai_api_key = input("Enter your OpenAI API key: ").strip()
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
    # Initialize GitSummarizer
    summarizer = GitSummarizer(
        pinecone_api_key=pinecone_api_key,
        openai_api_key=openai_api_key
    )
    
    # Get repository URL
    repo_url = input("\nEnter GitHub repository URL: ").strip()
    
    print("\nLoading repository...")
    success = summarizer.load_repository(repo_url)
    
    if not success:
        print("Failed to load repository. Exiting.")
        summarizer.cleanup()
        return
    
    print("\nRepository loaded successfully!")
    
    # Show available models
    available_models = summarizer.llm_interface.available_models()
    print("\nAvailable language models:")
    for i, model in enumerate(available_models):
        print(f"{i+1}. {model}")
    
    # Option to change model
    model_choice = input(f"\nChoose model (1-{len(available_models)}, default is 1): ").strip()
    if model_choice and model_choice.isdigit() and 1 <= int(model_choice) <= len(available_models):
        model_idx = int(model_choice) - 1
        summarizer.llm_interface = LLMInterface(model_name=available_models[model_idx])
        print(f"Using model: {available_models[model_idx]}")
    
    # Generate summary
    print("\nGenerating repository summary...")
    summary = summarizer.get_repo_summary()
    print("\nREPOSITORY SUMMARY:")
    print("-" * 80)
    print(summary)
    print("-" * 80)
    
    # Interactive query loop
    print("\nYou can now ask questions about the repository.")
    print("Type 'exit' or 'quit' to exit.")
    
    while True:
        query = input("\nYour question: ").strip()
        
        if query.lower() in ['exit', 'quit']:
            break
            
        if not query:
            continue
            
        print("\nThinking...")
        start_time = time.time()
        response = summarizer.query(query)
        elapsed = time.time() - start_time
        
        print("\nANSWER:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        print(f"Response time: {elapsed:.2f} seconds")
    
    # Cleanup
    print("\nCleaning up...")
    summarizer.cleanup()
    print("Done. Thank you for using GitSummarizer-RAG!")

def main():
    """
    Main entry point for the application.
    """
    parser = argparse.ArgumentParser(description="GitSummarizer-RAG: A tool for summarizing and querying GitHub repositories.")
    parser.add_argument("--repo", type=str, help="GitHub repository URL")
    parser.add_argument("--query", type=str, help="Query to run against the repository")
    parser.add_argument("--summary", action="store_true", help="Generate a summary of the repository")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", type=str, help="Language model to use")
    
    args = parser.parse_args()
    
    # If no arguments provided, default to interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
        return
    
    # Run in interactive mode if specified
    if args.interactive:
        interactive_mode()
        return
    
    # Running in CLI mode
    summarizer = GitSummarizer(llm_model=args.model)
    
    # Load repository
    if args.repo:
        print(f"Loading repository: {args.repo}")
        success = summarizer.load_repository(args.repo)
        
        if not success:
            print("Failed to load repository. Exiting.")
            summarizer.cleanup()
            return
            
        print("Repository loaded successfully!")
        
        # Generate summary if requested
        if args.summary:
            print("\nGenerating repository summary...")
            summary = summarizer.get_repo_summary()
            print("\nREPOSITORY SUMMARY:")
            print("-" * 80)
            print(summary)
            print("-" * 80)
        
        # Run query if provided
        if args.query:
            print(f"\nQuery: {args.query}")
            response = summarizer.query(args.query)
            print("\nANSWER:")
            print("-" * 80)
            print(response)
            print("-" * 80)
    else:
        print("Error: No repository URL provided. Use --repo to specify a repository URL.")
    
    # Cleanup
    summarizer.cleanup()

if __name__ == "__main__":
    main() 