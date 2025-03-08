import os
from typing import List, Dict, Any, Optional, Union
import uuid

from pinecone import Pinecone
from langchain.schema import Document
from langchain_pinecone import PineconeVectorStore
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

import config

class VectorStore:
    """
    Class for managing the vector store operations using Pinecone.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        index_name: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize the VectorStore.
        
        Args:
            api_key: Pinecone API key. If None, uses value from config or environment variable.
            index_name: Name of the Pinecone index to use. If None, uses value from config.
            embedding_model: Name of the embedding model to use. If None, uses default from config.
        """
        self.api_key = api_key or config.PINECONE_API_KEY or os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("Pinecone API key is required")
            
        self.index_name = index_name or config.PINECONE_INDEX_NAME
        self.embedding_model = embedding_model or config.DEFAULT_EMBEDDING_MODEL
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        
        # Check if index exists, if not create it
        self._create_index_if_not_exists()
        
        # Initialize embeddings
        if "openai" in self.embedding_model.lower():
            self.embeddings = OpenAIEmbeddings()
        else:
            # Use HuggingFace embeddings by default
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        
        # Initialize the vector store
        self.vector_store = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings
        )
    
    def _create_index_if_not_exists(self):
        """
        Create a Pinecone index if it doesn't already exist.
        """
        # List existing indexes
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        # Create index if it doesn't exist
        if self.index_name not in existing_indexes:
            self.pc.create_index(
                name=self.index_name,
                dimension=768,  # Default dimension for sentence-transformers
                metric="cosine"
            )
            print(f"Created new Pinecone index: {self.index_name}")
    
    def add_documents(self, documents: List[Dict[str, Any]], namespace: Optional[str] = None) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents to add. Each document should be a dictionary with 'content' key.
            namespace: Optional namespace for the documents.
            
        Returns:
            List of IDs for the added documents.
        """
        # Convert documents to LangChain format
        langchain_docs = []
        for doc in documents:
            metadata = {k: v for k, v in doc.items() if k != 'content'}
            
            # Ensure content exists
            if 'content' not in doc:
                continue
                
            # Add a unique ID if metadata doesn't have one
            if 'id' not in metadata:
                metadata['id'] = str(uuid.uuid4())
                
            langchain_docs.append(
                Document(
                    page_content=doc['content'],
                    metadata=metadata
                )
            )
        
        # Add to vector store
        if namespace:
            ids = self.vector_store.add_documents(langchain_docs, namespace=namespace)
        else:
            ids = self.vector_store.add_documents(langchain_docs)
            
        return ids
    
    def add_code_chunks(self, code_chunks: List[Dict[str, Any]], repo_url: str) -> List[str]:
        """
        Add code chunks to the vector store.
        
        Args:
            code_chunks: List of code chunks to add. Each should be a dictionary from the CodeChunker.
            repo_url: URL of the repository for namespace.
            
        Returns:
            List of IDs for the added documents.
        """
        documents = []
        for i, chunk in enumerate(code_chunks):
            documents.append({
                'content': chunk['chunk'],
                'id': f"{repo_url}-chunk-{i}",
                'start_line': chunk['start_line'],
                'end_line': chunk['end_line'],
                'token_count': chunk['token_count'],
                'repo_url': repo_url,
                'chunk_index': i
            })
            
        return self.add_documents(documents, namespace=repo_url)
    
    def similarity_search(self, query: str, namespace: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Perform a similarity search with a query.
        
        Args:
            query: The query to search for.
            namespace: Optional namespace to search in.
            k: Number of results to return.
            
        Returns:
            List of Document objects with the search results.
        """
        if namespace:
            return self.vector_store.similarity_search(query, k=k, namespace=namespace)
        else:
            return self.vector_store.similarity_search(query, k=k)
    
    def delete_documents(self, ids: List[str], namespace: Optional[str] = None):
        """
        Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete.
            namespace: Optional namespace to delete from.
        """
        if namespace:
            self.vector_store.delete(ids, namespace=namespace)
        else:
            self.vector_store.delete(ids)
    
    def delete_namespace(self, namespace: str):
        """
        Delete an entire namespace from the vector store.
        
        Args:
            namespace: The namespace to delete.
        """
        try:
            # Get pinecone index
            index = self.pc.Index(self.index_name)
            index.delete(namespace=namespace)
            print(f"Deleted namespace: {namespace}")
        except Exception as e:
            print(f"Error deleting namespace: {e}") 