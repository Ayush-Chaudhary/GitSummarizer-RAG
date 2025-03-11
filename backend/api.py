#!/usr/bin/env python3
import os
import sys
import json
from typing import Optional, List, Dict, Any
import time
from datetime import datetime
import atexit

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from main import GitSummarizer

# File to store repository status
STATUS_FILE = "repository_status.json"
# File to track server restarts due to code changes
CODE_CHANGE_FLAG = ".code_changed"

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
# Store detailed status of repositories with timestamps
repository_status = {}

def is_code_change_restart():
    """Check if the server restart was due to code changes."""
    return os.path.exists(CODE_CHANGE_FLAG)

def mark_code_change():
    """Mark that a code change has occurred."""
    try:
        with open(CODE_CHANGE_FLAG, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"Error marking code change: {e}")

def clear_code_change_flag():
    """Clear the code change flag."""
    try:
        if os.path.exists(CODE_CHANGE_FLAG):
            os.remove(CODE_CHANGE_FLAG)
    except Exception as e:
        print(f"Error clearing code change flag: {e}")

def load_status_from_disk():
    """Load repository status from disk if it exists and is valid."""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
                saved_status = json.load(f)
                
                # If this is a restart due to code changes, don't load old status
                if is_code_change_restart():
                    print("Code change detected - clearing saved status")
                    return {}
                
                # Filter out stale entries
                current_time = datetime.now()
                valid_status = {}
                for repo_url, status in saved_status.items():
                    try:
                        last_updated = datetime.fromisoformat(status["last_updated"])
                        # Only keep entries less than 5 minutes old
                        if (current_time - last_updated).total_seconds() < 300:
                            valid_status[repo_url] = status
                    except (KeyError, ValueError):
                        continue
                return valid_status
    except Exception as e:
        print(f"Error loading status from disk: {e}")
    return {}

def save_status_to_disk():
    """Save repository status to disk."""
    try:
        # Don't save if this is a code change restart
        if not is_code_change_restart():
            with open(STATUS_FILE, 'w') as f:
                json.dump(repository_status, f)
    except Exception as e:
        print(f"Error saving status to disk: {e}")

# Load saved status on startup
repository_status = load_status_from_disk()

# Register save_status_to_disk to run on exit
atexit.register(save_status_to_disk)

def update_repository_status(repo_url: str, stage: str, message: str, progress: dict = None):
    """Update the status of a repository with timestamp."""
    current_time = datetime.now().isoformat()
    repository_status[repo_url] = {
        "stage": stage,
        "message": message,
        "progress": progress,
        "last_updated": current_time
    }
    print(f"Status update [{current_time}] - {repo_url}: {stage} - {message}")
    
    # Only save to disk for completed states
    if stage in ["ready", "error"]:
        save_status_to_disk()

# Pydantic models for request/response
class RepoRequest(BaseModel):
    repo_url: str
    force_reload: bool = False
    
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

class StatusResponse(BaseModel):
    loaded: bool
    status: str
    details: dict
    
# Background task to load repository
def load_repository_task(repo_url: str):
    try:
        # Initialize GitSummarizer with status callback
        summarizer = GitSummarizer(status_callback=update_repository_status)
        
        # Set initial status
        update_repository_status(repo_url, "initializing", "Starting repository processing")
        
        # Start processing with timeout
        start_time = time.time()
        success = summarizer.load_repository(repo_url)
        processing_time = time.time() - start_time
        
        if success:
            # Store the summarizer for this repository
            active_repos[repo_url] = summarizer
            update_repository_status(
                repo_url, 
                "ready", 
                f"Repository loaded successfully in {processing_time:.1f} seconds",
                {"processing_time": processing_time}
            )
        else:
            error_msg = f"Failed to load repository after {processing_time:.1f} seconds"
            print(error_msg)
            update_repository_status(repo_url, "error", error_msg)
            
    except Exception as e:
        error_msg = f"Error loading repository {repo_url}: {str(e)}"
        print(error_msg)
        update_repository_status(repo_url, "error", error_msg)

@app.on_event("startup")
async def startup_event():
    """Handle startup tasks."""
    print("Loading saved repository status...")
    global repository_status
    repository_status = load_status_from_disk()
    
    if is_code_change_restart():
        print("Server restarted due to code changes - clearing status")
        repository_status = {}
        clear_code_change_flag()
    else:
        # Only mark interrupted status for non-code-change restarts
        for repo_url, status in repository_status.items():
            if status["stage"] not in ["ready", "error"]:
                update_repository_status(
                    repo_url,
                    "error",
                    "Processing interrupted by server restart - please try again"
                )

@app.on_event("shutdown")
async def shutdown_event():
    """Handle shutdown tasks."""
    print("Saving repository status...")
    save_status_to_disk()

# API Routes
@app.post("/api/repository", response_model=RepoResponse)
async def load_repository(background_tasks: BackgroundTasks, repo_request: RepoRequest):
    """
    Load a GitHub repository for analysis.
    This is an asynchronous operation that will run in the background.
    """
    repo_url = repo_request.repo_url
    force_reload = repo_request.force_reload if hasattr(repo_request, 'force_reload') else False
    
    # Check if already loaded or processing
    if repo_url in repository_status and not force_reload:
        status = repository_status[repo_url]
        # If the repository is already being processed and the last update was recent
        if status["stage"] not in ["ready", "error"]:
            last_updated = datetime.fromisoformat(status["last_updated"])
            if (datetime.now() - last_updated).total_seconds() < 300:  # 5 minutes timeout
                return {"success": True, "message": "Repository is already being processed"}
    
    # If we're here, either:
    # 1. The repository isn't being processed
    # 2. The previous processing timed out
    # 3. Force reload was requested
    # Clear existing status and start fresh
    if repo_url in active_repos:
        summarizer = active_repos[repo_url]
        summarizer.cleanup()
        del active_repos[repo_url]
    if repo_url in repository_status:
        del repository_status[repo_url]
    
    # Initialize status
    update_repository_status(repo_url, "queued", "Repository queued for processing")
    
    # Start loading in the background
    background_tasks.add_task(load_repository_task, repo_url)
    
    return {"success": True, "message": "Repository loading started"}

@app.get("/api/repository/status", response_model=StatusResponse)
async def get_repository_status(repo_url: str):
    """
    Check if a repository is loaded and ready for querying.
    Returns detailed status information about the loading process.
    """
    is_loaded = repo_url in active_repos
    status_info = repository_status.get(repo_url, {
        "stage": "not_found",
        "message": "Repository not found",
        "last_updated": datetime.now().isoformat()
    })
    
    # Check for stale status (no updates for 5 minutes)
    if status_info["stage"] not in ["ready", "error", "not_found"]:
        last_updated = datetime.fromisoformat(status_info["last_updated"])
        if (datetime.now() - last_updated).total_seconds() > 300:
            status_info = {
                "stage": "error",
                "message": "Processing timed out - please try again",
                "last_updated": datetime.now().isoformat()
            }
            repository_status[repo_url] = status_info
    
    return {
        "loaded": is_loaded,
        "status": status_info["stage"],
        "details": status_info
    }

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

@app.get("/api/repository/summary")
async def get_repository_summary(repo_url: str):
    """
    Get a summary of a loaded repository.
    """
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
    # Mark code change for development server auto-reload
    if '--reload' in sys.argv:
        mark_code_change()
    
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=1  # Add small delay to ensure flag file is processed
    ) 