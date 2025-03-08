import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from git import Repo
from github import Github
import config

class GitHubRetriever:
    """
    Class for retrieving code from GitHub repositories
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the GitHubRetriever.
        
        Args:
            temp_dir: Optional path to temporary directory for cloning repos
        """
        self.temp_dir = temp_dir or config.GITHUB_TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def clone_repository(self, repo_url: str) -> str:
        """
        Clone a GitHub repository.
        
        Args:
            repo_url: URL of the GitHub repository.
            
        Returns:
            Path to the cloned repository.
        """
        # Extract repository name from URL
        repo_name = repo_url.split('/')[-1]
        repo_path = os.path.join(self.temp_dir, repo_name)
        
        # Check if the repository already exists locally
        if os.path.exists(repo_path):
            try:
                # Try to use shutil.rmtree first
                shutil.rmtree(repo_path)
            except PermissionError:
                # If that fails, use system commands
                try:
                    if os.name == 'nt':  # Windows
                        os.system(f'rmdir /S /Q "{repo_path}"')
                    else:  # Unix-like
                        os.system(f'rm -rf "{repo_path}"')
                except Exception as e:
                    raise Exception(f"Error removing existing repository: {e}")
        
        # Clone the repository
        print(f"Cloning repository: {repo_url}")
        try:
            Repo.clone_from(repo_url, repo_path)
            print(f"Repository cloned to: {repo_path}")
        except Exception as e:
            raise Exception(f"Error cloning repository: {e}")
        
        return repo_path
    
    def get_file_paths(self, repo_path: str, exclude_dirs: Optional[List[str]] = None) -> List[str]:
        """
        Get all file paths in the repository.
        
        Args:
            repo_path: Path to the cloned repository.
            exclude_dirs: Directories to exclude, e.g. ['.git', 'node_modules']
            
        Returns:
            List of file paths.
        """
        if exclude_dirs is None:
            exclude_dirs = ['.git', 'node_modules', 'venv', '.venv', '__pycache__', '.pytest_cache', '.github']
            
        file_paths = []
        for root, dirs, files in os.walk(repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
                
        return file_paths
    
    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        Read the content of a file.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            Content of the file or None if file can't be read as text.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            print(f"Could not read file as text: {file_path}")
            return None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def get_repo_structure(self, repo_path: str) -> Dict:
        """
        Get the structure of the repository.
        
        Args:
            repo_path: Path to the cloned repository.
            
        Returns:
            Dictionary representing the repository structure.
        """
        structure = {}
        root_path = Path(repo_path)
        
        for path in root_path.rglob('*'):
            if '.git' in path.parts:
                continue
                
            if path.is_file():
                # Create relative path from repo root
                rel_path = path.relative_to(root_path)
                
                # Build the nested structure
                current = structure
                for part in rel_path.parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Add the file
                current[rel_path.parts[-1]] = str(path)
        
        return structure
    
    def cleanup(self):
        """
        Clean up temporary directories.
        """
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temporary directory: {self.temp_dir}")
            except PermissionError:
                # On Windows, use system commands to force delete
                try:
                    if os.name == 'nt':  # Windows
                        os.system(f'rmdir /S /Q "{self.temp_dir}"')
                    else:  # Unix-like
                        os.system(f'rm -rf "{self.temp_dir}"')
                    print(f"Cleaned up temporary directory using system command: {self.temp_dir}")
                except Exception as e:
                    print(f"Warning: Could not clean up temporary directory: {e}")
                    print(f"You may need to manually delete: {self.temp_dir}") 