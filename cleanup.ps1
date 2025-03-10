#!/usr/bin/env pwsh
# Cleanup script for GitSummarizer-RAG

Write-Host "Cleaning up cached directories..." -ForegroundColor Cyan

# Clean frontend caches
if (Test-Path "frontend\.next") {
    Write-Host "Removing frontend/.next directory..." -ForegroundColor Yellow
    Remove-Item -Path "frontend\.next" -Recurse -Force
}

# Clean backend caches
Write-Host "Removing Python cache directories..." -ForegroundColor Yellow
Get-ChildItem -Path "backend" -Include "__pycache__" -Directory -Recurse | 
    ForEach-Object { 
        Write-Host "Removing $_" -ForegroundColor Yellow
        Remove-Item -Path $_.FullName -Recurse -Force 
    }

# Clean root __pycache__ if it exists
if (Test-Path "__pycache__") {
    Write-Host "Removing root __pycache__ directory..." -ForegroundColor Yellow
    Remove-Item -Path "__pycache__" -Recurse -Force
}

# Clean temporary repo directory
if (Test-Path "temp_repos") {
    Write-Host "Removing temp_repos directory..." -ForegroundColor Yellow
    Remove-Item -Path "temp_repos" -Recurse -Force -ErrorAction SilentlyContinue
    # Recreate the directory
    New-Item -Path "temp_repos" -ItemType Directory | Out-Null
}

# Also create a temp_repos directory in the backend if it doesn't exist
if (-not (Test-Path "backend\temp_repos")) {
    Write-Host "Creating backend/temp_repos directory..." -ForegroundColor Yellow
    New-Item -Path "backend\temp_repos" -ItemType Directory | Out-Null
}

Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "You can now start the backend and frontend applications." -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "To start the backend:" -ForegroundColor Cyan
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  python api.py" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "To start the frontend:" -ForegroundColor Cyan
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm install" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White 