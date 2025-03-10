#!/usr/bin/env python3
import os
import sys
import json
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from main import GitSummarizer

# Initialize FastAPI app
app = FastAPI(
    title="GitSummarizer-RAG API",
    description="API for analyzing GitHub repositories using RAG techniques",
    version="1.0.0"
)

# Enable CORS to allow frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active repositories and their summarizers
active_repos = {}

# Pydantic models for request/response
class RepoRequest(BaseModel):
    repo_url: str
    
class QueryRequest(BaseModel):
    repo_url: str
    query: str
    
class RepoResponse(BaseModel):
    success: bool
    message: str
    
class QueryResponse(BaseModel):
    answer: str
    
class SummaryResponse(BaseModel):
    summary: str
    
# Background task to load repository
def load_repository_task(repo_url: str):
    try:
        # Initialize GitSummarizer
        summarizer = GitSummarizer()
        success = summarizer.load_repository(repo_url)
        
        if success:
            # Store the summarizer for this repository
            active_repos[repo_url] = summarizer
        else:
            print(f"Failed to load repository: {repo_url}")
    except Exception as e:
        print(f"Error loading repository {repo_url}: {e}")

# API Routes
@app.post("/api/repository", response_model=RepoResponse)
async def load_repository(background_tasks: BackgroundTasks, repo_request: RepoRequest):
    """
    Load a GitHub repository for analysis.
    This is an asynchronous operation that will run in the background.
    """
    repo_url = repo_request.repo_url
    
    # Check if already loaded or loading
    if repo_url in active_repos:
        return {"success": True, "message": "Repository already loaded"}
    
    # Start loading in the background
    background_tasks.add_task(load_repository_task, repo_url)
    
    return {"success": True, "message": "Repository loading started"}

@app.get("/api/repository/{repo_url}/status")
async def get_repository_status(repo_url: str):
    """
    Check if a repository is loaded and ready for querying.
    """
    # URL decode the repo_url if needed
    
    if repo_url in active_repos:
        return {"loaded": True, "ready": True}
    else:
        return {"loaded": False, "ready": False}

@app.post("/api/query", response_model=QueryResponse)
async def query_repository(query_request: QueryRequest):
    """
    Query a loaded repository with a natural language question.
    """
    repo_url = query_request.repo_url
    
    if repo_url not in active_repos:
        raise HTTPException(status_code=404, detail="Repository not loaded")
    
    summarizer = active_repos[repo_url]
    answer = summarizer.query(query_request.query)
    
    return {"answer": answer}

@app.get("/api/repository/{repo_url}/summary", response_model=SummaryResponse)
async def get_repository_summary(repo_url: str):
    """
    Get a summary of a loaded repository.
    """
    # URL decode the repo_url if needed
    
    if repo_url not in active_repos:
        raise HTTPException(status_code=404, detail="Repository not loaded")
    
    summarizer = active_repos[repo_url]
    summary = summarizer.get_repo_summary()
    
    return {"summary": summary}

@app.delete("/api/repository/{repo_url}")
async def unload_repository(repo_url: str):
    """
    Unload a repository to free up resources.
    """
    # URL decode the repo_url if needed
    
    if repo_url in active_repos:
        summarizer = active_repos[repo_url]
        summarizer.cleanup()
        del active_repos[repo_url]
        return {"success": True, "message": "Repository unloaded"}
    else:
        return {"success": False, "message": "Repository not found"}

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Check if the API is running.
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    # Run the API server
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 