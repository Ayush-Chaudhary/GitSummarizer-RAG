import os
import tiktoken
import json
from typing import List, Dict, Tuple, Any, Optional

# Import tree-sitter language modules
import tree_sitter_python as tspython
import tree_sitter_java as tsjava
import tree_sitter_cpp as tscpp
import tree_sitter_javascript as tsjs
import tree_sitter_go as tsgo
import tree_sitter_html as tshtml
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
    Class for parsing code and extracting breakpoints.
    """
    
    def __init__(self, file_extension: str):
        """
        Initialize the CodeParser.
        
        Args:
            file_extension: The file extension (language) of the code.
        """
        self.file_extension = file_extension
        self.parser = Parser()
        
        # Set language
        if file_extension == "py":
            language = Language(tspython.language())
            self.parser = Parser(language)
        elif file_extension == "java":
            language = Language(tsjava.language())  
            self.parser = Parser(language)
        elif file_extension == "cpp":
            language = Language(tscpp.language())
            self.parser = Parser(language)
        elif file_extension == "js":
            language = Language(tsjs.language())
            self.parser = Parser(language)
        elif file_extension == "go":
            language = Language(tsgo.language())
            self.parser = Parser(language)
        elif file_extension == "html":
            language = Language(tshtml.language())
            self.parser = Parser(language)
    
    def parse_code(self, code: str):
        """
        Parse the code using tree-sitter.
        
        Args:
            code: The code to parse.
            
        Returns:
            The parsed syntax tree.
        """
        return self.parser.parse(bytes(code, 'utf8'))
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extracts function/class definitions as breakpoints.
        
        Args:
            code: The code to extract breakpoints from.
            
        Returns:
            List of line numbers for breakpoints.
        """
        # Define syntax structures to extract based on language
        syntax_structures = {
            "py": ["import_statement", "function_definition", "class_definition"],
            "java": ["method_declaration", "class_declaration", "annotation"],
            "cpp": ["function_definition", "class_specifier"],
            "js": ["function_declaration", "class_declaration", "arrow_function"],
            "go": ["function_declaration", "method_declaration"],
            "html": ["element", "script_element"]
        }
        
        tree = self.parse_code(code)
        breakpoints = []
        
        def traverse(node):
            if node.type in syntax_structures.get(self.file_extension, []):
                # Adjust for special cases
                if self.file_extension == "py" and node.type == "import_statement":
                    # Only add imports as breakpoints if they're at the top level
                    if node.parent.type == "module":
                        breakpoints.append(node.start_point[0])
                else:
                    breakpoints.append(node.start_point[0])
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return sorted(breakpoints)
    
    def extract_comments(self, code: str) -> List[int]:
        """
        Extract line numbers with comments.
        
        Args:
            code: The code to extract comments from.
            
        Returns:
            List of line numbers with comments.
        """
        comment_types = {
            "py": ["comment"],
            "java": ["line_comment", "block_comment"],
            "cpp": ["comment"],
            "js": ["comment"],
            "go": ["comment"],
            "html": ["comment"]
        }
        
        tree = self.parse_code(code)
        comment_lines = []
        
        def traverse(node):
            if node.type in comment_types.get(self.file_extension, []):
                # Add the line number
                comment_lines.append(node.start_point[0])
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return sorted(comment_lines)

