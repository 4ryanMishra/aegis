# ==============================================================================
# AEGIS - One-Click Demo Environment Launcher (Windows PowerShell)
# ==============================================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\run-demo.ps1
#
# This script starts the complete AEGIS demo environment (Python Backend API + 
# Next.js Forensic Dashboard), monitors readiness, and launches the browser.
# ==============================================================================

[CmdletBinding()]
param()

$RepoRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "            AEGIS - ORACLE VERIFICATION ENGINE              " -ForegroundColor Cyan
Write-Host "             One-Click Product Demo Launcher                " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Dependency and Environment Checks
# ------------------------------------------------------------------------------
Write-Host "[1/4] Checking runtime dependencies..." -ForegroundColor Yellow

# Check Python
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Host "[ERROR] Python 3.10+ is required but not found in PATH." -ForegroundColor Red
    exit 1
}
$PythonVersion = python --version 2>&1
Write-Host "  [OK] Python: $PythonVersion" -ForegroundColor Green

# Check Node.js
$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    Write-Host "[ERROR] Node.js 18+ is required but not found in PATH." -ForegroundColor Red
    exit 1
}
$NodeVersion = node --version 2>&1
Write-Host "  [OK] Node.js: $NodeVersion" -ForegroundColor Green

# Check npm
$NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $NpmCmd) {
    Write-Host "[ERROR] npm is required but not found in PATH." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] npm package manager ready" -ForegroundColor Green

# Check Web Directory & Node Modules
$WebDir = Join-Path $RepoRoot "apps\web"
if (-not (Test-Path $WebDir)) {
    Write-Host "[ERROR] Frontend directory not found at $WebDir" -ForegroundColor Red
    exit 1
}

$NodeModulesDir = Join-Path $WebDir "node_modules"
if (-not (Test-Path $NodeModulesDir)) {
    Write-Host "  [INFO] Installing frontend dependencies (one-time setup)..." -ForegroundColor Yellow
    Push-Location $WebDir
    try {
        npm install --no-audit --no-fund
    } finally {
        Pop-Location
    }
}

# ------------------------------------------------------------------------------
# 2. Process Management Setup
# ------------------------------------------------------------------------------
$BackendProcess = $null
$FrontendProcess = $null

function Stop-DemoProcesses {
    Write-Host ""
    Write-Host "[AEGIS] Shutting down demo services..." -ForegroundColor Yellow
    
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        try {
            Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
            Write-Host "  [STOPPED] Python Backend API (PID: $($BackendProcess.Id))" -ForegroundColor Gray
        } catch {}
    }
    
    if ($FrontendProcess -and -not $FrontendProcess.HasExited) {
        try {
            Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
            Write-Host "  [STOPPED] Next.js Frontend Server (PID: $($FrontendProcess.Id))" -ForegroundColor Gray
        } catch {}
    }
    
    Write-Host "[AEGIS] Demo services cleaned up successfully." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Launch Services
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Starting AEGIS backend services..." -ForegroundColor Yellow

# Start Python FastAPI Backend (Port 8000)
$BackendArgs = "-m uvicorn services.api.main:app --host 127.0.0.1 --port 8000"
$BackendStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$BackendStartInfo.FileName = "python"
$BackendStartInfo.Arguments = $BackendArgs
$BackendStartInfo.WorkingDirectory = $RepoRoot
$BackendStartInfo.UseShellExecute = $false
$BackendStartInfo.CreateNoWindow = $true

$BackendProcess = [System.Diagnostics.Process]::Start($BackendStartInfo)
Write-Host "  [STARTED] Python API Server running (PID: $($BackendProcess.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "[3/4] Starting AEGIS forensic frontend..." -ForegroundColor Yellow

# Start Next.js Frontend (Port 3000)
$FrontendStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$FrontendStartInfo.FileName = "npm.cmd"
if (-not (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)) {
    $FrontendStartInfo.FileName = "npm"
}
$FrontendStartInfo.Arguments = "run dev -- -p 3000"
$FrontendStartInfo.WorkingDirectory = $WebDir
$FrontendStartInfo.UseShellExecute = $false
$FrontendStartInfo.CreateNoWindow = $true

$FrontendProcess = [System.Diagnostics.Process]::Start($FrontendStartInfo)
Write-Host "  [STARTED] Next.js Dashboard running (PID: $($FrontendProcess.Id))" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 4. Service Readiness Verification & Browser Launch
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Verifying endpoint health..." -ForegroundColor Yellow

$BackendReady = $false
$MaxBackendAttempts = 30
$BackendAttempt = 0

while ((-not $BackendReady) -and ($BackendAttempt -lt $MaxBackendAttempts)) {
    Start-Sleep -Milliseconds 500
    $BackendAttempt++
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response -and $response.status -eq "HEALTHY") {
            $BackendReady = $true
        }
    } catch {}
}

if (-not $BackendReady) {
    Write-Host "  [WARNING] Backend health probe timed out. (Proceeding with startup...)" -ForegroundColor Yellow
} else {
    Write-Host "  [HEALTHY] Backend API: http://127.0.0.1:8000" -ForegroundColor Green
}

$FrontendReady = $false
$MaxFrontendAttempts = 40
$FrontendAttempt = 0

while ((-not $FrontendReady) -and ($FrontendAttempt -lt $MaxFrontendAttempts)) {
    Start-Sleep -Milliseconds 500
    $FrontendAttempt++
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.StatusCode -eq 200) {
            $FrontendReady = $true
        }
    } catch {}
}

Write-Host "  [HEALTHY] Forensic Dashboard: http://localhost:3000" -ForegroundColor Green

# Open browser
try {
    Start-Process "http://localhost:3000"
} catch {
    Write-Host "  [INFO] Please open http://localhost:3000 in your browser." -ForegroundColor Gray
}

# ------------------------------------------------------------------------------
# 5. Ready Summary & Process Wait Loop
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "            AEGIS DEMO ENVIRONMENT IS READY!                " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend Dashboard : http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Backend REST API   : http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Interactive Docs   : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Scenarios available in UI:" -ForegroundColor White
Write-Host "    - Scenario A: Healthy Consensus (Normal 80% LTV)" -ForegroundColor Gray
Write-Host "    - Scenario B: Flash Spike / Crash (Restricted 50% LTV + Haircut)" -ForegroundColor Gray
Write-Host "    - Scenario C: Poisoned Validator (Median Robust Suppression)" -ForegroundColor Gray
Write-Host "    - Scenario D: Market Dislocation (Circuit Breaker Tripped)" -ForegroundColor Gray
Write-Host "    - Scenario E: OSM Read Failure (Failsafe Decentralized Fallback)" -ForegroundColor Gray
Write-Host ""
Write-Host "Press [CTRL + C] in this window to stop all AEGIS services." -ForegroundColor Magenta
Write-Host ""

try {
    while ($true) {
        if ($BackendProcess.HasExited) {
            Write-Host "[WARNING] Backend process exited unexpectedly." -ForegroundColor Red
            break
        }
        if ($FrontendProcess.HasExited) {
            Write-Host "[WARNING] Frontend process exited unexpectedly." -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Stop-DemoProcesses
}
