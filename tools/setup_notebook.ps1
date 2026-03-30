# Setup script for secondary machines (e.g., Notebook)
# This script installs required CLI tools and extensions.

Write-Host "Starting Studio Brain Notebook Setup..." -ForegroundColor Cyan

# 1. Check for Node.js (Required for Gemini CLI and Claude Code)
if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js/npm is not installed. Please install it from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# 2. Install AI CLIs
Write-Host "`n[1/4] Installing AI CLIs..." -ForegroundColor Yellow
npm install -g @google/gemini-cli
npm install -g @anthropic-ai/claude-code

# 3. Install Gemini Extensions (Google Workspace)
Write-Host "`n[2/4] Installing Gemini CLI Extensions..." -ForegroundColor Yellow
# Assuming the user uses the standard extension installation command for gemini
gemini extension install @google/gemini-workspace-extension

# 4. Check for GitHub CLI
Write-Host "`n[3/4] Checking GitHub CLI..." -ForegroundColor Yellow
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: GitHub CLI (gh) is not installed. Please install it from https://cli.github.com/" -ForegroundColor DarkYellow
} else {
    Write-Host "GitHub CLI is installed. Run 'gh auth login' if you haven't already." -ForegroundColor Green
}

# 5. Setup Python Virtual Environment (Optional, for scripts)
Write-Host "`n[4/4] Setting up Python Environment (Optional)..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    if (!(Test-Path .venv)) {
        Write-Host "Creating virtual environment in .venv..."
        python -m venv .venv
    }
    Write-Host "Activating virtual environment and installing requirements..."
    .venv\Scripts\Activate.ps1
    if (Test-Path pipeline\requirements.txt) {
        pip install -r pipeline\requirements.txt
    }
} else {
    Write-Host "WARNING: Python is not installed. Skipping Python setup." -ForegroundColor DarkYellow
}

Write-Host "`nSetup Complete!" -ForegroundColor Green
Write-Host "------------------------------------------------"
Write-Host "Next Steps:"
Write-Host "1. Run 'gemini' and provide your API key."
Write-Host "2. Run 'gh auth login' to connect to GitHub."
Write-Host "3. (Optional) Set GOOGLE_APPLICATION_CREDENTIALS for Python scripts."
Write-Host "------------------------------------------------"
