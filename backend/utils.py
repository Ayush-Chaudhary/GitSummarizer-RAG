import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

import config

def get_file_extension(file_path: str) -> Optional[str]:
    """
    Get the language identifier from a file extension.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        Language identifier or None if unsupported.
    """
    ext = os.path.splitext(file_path)[1].lower()
    return config.SUPPORTED_LANGUAGES.get(ext)

def is_supported_file(file_path: str) -> bool:
    """
    Check if a file is supported for processing.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        True if the file is supported, False otherwise.
    """
    return get_file_extension(file_path) is not None

def is_binary_file(file_path: str) -> bool:
    """
    Check if a file is binary.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        True if the file is binary, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # Read a small chunk
        return False
    except UnicodeDecodeError:
        return True

def save_json(data: Any, file_path: str):
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save.
        file_path: Path to the file.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load_json(file_path: str) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        Loaded data.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_repo_info_from_url(repo_url: str) -> Dict[str, str]:
    """
    Extract repository information from a URL.
    
    Args:
        repo_url: URL of the repository.
        
    Returns:
        Dictionary with repository information.
    """
    # Remove trailing .git if present
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
        
    # Handle GitHub URLs
    if 'github.com' in repo_url:
        parts = repo_url.split('github.com/')
        if len(parts) > 1:
            owner_repo = parts[1].split('/')
            if len(owner_repo) >= 2:
                return {
                    'platform': 'github',
                    'owner': owner_repo[0],
                    'repo': owner_repo[1],
                    'url': repo_url
                }
    
    # Default to basic info if URL format is not recognized
    return {
        'platform': 'unknown',
        'url': repo_url,
        'name': repo_url.split('/')[-1]
    }

def format_code_for_display(code: str, language: Optional[str] = None) -> str:
    """
    Format code for display with appropriate markdown.
    
    Args:
        code: The code to format.
        language: Optional language identifier for syntax highlighting.
        
    Returns:
        Formatted code for display.
    """
    lang_str = language or ""
    return f"```{lang_str}\n{code}\n```" 