class CodeChunker:
    """
    Class for chunking code into semantically meaningful segments.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the CodeChunker.
        
        Args:
            file_extension: The file extension (language) of the code.
            encoding_name: The encoding name for token counting.
        """
        self.file_extension = file_extension
        self.encoding_name = encoding_name
        self.parser = CodeParser(file_extension)
    
    def chunk(self, code: str, token_limit: int = None) -> List[Dict[str, Any]]:
        """
        Chunk the code into semantically meaningful segments.
        
        Args:
            code: The code to chunk.
            token_limit: Maximum tokens per chunk. Defaults to config value if None.
            
        Returns:
            List of dictionaries containing chunk information.
        """
        token_limit = token_limit or config.DEFAULT_CHUNK_TOKEN_LIMIT
        
        # Get function/class breakpoints and comment lines
        breakpoints = self.parser.extract_breakpoints(code)
        comment_lines = self.parser.extract_comments(code)
        
        # Split the code into lines
        lines = code.split('\n')
        
        chunked_code = []
        start_line = 0
        i = 0
        
        # Add the first line as a breakpoint if not already present
        if 0 not in breakpoints:
            breakpoints.insert(0, 0)
        
        # Add the last line as a breakpoint if not already present
        if len(lines) - 1 not in breakpoints:
            breakpoints.append(len(lines) - 1)
        
        while i < len(lines):
            # Start a new chunk from the current position
            start_line = i
            current_chunk = []
            token_count = 0
            
            # Identify the class or function name for this chunk if possible
            class_name = None
            function_name = None
            
            # Check if this breakpoint is a class or function definition
            if self.file_extension == "py" and i < len(lines):
                line = lines[i].strip()
                if line.startswith("class "):
                    class_name = line.split("class ")[1].split("(")[0].split(":")[0].strip()
                elif line.startswith("def "):
                    function_name = line.split("def ")[1].split("(")[0].strip()
                    # Check if this is a method inside a class by looking at indentation pattern
                    for j in range(i-1, -1, -1):
                        prev_line = lines[j].strip()
                        if prev_line.startswith("class ") and len(lines[j]) - len(lines[j].lstrip()) < len(lines[i]) - len(lines[i].lstrip()):
                            class_name = prev_line.split("class ")[1].split("(")[0].split(":")[0].strip()
                            break
            elif self.file_extension == "java" and i < len(lines):
                # Java class and method detection
                line = lines[i].strip()
                # Check for class declaration
                if "class " in line and "{" in line:
                    parts = line.split("class ")[1].split("{")[0].strip()
                    class_name = parts.split(" ")[0].strip() # Handle inheritance, interfaces, etc.
                # Check for method declaration (simplistic)
                elif ("public " in line or "private " in line or "protected " in line) and "(" in line and ")" in line:
                    parts = line.split("(")[0].strip().split(" ")
                    # Last word before the parameters is the method name
                    function_name = parts[-1].strip()
                    # Find parent class
                    for j in range(i-1, -1, -1):
                        prev_line = lines[j].strip()
                        if "class " in prev_line:
                            parts = prev_line.split("class ")[1].split("{")[0].strip()
                            class_name = parts.split(" ")[0].strip()
                            break
            elif self.file_extension == "js" and i < len(lines):
                # JavaScript class and function detection
                line = lines[i].strip()
                # Check for class declaration
                if line.startswith("class "):
                    class_name = line.split("class ")[1].split("{")[0].split(" ")[0].strip()
                # Check for function declaration
                elif line.startswith("function "):
                    function_name = line.split("function ")[1].split("(")[0].strip()
                # Check for method in class
                elif "=" in line and "function" in line:
                    function_name = line.split("=")[0].strip()
                # Arrow functions
                elif "=>" in line:
                    parts = line.split("=")[0].strip()
                    if parts:
                        function_name = parts.split(" ")[-1].strip()
                # Find parent class for methods
                if function_name and not class_name:
                    for j in range(i-1, -1, -1):
                        prev_line = lines[j].strip()
                        if prev_line.startswith("class "):
                            class_name = prev_line.split("class ")[1].split("{")[0].split(" ")[0].strip()
                            break
            elif self.file_extension == "cpp" and i < len(lines):
                # C++ class and function detection
                line = lines[i].strip()
                # Check for class declaration
                if "class " in line and ("{" in line or ";" in line):
                    class_name = line.split("class ")[1].split("{")[0].split(":")[0].strip()
                # Check for function definition
                elif "(" in line and ")" in line and "{" in line:
                    parts = line.split("(")[0].strip().split(" ")
                    # Last word before parameters is the function name
                    function_name = parts[-1].strip()
                    # Check if this is a class method by looking for ClassName::
                    if "::" in function_name:
                        parts = function_name.split("::")
                        class_name = parts[0].strip()
                        function_name = parts[1].strip()
            
            # Special case for import statements in Python
            if self.file_extension == "py" and "import" in lines[i]:
                # Group import statements together
                while i < len(lines) and (i in breakpoints or "import" in lines[i] or i in comment_lines or lines[i].strip() == ""):
                    current_chunk.append(lines[i])
                    token_count += count_tokens(lines[i], self.encoding_name)
                    i += 1
                    
                    # But still respect token limit
                    if token_count > token_limit:
                        break
                        
                # If we've gone over the token limit or encountered a non-import line, end the chunk
                if i <= len(lines) - 1:
                    start_line = i  # Start new chunk from this import
            else:
                # For normal code sections, try to group by functions/classes
                while i < len(lines) and token_count <= token_limit:
                    # Add current line to chunk
                    current_chunk.append(lines[i])
                    token_count += count_tokens(lines[i], self.encoding_name)
                    i += 1
                    
                    # If we've reached a breakpoint and accumulated enough lines, it's a good place to end
                    if i < len(lines) and i in breakpoints and len(current_chunk) > 5 and token_count > token_limit * 0.5:
                        break
                        
                    # Stop if we're going over the token limit
                    if token_count > token_limit:
                        # If we've just started and already over token limit, process just this line
                        if len(current_chunk) <= 1:
                            i += 1  # Move to next line
                        else:
                            # Find the nearest breakpoint before the current position
                            stop_line = max([x for x in breakpoints if x < i], default=start_line)
                            # Adjust to match the breakpoint
                            diff = i - stop_line
                            if diff > 1:  # Only adjust if there's a significant difference
                                i = stop_line
                                # Remove the excess lines we added
                                current_chunk = current_chunk[:-diff]
                        break
                        
                    # Stop if we've reached the end of the file
                    if i >= len(lines):
                        break
            
            # Add the chunk to the list
            chunk_text = '\n'.join(current_chunk)
            chunk_info = {
                'chunk': chunk_text,
                'start_line': start_line + 1,  # Convert to 1-indexed
                'end_line': start_line + len(current_chunk),
                'token_count': token_count,
                'class_name': class_name,
                'function_name': function_name
            }
            chunked_code.append(chunk_info)
        
        return chunked_code
    
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