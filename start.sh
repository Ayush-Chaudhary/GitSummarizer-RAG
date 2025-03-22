#!/bin/bash

# Check if Python and Node.js are installed
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed or not in PATH. Please install Python first."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "Node.js is not installed or not in PATH. Please install Node.js first."
    exit 1
fi

# Clean up any existing lock files
if [ -f "backend/.processing_lock" ]; then
    rm backend/.processing_lock
    echo "Removed stale processing lock file"
fi

# Start the backend server
echo "Starting backend server..."
(cd backend && python3 api.py) &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 2

# Start the frontend server
echo "Starting frontend server..."
cd frontend && npm run dev &
FRONTEND_PID=$!

# Function to handle exit and kill both servers
function cleanup {
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID
    exit 0
}

# Register the cleanup function for the SIGINT and SIGTERM signals
trap cleanup SIGINT SIGTERM

echo "Both servers are running!"
echo "Backend API: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both servers."

# Wait for user to press Ctrl+C
wait $FRONTEND_PID 