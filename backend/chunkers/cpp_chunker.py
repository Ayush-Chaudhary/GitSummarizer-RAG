import os
from typing import List, Dict, Tuple, Any, Optional, Set
import time

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from chunkers.base_chunker import BaseChunker, CodeParser

class CppCodeParser(CodeParser):
    """C/C++-specific code parser implementation"""
    
    def __init__(self, file_extension: str):
        """
        Initialize the CppCodeParser.
        
        Args:
            file_extension: The file extension (language) of the code.
        """
        super().__init__(file_extension)
        try:
            language = Language(tscpp.language())
            self.parser = self.parser or Parser(language)
        except Exception as e:
            print(f"Error initializing C/C++ parser: {e}")
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extracts function/class definitions as breakpoints for C++ code.
        
        Args:
            code: The code to extract breakpoints from.
            
        Returns:
            List of line numbers for breakpoints.
        """
        tree = self.parse_code(code)
        if not tree:
            return []
            
        breakpoints = []
        
        # Types of nodes that mark logical breakpoints in C++
        syntax_structures = [
            "function_definition", 
            "class_specifier", 
            "struct_specifier",
            "enum_specifier",
            "namespace_definition",
            "preproc_include",
            "preproc_define"
        ]
        
        def traverse(node):
            if node.type in syntax_structures:
                breakpoints.append(node.start_point[0])
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return sorted(breakpoints)
    
    def extract_comments(self, code: str) -> List[int]:
        """
        Extract line numbers with comments for C++ code.
        
        Args:
            code: The code to extract comments from.
            
        Returns:
            List of line numbers with comments.
        """
        tree = self.parse_code(code)
        if not tree:
            return []
            
        comment_lines = []
        
        def traverse(node):
            if node.type == "comment":
                comment_lines.append(node.start_point[0])
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return sorted(comment_lines)

class CppChunker(BaseChunker):
    """
    C/C++-specific implementation of code chunking.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the CppChunker.
        
        Args:
            file_extension: The file extension (should be 'c', 'cpp', 'h', or 'hpp').
            encoding_name: The encoding name for token counting.
        """
        super().__init__(file_extension, encoding_name)
        self.parser = CppCodeParser(file_extension)
    
    def _identify_code_sections(self, code: str, lines: List[str], file_name: str = None) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict], Optional[Dict]]:
        """
        Identify different sections of C++ code.
        
        Args:
            code: The full code string
            lines: The code split into lines
            file_name: Name of the file (not full path) to associate with chunks
            
        Returns:
            Tuple containing lists of identified sections:
            (classes, functions, imports, main_code, other_code)
            Note: With the simplified chunking strategy, only classes and functions are 
                  identified separately. Main code and other code are grouped together.
        """
        # Initialize containers for different code sections
        classes = []
        functions = []
        imports = []
        main_code = None
        other_code = None
        
        # Track which lines are accounted for
        accounted_lines = set()
        
        # Parse the code
        tree = self.parser.parse_code(code)
        
        if not tree:
            return [], [], [], None, None
        
        # Extract all classes
        classes = self._extract_classes(tree, lines)
        
        # Extract all standalone functions (not methods inside classes)
        functions = self._extract_standalone_functions(tree, lines, accounted_lines)
        
        # Return the sections - imports, main_code, and other_code will be handled
        # as part of the "everything else" chunk in the base chunker
        return classes, functions, imports, main_code, other_code
    
    def _extract_classes(self, tree, lines):
        """Extract all class definitions from the syntax tree."""
        classes = []
        root_node = tree.root_node
        
        def traverse_for_classes(node):
            if node.type == 'class_specifier' or node.type == 'struct_specifier':
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                # Extract the class name
                class_name = None
                # Look for the name through a type identifier
                for child in node.children:
                    if child.type == 'type_identifier':
                        class_name = lines[child.start_point[0]][child.start_point[1]:child.end_point[1]]
                        break
                
                if class_name:
                    classes.append({
                        'start': start_line,
                        'end': end_line,
                        'name': class_name
                    })
            
            # Recursively check children
            for child in node.children:
                traverse_for_classes(child)
        
        traverse_for_classes(root_node)
        return classes
    
    def _extract_standalone_functions(self, tree, lines, accounted_lines):
        """Extract all function definitions that are not methods (not inside classes)."""
        functions = []
        root_node = tree.root_node
        
        def traverse_for_functions(node, inside_class=False):
            # Skip if inside a class
            if node.type == 'class_specifier' or node.type == 'struct_specifier':
                for child in node.children:
                    traverse_for_functions(child, True)
                return
            
            # Function definition 
            if node.type == 'function_definition' and not inside_class:
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                # Skip if already accounted for
                if start_line in accounted_lines:
                    return
                
                # Extract the function name - in C++ this can be complex
                func_name = self._extract_function_name(node, lines)
                
                if func_name:
                    functions.append({
                        'start': start_line,
                        'end': end_line,
                        'name': func_name
                    })
            
            # Recursively check children
            for child in node.children:
                if not inside_class:
                    traverse_for_functions(child, False)
        
        traverse_for_functions(root_node)
        return functions
    
    def _extract_function_name(self, node, lines):
        """Extract function name from a function definition node."""
        func_name = "unknown"
        
        # Try to find function declarator
        for child in node.children:
            if child.type == 'function_declarator':
                # The function name is often in the first child of function_declarator
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        func_name = lines[subchild.start_point[0]][subchild.start_point[1]:subchild.end_point[1]]
                        return func_name
        
        # Fallback to text-based extraction if tree-sitter parsing didn't work
        line_text = lines[node.start_point[0]]
        line_parts = line_text.split('(')[0].strip().split()
        if len(line_parts) > 0:
            func_name = line_parts[-1]  # Usually the last token before ( is the function name
        
        return func_name 