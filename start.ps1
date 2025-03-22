# PowerShell script to start both the frontend and backend services

# First, check if both Python and Node.js are installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python first."
    exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is not installed or not in PATH. Please install Node.js first."
    exit 1
}

# Clean up any existing lock files
if (Test-Path "$PSScriptRoot\backend\.processing_lock") {
    Remove-Item "$PSScriptRoot\backend\.processing_lock" -Force
    Write-Host "Removed stale processing lock file"
}

# Set up the backend server in a new window
Start-Process powershell -ArgumentList "-Command cd $PSScriptRoot; cd backend; python api.py"

# Wait a moment to ensure backend starts first
Start-Sleep -Seconds 2

# Start the frontend server
Write-Host "Starting frontend server..."
Set-Location -Path "$PSScriptRoot\frontend"
npm run dev

# Inform the user
Write-Host "Both servers are running!"
Write-Host "Backend API: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Press Ctrl+C to stop the frontend server." 