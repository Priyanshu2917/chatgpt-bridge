# ============================================
# ChatGPT Bridge - First Time Setup
# ============================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   ChatGPT Bridge - Setup Starting..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get project directory
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

# --------------------------------------------
# Check Python
# --------------------------------------------

Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow

try {
    python --version
}
catch {
    Write-Host ""
    Write-Host "ERROR: Python is not installed or not added to PATH." -ForegroundColor Red
    Write-Host "Please install Python and enable 'Add Python to PATH'." -ForegroundColor Red
    exit 1
}

# --------------------------------------------
# Create Virtual Environment
# --------------------------------------------

Write-Host ""
Write-Host "[2/4] Checking virtual environment..." -ForegroundColor Yellow

if (-Not (Test-Path ".\venv")) {

    Write-Host "Creating virtual environment..." -ForegroundColor Cyan

    python -m venv venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }

    Write-Host "Virtual environment created successfully." -ForegroundColor Green
}
else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# --------------------------------------------
# Activate Virtual Environment
# --------------------------------------------

Write-Host ""
Write-Host "[3/4] Activating virtual environment..." -ForegroundColor Yellow

& ".\venv\Scripts\Activate.ps1"

# --------------------------------------------
# Install Dependencies
# --------------------------------------------

Write-Host ""
Write-Host "[4/4] Installing required packages..." -ForegroundColor Yellow

python -m pip install --upgrade pip

python -m pip install `
    fastapi `
    uvicorn `
    playwright `
    pyperclip `
    pydantic

Write-Host ""
Write-Host "Installing Playwright browser..." -ForegroundColor Yellow

python -m playwright install chromium

# --------------------------------------------
# Setup Complete
# --------------------------------------------

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "        SETUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

 