# GitSummarizer-RAG

A powerful tool that allows users to analyze GitHub repositories using RAG (Retrieval-Augmented Generation) techniques and ask natural language questions about the codebase.

## Project Overview

GitSummarizer-RAG consists of two main components:

1. **Backend**: A Python-based RAG system that processes GitHub repositories, chunks code, stores it in a vector database, and answers questions using LLMs.
2. **Frontend**: A modern web interface that allows users to input GitHub repository URLs, ask questions, and view summaries and answers.

## Features

- **Repository Analysis**: Clone and analyze any public GitHub repository
- **Code Chunking**: Intelligent code chunking with parse tree analysis for better context
- **Vector Search**: Semantic search capabilities using Pinecone
- **Natural Language Queries**: Ask questions about the codebase in plain English
- **Repository Summaries**: Generate comprehensive summaries of repositories
- **Web Interface**: User-friendly interface for interacting with the system

## Project Structure

```
GitSummarizer-RAG/
├── backend/           # Python RAG system
│   ├── code_chunker.py        # Code parsing and chunking
│   ├── github_retriever.py    # GitHub repository handling
│   ├── llm_interface.py       # LLM interaction
│   ├── main.py                # Main application logic
│   ├── vector_store.py        # Vector database operations
│   ├── utils.py               # Utility functions
│   ├── config.py              # Configuration settings
│   ├── api.py                 # API endpoints (new)
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
├── frontend/          # Web interface
│   ├── public/               # Static assets
│   ├── src/                  # React/Next.js source code
│   ├── package.json          # Frontend dependencies
│   └── ...                   # Other frontend files
└── README.md          # This file
```

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Create a `.env` file in the backend directory with:
     ```
     OPENAI_API_KEY=your_openai_api_key
     PINECONE_API_KEY=your_pinecone_api_key
     ```

4. Run the API server:
   ```bash
   python api.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to [http://localhost:3000](http://localhost:3000)

## Usage

1. Enter a GitHub repository URL in the input field
2. Wait for the system to process the repository
3. Ask questions about the codebase or view the repository summary
4. Explore the codebase with natural language queries

## License

[MIT License](LICENSE)

## Acknowledgments

- OpenAI for language model APIs
- Pinecone for vector database
- Next.js for the frontend framework 