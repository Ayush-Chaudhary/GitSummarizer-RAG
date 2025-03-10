"""
Code chunker modules for different programming languages.
This package contains specialized chunkers for parsing and chunking different programming languages.
"""

from chunkers.base_chunker import BaseChunker
from chunkers.python_chunker import PythonChunker
from chunkers.cpp_chunker import CppChunker
from chunkers.java_chunker import JavaChunker
from chunkers.javascript_chunker import JavaScriptChunker
from chunkers.markdown_chunker import MarkdownChunker

# Map of file extensions to appropriate chunker classes
LANGUAGE_CHUNKERS = {
    # Python
    "py": PythonChunker,
    
    # C/C++
    "c": CppChunker,
    "cpp": CppChunker,
    "h": CppChunker,
    "hpp": CppChunker,
    
    # Java
    "java": JavaChunker,
    
    # JavaScript
    "js": JavaScriptChunker,
    "jsx": JavaScriptChunker,
    "ts": JavaScriptChunker,
    "tsx": JavaScriptChunker,
    
    # HTML (using JavaScript chunker for now)
    "html": JavaScriptChunker,
    "htm": JavaScriptChunker
}

def get_chunker_for_extension(file_extension, encoding_name="cl100k_base"):
    """
    Get the appropriate chunker for a given file extension.
    
    Args:
        file_extension: The file extension (e.g., "py", "java")
        encoding_name: The encoding name for token counting
        
    Returns:
        An instance of the appropriate chunker class
    """
    chunker_class = LANGUAGE_CHUNKERS.get(file_extension.lower(), BaseChunker)
    return chunker_class(file_extension, encoding_name) 