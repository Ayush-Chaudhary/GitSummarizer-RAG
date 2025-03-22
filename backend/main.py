#!/usr/bin/env python3
import os
import sys
import argparse
from typing import Dict, List, Any, Optional
import time

import threading
import queue

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
        llm_model: Optional[str] = None,
        status_callback: Optional[callable] = None
    ):
        """
        Initialize the GitSummarizer.
        
        Args:
            pinecone_api_key: API key for Pinecone. If None, uses config or env vars.
            openai_api_key: API key for OpenAI. If None, uses config or env vars.
            embedding_model: Name of the embedding model to use. If None, uses default from config.
            llm_model: Name of the language model to use. If None, uses default from config.
            status_callback: Callback function to update processing status.
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
        self.status_callback = status_callback
    
    def update_status(self, stage: str, message: str, progress: dict = None):
        """Update processing status through callback if available."""
        if self.status_callback:
            self.status_callback(self.current_repo_url, stage, message, progress)
    
    def load_repository(self, repo_url: str, skip_processing: bool = False) -> bool:
        """
        Load a repository, chunk its contents, and store in vector database.
        
        Args:
            repo_url: URL of the GitHub repository.
            skip_processing: If True, skip processing files and just restore state.
                            Used when restoring repositories after server restart.
            
        Returns:
            True if successful, False otherwise.
        """
        self.current_repo_url = repo_url
        print(f"Loading repository: {repo_url}")
        self.update_status("initializing", "Starting repository processing")
        
        # For repository restoration after restart, just set the state
        if skip_processing:
            print(f"Restoring repository state for {repo_url} (skipping processing)")
            self.loaded_repository = True
            self.update_status("ready", "Repository loaded and ready")
            return True
        
        # Clone repository
        try:
            self.update_status("cloning", "Cloning repository")
            repo_path = self.github_retriever.clone_repository(repo_url)
        except Exception as e:
            error_msg = f"Error cloning repository: {e}"
            print(error_msg)
            self.update_status("error", error_msg)
            return False
            
        # Get files
        try:
            self.update_status("scanning", "Scanning repository files")
            file_paths = self.github_retriever.get_file_paths(repo_path)
            print(f"Found {len(file_paths)} files in repository")
        except Exception as e:
            error_msg = f"Error getting file paths: {e}"
            print(error_msg)
            self.update_status("error", error_msg)
            return False
        
        # Process and chunk code files
        all_chunks = []
        processed_files = 0
        skipped_files = 0
        total_files = len(file_paths)
        
        self.update_status("processing", "Processing repository files", {
            "total_files": total_files,
            "processed_files": 0,
            "skipped_files": 0,
            "chunks_created": 0
        })
        
        # Track large files and problematic ones
        large_files = []
        problematic_files = []
        
        for file_idx, file_path in enumerate(file_paths):
            # Update progress
            if file_idx % 5 == 0 or file_idx == total_files - 1:
                self.update_status("processing", f"Processing file {file_idx+1}/{total_files}", {
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "skipped_files": skipped_files,
                    "chunks_created": len(all_chunks)
                })
            
            # Skip binary and unsupported files
            if utils.is_binary_file(file_path) or not utils.is_supported_file(file_path):
                print(f"Skipping binary or unsupported file: {file_path}")
                skipped_files += 1
                continue
                
            try:
                # Check file size before processing
                file_size = os.path.getsize(file_path)
                if file_size > 10000000:  # Skip files larger than ~10MB
                    large_files.append((file_path, file_size))
                    print(f"Skipping large file ({file_size/1000000:.2f}MB): {file_path}")
                    skipped_files += 1
                    continue
                    
                # Get file content
                content = self.github_retriever.read_file_content(file_path)
                if not content:
                    print(f"Skipping file with no content: {file_path}")
                    skipped_files += 1
                    continue
                    
                # Get language for chunking
                rel_path = os.path.relpath(file_path, repo_path)
                file_ext = utils.get_file_extension(file_path)
                
                if file_ext:
                    # Create chunker and chunk the file
                    chunker = CodeChunker(file_ext)

                    # Set up a cross-platform timeout using threading
                    # Create a queue for the results
                    result_queue = queue.Queue()
                    
                    # Create a function to process the file in a separate thread
                    def process_file():
                        try:
                            result = chunker.chunk(content)
                            result_queue.put(("success", result))
                        except Exception as e:
                            result_queue.put(("error", str(e)))
                    
                    # Create and start the worker thread
                    worker_thread = threading.Thread(target=process_file)
                    worker_thread.daemon = True
                    worker_thread.start()
                    
                    # Wait for the thread to finish or timeout (30 seconds)
                    worker_thread.join(timeout=30)
                    
                    # Check if the thread is still alive after timeout
                    if worker_thread.is_alive():
                        # Thread is still running after timeout - it's stuck
                        print(f"Warning: Chunking timed out for file: {rel_path}")
                        problematic_files.append((file_path, "timeout"))
                        skipped_files += 1
                        continue
                    
                    # Get the result if available
                    if not result_queue.empty():
                        status, result = result_queue.get()
                        if status == "error":
                            print(f"Error chunking {rel_path}: {result}")
                            problematic_files.append((file_path, result))
                            skipped_files += 1
                            continue
                        
                        # Process successful chunks
                        chunks = result
                        
                        # Add file path info to chunks
                        for chunk in chunks:
                            chunk['file_path'] = rel_path
                            
                        all_chunks.extend(chunks)
                        processed_files += 1
                        print(f"Processed {rel_path} - {len(chunks)} chunks")
                    else:
                        # This should not happen, but just in case
                        print(f"Error: No result returned for {rel_path}")
                        problematic_files.append((file_path, "no result returned"))
                        skipped_files += 1
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                problematic_files.append((file_path, str(e)))
                skipped_files += 1
        
        # Update final status
        self.update_status("storing", "Storing chunks in vector database", {
            "total_files": total_files,
            "processed_files": processed_files,
            "skipped_files": skipped_files,
            "chunks_created": len(all_chunks)
        })
        
        # Store chunks in vector store
        if all_chunks:
            try:
                self.vector_store.add_code_chunks(all_chunks, repo_url)
                print(f"Added {len(all_chunks)} chunks to vector store for {repo_url}")
                
                # Update state
                self.current_repo_path = repo_path
                self.loaded_repository = True
                
                self.update_status("ready", "Repository loaded and ready", {
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "skipped_files": skipped_files,
                    "chunks_created": len(all_chunks)
                })
                
                return True
            except Exception as e:
                error_msg = f"Error adding chunks to vector store: {e}"
                print(error_msg)
                self.update_status("error", error_msg)
                return False
        else:
            error_msg = "No chunks were created. Repository may be empty or contain unsupported file types."
            print(error_msg)
            self.update_status("error", error_msg)
            return False
    
    def query(self, query_text: str, k: int = None) -> str:
        """
        Query the repository with a natural language question.
        
        Args:
            query_text: The query text.
            k: Number of results to return. If None, uses the value from config.
            
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
                k=k  # k will be handled by vector_store.similarity_search
            )
            
            # Query the language model
            response = self.llm_interface.query(query_text, results)
            return response
        except Exception as e:
            return f"Error processing query: {e}"
    
    def get_repo_summary(self, k: int = None) -> str:
        """
        Generate a summary of the repository.
        
        Args:
            k: Number of key code snippets to use for summarization. If None, uses the value from config.
            
        Returns:
            Summary of the repository.
        """
        if not self.loaded_repository:
            return "Error: No repository loaded. Please load a repository first."
            
        # Check if summary generation is enabled in config
        if not config.GENERATE_SUMMARY:
            return "Summary generation is disabled in configuration. Set GENERATE_SUMMARY to True in config.py to enable."
            
        # Perform similarity search for key components
        try:
            results = self.vector_store.similarity_search(
                "main components architecture overview", 
                namespace=self.current_repo_url,
                k=k  # k will be handled by vector_store.similarity_search
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
    """Run the GitSummarizer in interactive mode."""
    try:
        summarizer = GitSummarizer()
        print("GitSummarizer Interactive Mode")
        print("------------------------------")
        
        # Input repository URL
        repo_url = input("Enter GitHub repository URL (e.g., https://github.com/username/repo): ").strip()
        
        # Load repository
        print(f"\nLoading repository: {repo_url}")
        if summarizer.load_repository(repo_url):
            print("Repository loaded successfully!")
        else:
            print("Failed to load repository. Exiting.")
            return
        
        # Generate summary if enabled in config
        if config.GENERATE_SUMMARY:
            print("\nGenerating repository summary...")
            summary = summarizer.get_repo_summary()
            print("\nREPOSITORY SUMMARY:")
            print("-------------------")
            print(summary)
        else:
            print("\nRepository summary generation is disabled in config. Set GENERATE_SUMMARY to True in config.py to enable.")
        
        # Interactive query loop
        while True:
            print("\nEnter a question about the repository (or 'quit' to exit):")
            query = input("> ").strip()
            
            if query.lower() in ["quit", "exit", "q"]:
                break
                
            # Process the query
            print("\nProcessing query...")
            response = summarizer.query(query)
            print("\nANSWER:")
            print("-------")
            print(response)
    
    except KeyboardInterrupt:
        print("\nExiting GitSummarizer...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up
        if 'summarizer' in locals():
            summarizer.cleanup()

def main():
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(description="GitSummarizer - Analyze and query GitHub repositories")
    
    # Setup commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Load repository command
    load_parser = subparsers.add_parser("load", help="Load a GitHub repository")
    load_parser.add_argument("repo_url", help="URL of the GitHub repository")
    load_parser.add_argument("--summary", action="store_true", help="Generate a summary of the repository")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query a loaded repository")
    query_parser.add_argument("query_text", help="Question about the repository")
    
    # Interactive mode
    interactive_parser = subparsers.add_parser("interactive", help="Run in interactive mode")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to interactive mode if no command is provided
    if not args.command:
        interactive_mode()
        return
    
    try:
        # Initialize the GitSummarizer
        summarizer = GitSummarizer()
        
        if args.command == "interactive":
            interactive_mode()
        elif args.command == "load":
            # Load repository
            print(f"Loading repository: {args.repo_url}")
            if summarizer.load_repository(args.repo_url):
                print("Repository loaded successfully!")
                
                # Generate summary if requested or enabled in config
                if args.summary or config.GENERATE_SUMMARY:
                    print("\nGenerating repository summary...")
                    summary = summarizer.get_repo_summary()
                    print("\nREPOSITORY SUMMARY:")
                    print("-------------------")
                    print(summary)
            else:
                print("Failed to load repository.")
        elif args.command == "query":
            # Query the repository
            print(f"Processing query: {args.query_text}")
            response = summarizer.query(args.query_text)
            print("\nANSWER:")
            print("-------")
            print(response)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up
        if 'summarizer' in locals():
            summarizer.cleanup()

if __name__ == "__main__":
    main() 