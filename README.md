# GitSummarizer-RAG

A powerful tool that allows users to analyze GitHub repositories using RAG (Retrieval-Augmented Generation) techniques and ask natural language questions about the codebase.

## Project Overview

GitSummarizer-RAG consists of two main components:

1. **Backend**: A Python-based RAG system that processes GitHub repositories, chunks code, stores it in a vector database, and answers questions using LLMs.
2. **Frontend**: A minimalist web interface that allows users to input GitHub repository URLs, ask questions, and view summaries and answers.

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
├── backend/               # Python RAG system
│   ├── api.py             # FastAPI server for backend
│   ├── code_chunker.py    # Code parsing and chunking
│   ├── chunkers/          # Language-specific chunkers
│   ├── config.py          # Configuration settings
│   ├── github_retriever.py # GitHub repository handling
│   ├── llm_interface.py   # LLM interaction
│   ├── main.py            # Main application logic
│   ├── utils.py           # Utility functions
│   ├── vector_store.py    # Vector database operations
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment variables (create this)
├── frontend/              # Web interface
│   ├── public/            # Static HTML
│   ├── src/               # JavaScript source code
│   │   ├── css/           # Stylesheets
│   │   └── js/            # JavaScript files
│   ├── server.js          # Express server for frontend
│   └── package.json       # Frontend dependencies
└── start.ps1              # PowerShell script to start both servers
```

## Getting Started

### Prerequisites

- Python 3.9+ with pip
- Node.js 14+ with npm
- OpenAI API key
- Pinecone API key (free tier available)

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
     PINECONE_ENVIRONMENT=your_pinecone_environment
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

### Using the Start Script (Windows)

For convenience, you can use the provided PowerShell script to start both servers at once:

```powershell
.\start.ps1
```

## Usage

1. Enter a GitHub repository URL in the input field
2. Click "Analyze" and wait for the system to process the repository
3. Once loaded, you can:
   - Ask questions about the codebase in the Chat tab
   - View the repository summary in the Summary tab
4. Use the "Analyze Another Repository" button to start over

## Deployment

The application can be deployed using various cloud platforms:

1. **Render.com** (recommended for beginners): Deploy frontend as a Static Site and backend as a Web Service.
2. **Railway.app**: Simple deployment for both frontend and backend.
3. **Vercel + Heroku**: Deploy frontend to Vercel and backend to Heroku.
4. **AWS Free Tier**: Use EC2 or Elastic Beanstalk (more complex setup).

Remember that while hosting platforms offer free tiers, there will be costs associated with:
- OpenAI API usage (typically $0.01-0.02 per query)
- Pinecone vector database usage (free tier available but limited)

## License

[MIT License](LICENSE)

## Acknowledgments

- OpenAI for language model APIs
- Pinecone for vector database
- Express.js for the web server 