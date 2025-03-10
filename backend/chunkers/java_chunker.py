import os
from typing import List, Dict, Tuple, Any, Optional, Set
import time

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from chunkers.base_chunker import BaseChunker, CodeParser

class JavaCodeParser(CodeParser):
    """Java-specific code parser implementation"""
    
    def __init__(self, file_extension: str):
        """
        Initialize the JavaCodeParser.
        
        Args:
            file_extension: The file extension (language) of the code.
        """
        super().__init__(file_extension)
        try:
            language = Language(tsjava.language())
            self.parser = self.parser or Parser(language)
        except Exception as e:
            print(f"Error initializing Java parser: {e}")
    
    def extract_breakpoints(self, code: str) -> List[int]:
        """
        Extracts function/class definitions as breakpoints for Java code.
        
        Args:
            code: The code to extract breakpoints from.
            
        Returns:
            List of line numbers for breakpoints.
        """
        tree = self.parse_code(code)
        if not tree:
            return []
            
        breakpoints = []
        
        # Types of nodes that mark logical breakpoints in Java
        syntax_structures = [
            "class_declaration", 
            "method_declaration",
            "interface_declaration",
            "enum_declaration",
            "import_declaration",
            "package_declaration"
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
        Extract line numbers with comments for Java code.
        
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
            if node.type in ["line_comment", "block_comment"]:
                comment_lines.append(node.start_point[0])
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return sorted(comment_lines)

class JavaChunker(BaseChunker):
    """
    Java-specific implementation of code chunking.
    """
    
    def __init__(self, file_extension: str, encoding_name: str = "cl100k_base"):
        """
        Initialize the JavaChunker.
        
        Args:
            file_extension: The file extension (should be 'java').
            encoding_name: The encoding name for token counting.
        """
        super().__init__(file_extension, encoding_name)
        self.parser = JavaCodeParser(file_extension)
    
    def _identify_code_sections(self, code: str, lines: List[str], file_name: str = None) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict], Optional[Dict]]:
        """
        Identify different sections of Java code.
        
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
            if node.type == 'class_declaration':
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
            if node.type == 'class_declaration':
                for child in node.children:
                    traverse_for_functions(child, True)
                return
            
            # Method declaration (standalone functions)
            if node.type == 'method_declaration' and not inside_class:
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
            # Process class declarations
            if node.type in ["class_declaration", "interface_declaration", "enum_declaration"]:
                # Extract entity name
                entity_name = self._extract_entity_name(node, lines)
                
                # Get boundaries
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                classes.append({
                    'name': entity_name,
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark these lines as accounted for
                for i in range(start_line, end_line + 1):
                    accounted_lines.add(i)
            
            # Process method declarations (only top-level ones, not in classes)
            elif node.type == "method_declaration":
                # Skip if this is a method inside a class (already covered)
                is_method = False
                parent_node = node.parent
                while parent_node:
                    if parent_node.type in ["class_declaration", "interface_declaration"]:
                        is_method = True
                        break
                    parent_node = parent_node.parent
                
                if not is_method:
                    # Extract method info
                    method_name = self._extract_method_name(node, lines)
                    
                    # Check if this is the main method
                    if method_name == "main" and "String[] args" in lines[node.start_point[0]]:
                        # Get boundaries
                        start_line = node.start_point[0]
                        end_line = node.end_point[0]
                        
                        # Create main code section
                        main_code = {
                            'start': start_line,
                            'end': end_line
                        }
                        
                        # Mark these lines as accounted for
                        for i in range(start_line, end_line + 1):
                            accounted_lines.add(i)
                        
                        return
                    
                    # Get method boundaries
                    start_line = node.start_point[0]
                    end_line = node.end_point[0]
                    
                    functions.append({
                        'name': method_name,
                        'start': start_line,
                        'end': end_line
                    })
                    
                    # Mark these lines as accounted for
                    for i in range(start_line, end_line + 1):
                        accounted_lines.add(i)
            
            # Process imports
            elif node.type == "import_declaration":
                # Get boundaries
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                
                imports.append({
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark these lines as accounted for
                for i in range(start_line, end_line + 1):
                    accounted_lines.add(i)
            
            # Process package declarations
            elif node.type == "package_declaration":
                # Get boundaries
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
    
    def _extract_entity_name(self, node, lines: List[str]) -> str:
        """Extract class/interface/enum name from a node"""
        try:
            # Try to find identifier node
            for child in node.children:
                if child.type == "identifier":
                    return lines[node.start_point[0]][child.start_point[1]:child.end_point[1]]
            
            # Fallback to text-based extraction
            line = lines[node.start_point[0]]
            
            if "class " in line:
                parts = line.split("class ")[1].split("{")[0].split("extends")[0].split("implements")[0].strip()
                return parts.split(" ")[0].strip()
            elif "interface " in line:
                parts = line.split("interface ")[1].split("{")[0].split("extends")[0].strip()
                return parts.split(" ")[0].strip()
            elif "enum " in line:
                parts = line.split("enum ")[1].split("{")[0].strip()
                return parts.split(" ")[0].strip()
        except Exception:
            pass
        
        return "unknown"
    
    def _extract_method_name(self, node, lines: List[str]) -> str:
        """Extract method name from a node"""
        try:
            # Try to find identifier node
            for child in node.children:
                if child.type == "identifier":
                    return lines[node.start_point[0]][child.start_point[1]:child.end_point[1]]
            
            # Fallback to text-based extraction
            line = lines[node.start_point[0]]
            
            # Simplistic extraction, more robust parsing may be needed
            if "(" in line:
                # Get the word before the opening parenthesis
                parts = line.split("(")[0].strip().split(" ")
                return parts[-1].strip()
        except Exception:
            pass
        
        return "unknown"
    
    def _identify_java_sections(self, lines: List[str], accounted_lines: Set[int], 
                              classes: List[Dict], functions: List[Dict], imports: List[Dict]):
        """
        Identify Java-specific sections that might not be caught by the parser.
        
        Args:
            lines: The code split into lines
            accounted_lines: Set of line numbers already accounted for
            classes: List to add class info to
            functions: List to add function info to
            imports: List to add import info to
        """
        # Find imports
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip already accounted lines
            if i in accounted_lines:
                continue
                
            # Track import statements
            if line.startswith("import "):
                imports.append({
                    'start': i,
                    'end': i
                })
                accounted_lines.add(i)
            
            # Track package declarations
            elif line.startswith("package "):
                imports.append({
                    'start': i,
                    'end': i
                })
                accounted_lines.add(i)
        
        # Look for class definitions
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip already accounted lines
            if i in accounted_lines:
                i += 1
                continue
                
            # Match class, interface, or enum patterns
            if (line.startswith("public class ") or 
                line.startswith("private class ") or 
                line.startswith("protected class ") or 
                line.startswith("class ") or
                line.startswith("public interface ") or
                line.startswith("private interface ") or
                line.startswith("protected interface ") or
                line.startswith("interface ") or
                line.startswith("public enum ") or
                line.startswith("private enum ") or
                line.startswith("protected enum ") or
                line.startswith("enum ")):
                
                # Extract entity name
                entity_name = ""
                
                if "class " in line:
                    entity_type = "class"
                    parts = line.split("class ")[1].split("{")[0].split("extends")[0].split("implements")[0].strip()
                    entity_name = parts.split(" ")[0].strip()
                elif "interface " in line:
                    entity_type = "interface"
                    parts = line.split("interface ")[1].split("{")[0].split("extends")[0].strip()
                    entity_name = parts.split(" ")[0].strip()
                elif "enum " in line:
                    entity_type = "enum"
                    parts = line.split("enum ")[1].split("{")[0].strip()
                    entity_name = parts.split(" ")[0].strip()
                
                if not entity_name:
                    i += 1
                    continue
                
                start_line = i
                
                # Find the end (matching closing brace)
                braces = 0
                end_line = i
                
                # Search for opening brace
                j = i
                while j < len(lines) and "{" not in lines[j]:
                    j += 1
                
                if j >= len(lines):
                    i += 1
                    continue
                
                # Count braces to find the end
                for j in range(i, len(lines)):
                    current_line = lines[j]
                    for char in current_line:
                        if char == '{':
                            braces += 1
                        elif char == '}':
                            braces -= 1
                            if braces == 0:
                                end_line = j
                                break
                    if braces == 0 and j > i:
                        break
                
                # Add to classes list
                classes.append({
                    'name': entity_name,
                    'start': start_line,
                    'end': end_line
                })
                
                # Mark lines as accounted for
                for k in range(start_line, end_line + 1):
                    accounted_lines.add(k)
                
                i = end_line + 1
            else:
                i += 1
        
        # Look for method definitions
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip already accounted lines
            if i in accounted_lines:
                i += 1
                continue
            
            # Skip comments
            if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
                i += 1
                continue
            
            # Look for method definitions
            if ("(" in line and ")" in line and 
                any(x in line for x in ["public ", "private ", "protected ", "static ", "void ", "String ", "int "]) and
                not line.endsWith(";")):
                
                # Extract method name
                method_name = ""
                
                # Simple method name extraction
                if "(" in line:
                    parts = line.split("(")[0].strip().split(" ")
                    method_name = parts[-1].strip()
                
                if not method_name or method_name in ["if", "while", "for", "switch"]:
                    i += 1
                    continue
                
                # Check for main method
                if method_name == "main" and "String[] args" in line:
                    # Will be handled by main code detection
                    i += 1
                    continue
                
                start_line = i
                
                # Find the method body
                braces = 0
                end_line = i
                
                # Search for opening brace
                j = i
                while j < len(lines) and "{" not in lines[j]:
                    j += 1
                
                if j >= len(lines):
                    i += 1
                    continue
                
                # Count braces to find the end
                for j in range(i, len(lines)):
                    current_line = lines[j]
                    for char in current_line:
                        if char == '{':
                            braces += 1
                        elif char == '}':
                            braces -= 1
                            if braces == 0:
                                end_line = j
                                break
                    if braces == 0 and j > i:
                        break
                
                # Add to functions list
                functions.append({
                    'name': method_name,
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
        """Identify Java main method"""
        for i, line in enumerate(lines):
            if i in accounted_lines:
                continue
                
            # Check for main method pattern
            if (("public static void main" in line or "static public void main" in line) and 
                "String[]" in line and "(" in line and ")" in line):
                
                start_line = i
                
                # Find the method body
                braces = 0
                end_line = i
                
                # Search for opening brace
                j = i
                while j < len(lines) and "{" not in lines[j]:
                    j += 1
                
                if j >= len(lines):
                    continue
                
                # Count braces to find the end
                for j in range(i, len(lines)):
                    current_line = lines[j]
                    for char in current_line:
                        if char == '{':
                            braces += 1
                        elif char == '}':
                            braces -= 1
                            if braces == 0:
                                end_line = j
                                break
                    if braces == 0 and j > i:
                        break
                
                # Mark lines as accounted for
                for k in range(start_line, end_line + 1):
                    accounted_lines.add(k)
                    
                print(f"Found Java main method: {start_line+1} to {end_line+1}")
                return {
                    'start': start_line,
                    'end': end_line
                }
                
        return None 