import os
from typing import List, Dict, Tuple, Any, Optional, Set
import time

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from chunkers.base_chunker import BaseChunker, CodeParser

class PythonCodeParser(CodeParser):
    """Python-specific code parser implementation"""
    
    def __init__(self, file_extension: str):
        """
        Initialize the PythonCodeParser.
        
        Args:
            file_extension: The file extension (language) of the code.
        """
        super().__init__(file_extension)
        try:
            language = Language(tspython.language())
            self.parser = self.parser or Parser(language)
        except Exception as e:
            print(f"Error initializing Python parser: {e}")
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extracts function/class definitions as breakpoints for Python code.
        
        Args:
            code: The code to extract breakpoints from.
            
        Returns:
            List of line numbers for breakpoints.
        """
        tree = self.parse_code(code)
        if not tree:
            return []
            
        breakpoints = []
        
        # Types of nodes that mark logical breakpoints in Python
        syntax_structures = ["import_statement", "function_definition", "class_definition"]
        
        def traverse(node):
            if node.type in syntax_structures:
                # Only add imports as breakpoints if they're at the top level
                if node.type == "import_statement":
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
        Extract line numbers with comments for Python code.
        
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

class PythonChunker(BaseChunker):
    """
    Python-specific implementation of code chunking.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the PythonChunker.
        
        Args:
            file_extension: The file extension (should be 'py').
            encoding_name: The encoding name for token counting.
        """
        super().__init__(file_extension, encoding_name)
        self.parser = PythonCodeParser(file_extension)
    
    def _identify_code_sections(self, code: str, lines: List[str], file_name: str = None) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict], Optional[Dict]]:
        """
        Identify different sections of Python code.
        
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
        
        # Find all class definitions
        class_nodes = root_node.children
        for node in class_nodes:
            if node.type == 'class_definition':
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
        
        return classes
    
    def _extract_standalone_functions(self, tree, lines, accounted_lines):
        """Extract all function definitions that are not methods (not inside classes)."""
        functions = []
        root_node = tree.root_node
        
        # Find all function definitions at the root level
        for node in root_node.children:
            if node.type == 'function_definition':
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                # Skip if this function is already accounted for (likely a method in a class)
                if start_line in accounted_lines:
                    continue
                
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
        
        return functions
    
    def _extract_imports(self, tree, lines):
        """Extract all import statements from the syntax tree."""
        imports = []
        root_node = tree.root_node
        
        # Find all import statements
        for node in root_node.children:
            if node.type in ('import_statement', 'import_from_statement'):
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                imports.append({
                    'start': start_line,
                    'end': end_line,
                    'name': 'imports'
                })
        
        return imports
    
    def _extract_from_syntax_tree(self, tree, lines: List[str], 
                                 classes: List[Dict], functions: List[Dict], 
                                 imports: List[Dict], accounted_lines: Set[int]):
        """
        Extract code sections from the syntax tree.
        
        Args:
            tree: The parsed syntax tree
            lines: The code split into lines
            classes: List to add class info to
            functions: List to add function info to
            imports: List to add import info to
            accounted_lines: Set of line numbers to mark as accounted for
        """
        def traverse(node, parent=None):
            if node.type == "class_definition":
                # Extract class info
                class_name = self._extract_class_name(node, lines)
                
                # Get class boundaries
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                classes.append({
                    'name': class_name,
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark these lines as accounted for
                for i in range(start_line, end_line + 1):
                    accounted_lines.add(i)
            
            elif node.type == "function_definition":
                # Skip if this is a method inside a class (already covered)
                is_method = False
                parent_node = node.parent
                while parent_node:
                    if parent_node.type == "class_definition":
                        is_method = True
                        break
                    parent_node = parent_node.parent
                
                if not is_method:
                    # Extract function info
                    func_name = self._extract_function_name(node, lines)
                    
                    # Get function boundaries
                    start_line = node.start_point[0]
                    end_line = node.end_point[0]
                    
                    functions.append({
                        'name': func_name,
                        'start': start_line,
                        'end': end_line
                    })
                    
                    # Mark these lines as accounted for
                    for i in range(start_line, end_line + 1):
                        accounted_lines.add(i)
            
            elif node.type == "import_statement" or node.type == "import_from_statement":
                # Extract import info
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                imports.append({
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark these lines as accounted for
                for i in range(start_line, end_line + 1):
                    accounted_lines.add(i)
            
            # Recursively process children
            for child in node.children:
                traverse(child, node)
        
        # Start traversal from root
        traverse(tree.root_node)
    
    def _extract_class_name(self, node, lines: List[str]) -> str:
        """Extract class name from a node"""
        try:
            for child in node.children:
                if child.type == "identifier":
                    return lines[node.start_point[0]][child.start_point[1]:child.end_point[1]]
            
            # Fallback
            line = lines[node.start_point[0]]
            if "class " in line:
                return line.split("class ")[1].split("(")[0].split(":")[0].strip()
        except Exception:
            pass
        
        return "unknown"
    
    def _extract_function_name(self, node, lines: List[str]) -> str:
        """Extract function name from a node"""
        try:
            for child in node.children:
                if child.type == "identifier":
                    return lines[node.start_point[0]][child.start_point[1]:child.end_point[1]]
            
            # Fallback
            line = lines[node.start_point[0]]
            if "def " in line:
                return line.split("def ")[1].split("(")[0].strip()
        except Exception:
            pass
        
        return "unknown"
    
    def _identify_python_sections(self, lines: List[str], accounted_lines: Set[int], 
                                 classes: List[Dict], functions: List[Dict], imports: List[Dict]):
        """
        Identify Python-specific sections that might not be caught by the parser.
        
        Args:
            lines: The code split into lines
            accounted_lines: Set of line numbers already accounted for
            classes: List to add class info to
            functions: List to add function info to
            imports: List to add import info to
        """
        # Find imports
        import_section = []
        in_import_section = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip already accounted lines
            if i in accounted_lines:
                continue
                
            # Track import statements
            if line.startswith("import ") or line.startswith("from "):
                if not in_import_section:
                    in_import_section = True
                    import_section = [i]
                    accounted_lines.add(i)
                else:
                    import_section.append(i)
                    accounted_lines.add(i)
            elif in_import_section and (line == "" or line.startswith("#")):
                # Allow blank lines and comments within import section
                import_section.append(i)
                accounted_lines.add(i)
            elif in_import_section:
                # End of import section
                in_import_section = False
                if len(import_section) > 0:
                    imports.append({
                        'start': min(import_section),
                        'end': max(import_section)
                    })
        
        # Handle any trailing import section
        if in_import_section and len(import_section) > 0:
            imports.append({
                'start': min(import_section),
                'end': max(import_section)
            })
            
        # Look for class and function definitions using indentation patterns
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Class detection
            if i not in accounted_lines and line.startswith("class "):
                start_line = i
                class_name = line.split("class ")[1].split("(")[0].split(":")[0].strip()
                
                # Find end using indentation
                indentation = len(lines[i]) - len(lines[i].lstrip())
                end_line = i
                
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        curr_indent = len(lines[j]) - len(lines[j].lstrip())
                        if curr_indent <= indentation:
                            break
                    end_line = j
                    j += 1
                
                # Add class info
                classes.append({
                    'name': class_name,
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark lines as accounted for
                for k in range(start_line, end_line + 1):
                    accounted_lines.add(k)
                
                i = end_line + 1
            
            # Function detection
            elif i not in accounted_lines and line.startswith("def "):
                start_line = i
                func_name = line.split("def ")[1].split("(")[0].strip()
                
                # Find end using indentation
                indentation = len(lines[i]) - len(lines[i].lstrip())
                end_line = i
                
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        curr_indent = len(lines[j]) - len(lines[j].lstrip())
                        if curr_indent <= indentation:
                            break
                    end_line = j
                    j += 1
                
                # Add function info
                functions.append({
                    'name': func_name,
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark lines as accounted for
                for k in range(start_line, end_line + 1):
                    accounted_lines.add(k)
                
                i = end_line + 1
            else:
                i += 1
    
    def _identify_main_code(self, lines: List[str], accounted_lines: Set[int]) -> Optional[Dict]:
        """Identify Python main block"""
        for i, line in enumerate(lines):
            if i not in accounted_lines and line.strip().startswith("if __name__ == "):
                start_line = i
                
                # Find end using indentation
                indentation = len(lines[i]) - len(lines[i].lstrip())
                end_line = len(lines) - 1
                
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        curr_indent = len(lines[j]) - len(lines[j].lstrip())
                        if curr_indent <= indentation:
                            end_line = j - 1
                            break
                
                # Mark lines as accounted for
                for k in range(start_line, end_line + 1):
                    accounted_lines.add(k)
                    
                return {
                    'start': start_line,
                    'end': end_line
                }
        
        return None 