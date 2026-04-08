# ============================================
# Conda Environment Setup Script (PowerShell)
# ============================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Conda Environment Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Conda is installed
Write-Host "Checking for Conda installation..." -ForegroundColor Yellow
try {
    $condaPath = (conda info --base)
} catch {
    Write-Host "Error: Conda is not installed or not in PATH, please install Conda and add it to your PATH to continue." -ForegroundColor Red
    Read-Host "Press enter to exit"
    exit 1
}

Write-Host "Check: Conda found" -ForegroundColor Green
Write-Host ""

# Setup variables
$ENV_NAME = "PortfolioEnv"
$ENV_PATH = "$condaPath\envs\$ENV_NAME"
$PYTHON_PATH = "$ENV_PATH\python.exe"

Write-Host "Conda base: $condaPath"
Write-Host "Environment name: $ENV_NAME"
Write-Host "Environment path: $ENV_PATH"
Write-Host "Python path: $PYTHON_PATH"
Write-Host ""

# Check if environment exists
Write-Host "Checking for existing environment..." -ForegroundColor Yellow
$envList = conda env list
$envExists = $envList | Select-String "^$ENV_NAME "

if ($envExists) {
    Write-Host "Environment '$ENV_NAME' already exists." -ForegroundColor Yellow
    Write-Host "Updating environment with environment.yml..." -ForegroundColor Yellow
    conda env update -n $ENV_NAME -f environment.yml --prune
    Write-Host "Check: Environment updated" -ForegroundColor Green
} else {
    Write-Host "Creating Conda environment from environment.yml..." -ForegroundColor Yellow
    conda env create -n $ENV_NAME -f environment.yml
    Write-Host "Check: Environment created successfully" -ForegroundColor Green
}

Write-Host ""

# Create .vscode directory
if (!(Test-Path ".vscode")) {
    New-Item -ItemType Directory -Name ".vscode" | Out-Null
    Write-Host "Created .vscode directory"
}

# Create settings.json with terminal profile and Python path
Write-Host "Creating VS Code settings..." -ForegroundColor Yellow

# Build the JSON object using ConvertTo-Json to avoid escaping issues
$settings = @{
    "terminal.integrated.profiles.windows" = @{
        "Command Prompt (PortfolioEnv)" = @{
            "path" = "C:\WINDOWS\System32\cmd.exe"
            "args" = @(
                "/K",
                "$condaPath\Scripts\activate.bat && conda activate $ENV_NAME"
            )
        }
    }
    "terminal.integrated.defaultProfile.windows" = "Command Prompt (PortfolioEnv)"
    "python.defaultInterpreterPath" = $PYTHON_PATH
    "python.linting.enabled" = $true
    "python.linting.flake8Enabled" = $true
    "python.formatting.provider" = "black"
    "[python]" = @{
        "editor.defaultFormatter" = "ms-python.python"
        "editor.formatOnSave" = $true
    }
    "python.analysis.typeCheckingMode" = "basic"
}

$settings | ConvertTo-Json -Depth 10 | Set-Content ".vscode\settings.json"

Write-Host "Check: VS Code settings created at .vscode/settings.json" -ForegroundColor Green
Write-Host ""

# Display what was created
Write-Host "Created settings.json with:" -ForegroundColor Green
Write-Host "  - Terminal profile: Command Prompt (PortfolioEnv)"
Write-Host "  - Conda activation: $condaPath\Scripts\activate.bat && conda activate $ENV_NAME"
Write-Host "  - Python path: $PYTHON_PATH"
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:"
Write-Host "  Environment Name: $ENV_NAME"
Write-Host "  Environment Path: $ENV_PATH"
Write-Host "  Python Path: $PYTHON_PATH"
Write-Host "  Settings File: .vscode/settings.json"
Write-Host "  Dependencies: environment.yml"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Close VS Code completely"
Write-Host "  2. Reopen VS Code"
Write-Host "  3. Open a new terminal (Ctrl + ``) - it will auto-activate $ENV_NAME"
Write-Host ""
Write-Host "You should see:"
Write-Host "  ($ENV_NAME) C:\Users\...>" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press enter to exit"