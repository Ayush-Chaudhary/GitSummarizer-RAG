import os
import time
from typing import List, Dict, Tuple, Any, Optional
import sys
import traceback

# Add the parent directory to sys.path to allow imports from sibling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tiktoken
from tree_sitter import Parser, Language

import config

def count_tokens(string: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count the number of tokens in a string.
    
    Args:
        string: The string to count tokens in.
        encoding_name: The name of the encoding to use.
        
    Returns:
        The number of tokens in the string.
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))

class CodeParser:
    """
    Base class for parsing code and extracting breakpoints.
    Language-specific parsers should extend this class.
    """
    
    def __init__(self, file_extension: str):
        """
        Initialize the CodeParser.
        
        Args:
            file_extension: The file extension (language) of the code.
        """
        self.file_extension = file_extension
        self.parser = None
    
    def parse_code(self, code: str):
        """
        Parse the code using tree-sitter.
        
        Args:
            code: The code to parse.
            
        Returns:
            The parsed syntax tree or None if parsing fails.
        """
        if not self.parser:
            return None
            
        try:
            return self.parser.parse(bytes(code, 'utf8'))
        except Exception as e:
            print(f"Error parsing code: {e}")
            return None
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extracts function/class definitions as breakpoints.
        Base implementation returns an empty list.
        
        Args:
            code: The code to extract breakpoints from.
            
        Returns:
            List of line numbers for breakpoints.
        """
        return []
    
    def extract_comments(self, code: str) -> List[int]:
        """
        Extract line numbers with comments.
        Base implementation returns an empty list.
        
        Args:
            code: The code to extract comments from.
            
        Returns:
            List of line numbers with comments.
        """
        return []

class BaseChunker:
    """
    Base class for chunking code into semantically meaningful segments.
    Language-specific chunkers should extend this class.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the BaseChunker.
        
        Args:
            file_extension: The file extension (language) of the code.
            encoding_name: The encoding name for token counting.
        """
        self.file_extension = file_extension
        self.encoding_name = encoding_name
        self.parser = CodeParser(file_extension)
    
    def chunk(self, code: str, token_limit: int = None, file_name: str = None) -> List[Dict[str, Any]]:
        """
        Chunk the given code into semantically meaningful chunks.
        
        Creates three types of chunks:
        1. Class chunks - one chunk per class
        2. Function chunks - one chunk per function
        3. Everything else in one big chunk
        
        Args:
            code: The code to chunk
            token_limit: Maximum tokens per chunk. Defaults to config value if None.
            file_name: Name of the file (not full path) to associate with chunks
            
        Returns:
            List of dictionaries containing chunk information
        """
        start_time = time.time()
        
        # Use default token limit if none provided
        if token_limit is None:
            token_limit = config.DEFAULT_CHUNK_TOKEN_LIMIT
            
        # Check the code is not empty
        if not code or not code.strip():
            return []
            
        # Split code into lines for processing
        lines = code.split('\n')
        
        # Initialize empty chunk containers
        chunks = []
        
        # Track which lines are accounted for
        accounted_lines = set()
        
        # 1. First pass: Identify all sections by type
        try:
            classes, functions, imports, main_code, other_code = self._identify_code_sections(code, lines, file_name)
            
            # 2. Create chunks for each section type - in the specific order
            
            # 1) Classes - one chunk per class
            for class_info in classes:
                class_lines = lines[class_info['start']:class_info['end']+1]
                
                # Skip if only one line (just a declaration)
                if len(class_lines) <= 1:
                    continue
                    
                class_chunk = self._create_chunk(
                    class_lines,
                    class_info['start'],
                    class_info['name'],
                    None,
                    file_name
                )
                
                if class_chunk:
                    chunks.append(class_chunk)
                    # Mark these lines as accounted for
                    for i in range(class_info['start'], class_info['end'] + 1):
                        accounted_lines.add(i)
            
            # 2) Functions - one chunk per function
            for func_info in functions:
                func_lines = lines[func_info['start']:func_info['end']+1]
                
                # Skip if only one line (just a declaration)
                if len(func_lines) <= 1:
                    continue
                    
                func_chunk = self._create_chunk(
                    func_lines,
                    func_info['start'],
                    None,
                    func_info['name'],
                    file_name
                )
                
                if func_chunk:
                    chunks.append(func_chunk)
                    # Mark these lines as accounted for
                    for i in range(func_info['start'], func_info['end'] + 1):
                        accounted_lines.add(i)
            
            # 3) Everything else in one big chunk
            remaining_lines = []
            for i in range(len(lines)):
                if i not in accounted_lines and lines[i].strip():
                    remaining_lines.append(i)
            
            if remaining_lines:
                # Get the continuous ranges of remaining lines
                ranges = []
                current_range = [remaining_lines[0]]
                
                for line in remaining_lines[1:]:
                    if line == current_range[-1] + 1:
                        current_range.append(line)
                    else:
                        ranges.append(current_range)
                        current_range = [line]
                
                if current_range:
                    ranges.append(current_range)
                
                # Collect all ranges into one chunk
                all_remaining_lines = []
                for line_range in ranges:
                    all_remaining_lines.extend(line_range)
                
                if all_remaining_lines:
                    # Sort the lines to maintain the original code order
                    all_remaining_lines.sort()
                    
                    # Collect all the actual lines of code
                    remaining_code_lines = []
                    for line_num in all_remaining_lines:
                        remaining_code_lines.append(lines[line_num])
                    
                    # Create the "everything else" chunk if there's at least 2 lines
                    if len(remaining_code_lines) > 1:
                        other_chunk = self._create_chunk(
                            remaining_code_lines,
                            all_remaining_lines[0],  # Start at the first remaining line
                            None,
                            "other",
                            file_name
                        )
                        
                        if other_chunk:
                            chunks.append(other_chunk)
            
        except Exception as e:
            print(f"Error during chunking: {e}")
            traceback.print_exc()
            # Fallback: Create a single chunk for the entire file if it has more than one line
            if len(lines) > 1:
                chunks = [self._create_chunk(lines, 0, None, "entire_file", file_name)]
        
        # Log total chunking time
        total_time = time.time() - start_time
        # print(f"Chunking completed in {total_time:.2f}s - Created {len(chunks)} chunks")
        
        return chunks
    
    def _remove_duplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate chunks (e.g., just class/function declaration line)
        """
        unique_chunks = []
        # Track which chunks we've seen by their start_line
        seen_starts = set()
        
        # Sort chunks by token count (descending) so we keep the most comprehensive chunk for each entity
        sorted_chunks = sorted(chunks, key=lambda x: x['token_count'], reverse=True)
        
        for chunk in sorted_chunks:
            # For each start_line, only keep the first occurrence (the one with the highest token count)
            if chunk['start_line'] not in seen_starts:
                unique_chunks.append(chunk)
                seen_starts.add(chunk['start_line'])
        
        return unique_chunks
    
    def _identify_code_sections(self, code: str, lines: List[str], file_name: str = None) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict], Optional[Dict]]:
        """
        Identify different sections of code: classes, functions, imports, main code, and other code.
        Base implementation returns empty lists. Should be overridden by subclasses.
        
        The sections will be processed in this order:
        1. Classes - one chunk per class
        2. Functions - one chunk per function 
        3. Everything else - one chunk for all remaining code
        
        Args:
            code: The full code string
            lines: The code split into lines
            file_name: Name of the file (not full path) to associate with chunks
            
        Returns:
            Tuple containing lists of identified sections:
            (classes, functions, imports, main_code, other_code)
            Note: With the simplified chunking strategy, imports, main_code, and other_code
                  will be grouped into the "everything else" chunk.
        """
        # The base implementation doesn't identify any sections
        # This should be overridden by language-specific chunkers
        return [], [], [], None, None
    
    def _collect_unaccounted_lines(self, lines: List[str], accounted_lines: set) -> Optional[Dict]:
        """
        Collect any remaining unaccounted lines as 'other code'
        
        Args:
            lines: List of code lines
            accounted_lines: Set of line numbers already accounted for
            
        Returns:
            Dictionary with start and end line numbers, or None if no unaccounted lines
        """
        unaccounted = []
        
        for i in range(len(lines)):
            if i not in accounted_lines and lines[i].strip():
                unaccounted.append(i)
                
        if not unaccounted:
            return None
            
        # Group consecutive unaccounted lines
        grouped = []
        if unaccounted:
            current_group = [unaccounted[0]]
            
            for line in unaccounted[1:]:
                if line == current_group[-1] + 1:
                    current_group.append(line)
                else:
                    grouped.append(current_group)
                    current_group = [line]
                    
            if current_group:
                grouped.append(current_group)
            
        # Combine all groups into one section
        if grouped:
            return {
                'start': min(min(group) for group in grouped),
                'end': max(max(group) for group in grouped)
            }
            
        return None
    
    def _merge_adjacent_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        Merge adjacent or overlapping sections of the same type
        
        Args:
            sections: List of section dictionaries with 'start' and 'end' keys
            
        Returns:
            List of merged sections
        """
        if not sections:
            return []
            
        # Sort sections by start line
        sorted_sections = sorted(sections, key=lambda s: s['start'])
        
        # Merge adjacent/overlapping sections
        merged = [sorted_sections[0]]
        
        for current in sorted_sections[1:]:
            previous = merged[-1]
            
            # If current section starts right after previous or overlaps
            if current['start'] <= previous['end'] + 1:
                # Extend the previous section
                previous['end'] = max(previous['end'], current['end'])
            else:
                # Add as a new section
                merged.append(current)
                
        return merged
    
    def _create_chunk(self, lines: List[str], start_line: int, class_name: Optional[str], function_name: Optional[str], file_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a chunk from the given lines.
        
        Args:
            lines: The lines of code for the chunk
            start_line: The starting line number
            class_name: Optional class name for the chunk
            function_name: Optional function name for the chunk
            file_name: Optional file name (not the full path) for the chunk
            
        Returns:
            Dictionary containing chunk information
        """
        if not lines:
            return None
            
        chunk_text = '\n'.join(lines)
        
        # Skip empty chunks
        if not chunk_text.strip():
            return None
            
        # Count tokens
        token_count = count_tokens(chunk_text, self.encoding_name)
        
        return {
            'chunk': chunk_text,
            'start_line': start_line + 1,  # Convert to 1-indexed
            'end_line': start_line + len(lines),
            'token_count': token_count,
            'class_name': class_name,
            'function_name': function_name,
            'file_name': file_name
        }
    
    def get_chunk(self, chunked_codebase: List[Dict[str, Any]], chunk_number: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk from the chunked codebase.
        
        Args:
            chunked_codebase: The chunked codebase.
            chunk_number: The chunk number to retrieve.
            
        Returns:
            The specified chunk or None if not found.
        """
        if 0 <= chunk_number < len(chunked_codebase):
            return chunked_codebase[chunk_number]
        return None 