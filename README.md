# GitSummarizer-RAG

A Retrieval-Augmented Generation (RAG) based tool for summarizing and querying GitHub repositories. This tool allows users to extract meaningful information from codebases by leveraging language models and vector databases.

## Features

- **Repository Retrieval**: Clone any GitHub repository using just the URL
- **Intelligent Code Chunking**: Break down code into semantically meaningful chunks
- **Vector Storage with Pinecone**: Store code embeddings for efficient retrieval
- **Multiple LLM Support**: Query your codebase using different language models
- **Semantic Search**: Find relevant code snippets based on natural language queries

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/GitSummarizer-RAG.git
cd GitSummarizer-RAG
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

## Usage

1. Run the main script:
```bash
python main.py
```

2. Follow the prompts to:
   - Enter a GitHub repository URL
   - Choose embedding and language model options
   - Ask questions about the codebase

## Project Structure

- `main.py`: Entry point for the application
- `github_retriever.py`: Handles GitHub repository retrieval
- `code_chunker.py`: Contains code chunking logic
- `vector_store.py`: Manages Pinecone vector storage and retrieval
- `llm_interface.py`: Provides interfaces for different language models
- `config.py`: Configuration settings for the application
- `utils.py`: Utility functions

## Examples

```python
# Example usage in code
from gitsummarizer import GitSummarizer

summarizer = GitSummarizer()
summarizer.load_repository("https://github.com/example/repo")
response = summarizer.query("Explain the main architecture of this codebase")
print(response)
```

## License

MIT License 