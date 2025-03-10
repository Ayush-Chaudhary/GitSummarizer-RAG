import os
from typing import List, Dict, Tuple, Any, Optional, Set
import time
import re

from chunkers.base_chunker import BaseChunker, CodeParser

class MarkdownParser(CodeParser):
    """Markdown-specific parser implementation"""
    
    def __init__(self, file_extension: str):
        """
        Initialize the MarkdownParser.
        
        Args:
            file_extension: The file extension (should be 'md').
        """
        super().__init__(file_extension)
        # No tree-sitter parser for Markdown, we'll use regex patterns
        self.parser = None
        
        # Regex patterns for Markdown features
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        self.code_block_start = re.compile(r'^```\w*$')
        self.code_block_end = re.compile(r'^```$')
        self.list_item = re.compile(r'^\s*[-*+]\s+(.+)$')
        self.numbered_list = re.compile(r'^\s*\d+\.\s+(.+)$')
    
    def parse_code(self, code: str):
        """
        No formal parsing for Markdown, just return the code.
        
        Args:
            code: The markdown content.
            
        Returns:
            The original code (no parsing).
        """
        return code
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extract line numbers where new sections start in Markdown.
        
        Args:
            code: The markdown content.
            
        Returns:
            List of line numbers for breakpoints.
        """
        lines = code.split('\n')
        breakpoints = []
        
        # Headers are natural breakpoints in markdown
        for i, line in enumerate(lines):
            if self.header_pattern.match(line):
                breakpoints.append(i)
                
        return sorted(breakpoints)
    
    def extract_comments(self, code: str) -> List[int]:
        """
        Markdown doesn't have formal comments, return empty list.
        
        Args:
            code: The markdown content.
            
        Returns:
            Empty list.
        """
        return []

class MarkdownChunker(BaseChunker):
    """
    Markdown-specific implementation of content chunking.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the MarkdownChunker.
        
        Args:
            file_extension: The file extension (should be 'md').
            encoding_name: The encoding name for token counting.
        """
        super().__init__(file_extension, encoding_name)
        self.parser = MarkdownParser(file_extension)
    
    def _identify_code_sections(self, code: str, lines: List[str], file_name: str = None) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict], Optional[Dict]]:
        """
        Identify different sections of Markdown content.
        For Markdown, we primarily care about headers and code blocks.
        
        Args:
            code: The full text content
            lines: The text split into lines
            file_name: Name of the file (not full path) to associate with chunks
            
        Returns:
            Tuple containing lists of identified sections:
            (classes, functions, imports, main_code, other_code)
            Note: For Markdown, "classes" represent headers, "functions" represent code blocks,
                  and other content will be grouped in the "everything else" chunk.
        """
        # Classes will represent headers
        classes = []
        # Functions will represent code blocks
        functions = []
        # Imports, main_code, and other_code are not used in Markdown
        imports = []
        main_code = None
        other_code = None
        
        # Track line numbering
        current_line = 0
        
        # Process headers and code blocks
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        in_code_block = False
        code_block_start = 0
        code_block_language = ""
        
        for i, line in enumerate(lines):
            # Check for headers
            header_match = header_pattern.match(line)
            if header_match and not in_code_block:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Find the end of this section (next header of same or higher level)
                end_line = i
                for j in range(i + 1, len(lines)):
                    next_header = header_pattern.match(lines[j])
                    if next_header and len(next_header.group(1)) <= level:
                        end_line = j - 1
                        break
                    end_line = j
                
                # Add header section
                if end_line > i:  # Only add if section has content
                    classes.append({
                        'start': i,
                        'end': end_line,
                        'name': title
                    })
            
            # Check for code blocks
            if line.strip().startswith("```") and not in_code_block:
                in_code_block = True
                code_block_start = i
                # Extract language if specified
                code_block_language = line.strip()[3:].strip()
            elif line.strip().startswith("```") and in_code_block:
                in_code_block = False
                # Add code block if it has content
                if i > code_block_start + 1:
                    functions.append({
                        'start': code_block_start,
                        'end': i,
                        'name': f"code_block_{code_block_language}" if code_block_language else "code_block"
                    })
        
        return classes, functions, imports, main_code, other_code 