import os
import time
from typing import List, Dict, Any, Optional
import sys
import json

from chunkers import get_chunker_for_extension

class CodeChunker:
    """
    Main entry point for code chunking.
    This class delegates chunking to specialized language-specific chunkers.
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
        self.chunker = get_chunker_for_extension(file_extension, encoding_name)
    
    def chunk(self, code: str, token_limit: int = None, file_name: str = None) -> List[Dict[str, Any]]:
        """
        Chunk the code into semantically meaningful segments.
        Delegates to the appropriate language-specific chunker.
        
        Args:
            code: The code to chunk.
            token_limit: Maximum tokens per chunk. Defaults to config value if None.
            file_name: Name of the file (not full path) to associate with chunks
            
        Returns:
            List of dictionaries containing chunk information.
        """
        return self.chunker.chunk(code, token_limit, file_name)
    
    def get_chunk(self, chunked_codebase: List[Dict[str, Any]], chunk_number: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk from the chunked codebase.
        
        Args:
            chunked_codebase: The chunked codebase.
            chunk_number: The chunk number to retrieve.
            
        Returns:
            The specified chunk or None if not found.
        """
        return self.chunker.get_chunk(chunked_codebase, chunk_number)


if __name__ == "__main__":
    import os
    import sys
    import json
    
    # Use command line arg as file path or default to the chunker file itself
    file_path = sys.argv[1] if len(sys.argv) > 1 else "code_chunker.py"
    
    # Extract file extension and file name from path
    file_extension = os.path.splitext(file_path)[1][1:]  # Remove the dot
    file_name = os.path.basename(file_path)  # Get just the file name, not the path
    
    # print(f"\nProcessing file: {file_name} (extension: {file_extension})")
    
    # Create chunker and read the file
    chunker = CodeChunker(file_extension)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Chunk the code with file name
        # print(f"Starting chunking process with simplified strategy:")
        # print(f"  1. Class chunks - one per class")
        # print(f"  2. Function chunks - one per function")
        # print(f"  3. Everything else in one chunk\n")
        
        chunks = chunker.chunk(code, file_name=file_name)
        
        if chunks:
            class_chunks = [c for c in chunks if c.get('class_name')]
            function_chunks = [c for c in chunks if c.get('function_name') and not c.get('class_name')]
            other_chunks = [c for c in chunks if not c.get('class_name') and not c.get('function_name') or c.get('function_name') == 'other']
            
            # print(f"Chunking complete. Found {len(chunks)} chunks:")
            # print(f"  - {len(class_chunks)} class chunks")
            # print(f"  - {len(function_chunks)} function chunks")
            # print(f"  - {len(other_chunks)} other chunks\n")
        else:
            print(f"No chunks were created for {file_name}\n")
        
        # Write chunks to output file
        if os.path.exists("chunks.txt"):
            os.remove("chunks.txt")
        
        with open("chunks.txt", "w", encoding="utf-8") as f:
            if not chunks:
                f.write(f"No chunks were found in the file: {file_name}\n")
            else:
                for i, chunk in enumerate(chunks):
                    f.write(f"Chunk {i + 1}:\n")
                    f.write(f"Start Line: {chunk['start_line']}\n")
                    f.write(f"End Line: {chunk['end_line']}\n")
                    f.write(f"Token Count: {chunk['token_count']}\n")
                    
                    # Always include file name for better traceability
                    f.write(f"File Name: {chunk.get('file_name', 'Unknown')}\n")
                    
                    if chunk.get('class_name'):
                        f.write(f"Class Name: {chunk['class_name']}\n")
                    
                    if chunk.get('function_name') and chunk.get('function_name') != 'other':
                        f.write(f"Function Name: {chunk['function_name']}\n")
                    
                    chunk_type = "Class" if chunk.get('class_name') else ("Function" if chunk.get('function_name') and chunk.get('function_name') != 'other' else "Other Code")
                    f.write(f"Chunk Type: {chunk_type}\n")
                    
                    f.write("Chunk Content:\n")
                    f.write(chunk['chunk'])
                    f.write("\n\n")
                
                # Also save as JSON for easier programmatic access
                with open("chunks.json", "w", encoding="utf-8") as json_file:
                    # We need to convert the chunks to a serializable format
                    serializable_chunks = []
                    for chunk in chunks:
                        serializable_chunk = {k: v for k, v in chunk.items()}
                        # Add chunk type for easier categorization
                        if chunk.get('class_name'):
                            serializable_chunk['chunk_type'] = 'Class'
                        elif chunk.get('function_name') and chunk.get('function_name') != 'other':
                            serializable_chunk['chunk_type'] = 'Function'
                        else:
                            serializable_chunk['chunk_type'] = 'Other Code'
                        
                        serializable_chunks.append(serializable_chunk)
                    
                    json.dump(serializable_chunks, json_file, indent=2)
        
        print(f"Processed {file_name} - {len(chunks)} chunks have been written to chunks.txt")
        # if chunks:
        #     print("Machine-readable format also saved to chunks.json")
            
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        import traceback
        traceback.print_exc() 