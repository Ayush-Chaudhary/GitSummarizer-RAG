# GitSummarizer Frontend

A minimalist, sleek web interface for the GitSummarizer-RAG application. This frontend allows users to analyze GitHub repositories, view summaries, and ask questions about the codebase.

## Features

- Analyze any GitHub repository
- View a comprehensive summary of the repository
- Query the repository with natural language questions
- Clean, minimalist UI with responsive design

## Directory Structure

```
frontend/
├── public/            # Static HTML files
├── src/               # Source code
│   ├── css/           # Stylesheets
│   └── js/            # JavaScript files
│       ├── api.js     # Backend API service
│       └── app.js     # Main application code
├── server.js          # Express web server
├── package.json       # Dependencies
└── README.md          # This file
```

## Setup

### Prerequisites

- Node.js (v14 or newer)
- npm or yarn
- Backend API server running (see main README for backend setup)

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

This will start the frontend server at http://localhost:3000.

## API Configuration

The API URL is configured in `src/js/api.js`. By default, it points to `http://localhost:8000/api`. If you deploy the backend elsewhere, update this URL.

## Deployment

To deploy the frontend to production:

1. Update the API URL in `src/js/api.js` to point to your deployed backend
2. Build the project for production (optional optimization step):
   ```bash
   npm run build
   ```
3. Start the server:
   ```bash
   npm start
   ```

## Functions

- **Repository Loading**: Handles loading and processing GitHub repositories
- **Status Tracking**: Monitors processing status with progress indicators
- **Query Interface**: Sends questions to the backend and displays responses
- **Summary View**: Displays the generated repository summary
- **Navigation Protection**: Prevents page refreshes during critical processing

## Usage

1. Enter a GitHub repository URL (e.g., https://github.com/username/repo)
2. Click "Analyze" and wait for the processing to complete
3. Once loaded, you can:
   - Ask questions about the repository in the Chat tab
   - View a summary of the repository structure in the Summary tab
4. Use the "Analyze Another Repository" button to start over

## Configuration

The API URL is configured in `/src/js/api.js`. By default, it points to `http://localhost:8000/api`. Update this if your backend is hosted elsewhere.

## Development

- HTML files are in `/public`
- CSS styles are in `/src/css`
- JavaScript files are in `/src/js` 