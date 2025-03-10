import os
from typing import List, Dict, Tuple, Any, Optional, Set
import time

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser

from chunkers.base_chunker import BaseChunker, CodeParser

class JavaScriptCodeParser(CodeParser):
    """JavaScript-specific code parser implementation"""
    
    def __init__(self, file_extension: str):
        """
        Initialize the JavaScriptCodeParser.
        
        Args:
            file_extension: The file extension (language) of the code.
        """
        super().__init__(file_extension)
        try:
            language = Language(tsjs.language())
            self.parser = self.parser or Parser(language)
        except Exception as e:
            print(f"Error initializing JavaScript parser: {e}")
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extracts class/function definitions as breakpoints for JavaScript code.
        
        Args:
            code: The code to extract breakpoints from.
            
        Returns:
            List of line numbers for breakpoints.
        """
        tree = self.parse_code(code)
        if not tree:
            return []
            
        breakpoints = []
        
        # Types of nodes that mark logical breakpoints in JavaScript
        syntax_structures = [
            "class_declaration", 
            "function_declaration",
            "arrow_function",
            "method_definition",
            "import_statement",
            "export_statement"
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
        Extract line numbers with comments for JavaScript code.
        
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

class JavaScriptChunker(BaseChunker):
    """
    JavaScript-specific implementation of code chunking.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the JavaScriptChunker.
        
        Args:
            file_extension: The file extension (should be 'js', 'jsx', 'ts', or 'tsx').
            encoding_name: The encoding name for token counting.
        """
        super().__init__(file_extension, encoding_name)
        self.parser = JavaScriptCodeParser(file_extension)
    
    def _identify_code_sections(self, code: str, lines: List[str], file_name: str = None) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict], Optional[Dict]]:
        """
        Identify different sections of JavaScript code.
        
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
            if node.type == 'class_declaration' or node.type == 'class':
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                # Extract the class name
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
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
            if node.type == 'class_declaration' or node.type == 'class':
                for child in node.children:
                    traverse_for_functions(child, True)
                return
            
            # Function declaration
            if (node.type == 'function_declaration' or node.type == 'function') and not inside_class:
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                # Skip if already accounted for
                if start_line in accounted_lines:
                    return
                
                # Extract the function name
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = lines[child.start_point[0]][child.start_point[1]:child.end_point[1]]
                        break
                
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
    
    def _extract_imports(self, tree, lines):
        """Extract all import statements from the syntax tree."""
        imports = []
        root_node = tree.root_node
        
        def traverse_for_imports(node):
            # Match import statements (ES6+)
            if node.type == 'import_statement' or node.type == 'import':
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                imports.append({
                    'start': start_line,
                    'end': end_line,
                    'name': 'imports'
                })
            
            # Match require statements (CommonJS)
            elif node.type == 'expression_statement':
                code_text = lines[node.start_point[0]][node.start_point[1]:node.end_point[1]]
                if 'require(' in code_text:
                    start_line = node.start_point[0]
                    end_line = node.end_point[0]
                    
                    imports.append({
                        'start': start_line,
                        'end': end_line,
                        'name': 'imports'
                    })
            
            # Recursively check children
            for child in node.children:
                traverse_for_imports(child)
        
        traverse_for_imports(root_node)
        return imports
    
    def _find_main_section(self, tree, lines, accounted_lines):
        """Find the main section of the code (e.g., module exports, IIFE)."""
        root_node = tree.root_node
        main_section = None
        
        # Look for module.exports or exports. patterns
        for i, line in enumerate(lines):
            if i not in accounted_lines and (
                'module.exports' in line or 
                'exports.' in line or 
                'if (typeof module !== \'undefined\')' in line or
                'if (typeof window !== \'undefined\')' in line
            ):
                # Find the end of this section
                start_line = i
                end_line = i
                
                # Look for closing bracket or end of file
                for j in range(i, len(lines)):
                    if j in accounted_lines:
                        continue
                    
                    if '}' in lines[j] and j > start_line:
                        end_line = j
                        break
                    
                    end_line = j
                
                main_section = {
                    'start': start_line,
                    'end': end_line
                }
                break
        
        return main_section 