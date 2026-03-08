$ErrorActionPreference = "Stop"

Write-Host "🛠️ Initializing Aetherlink 4080 Super Environment..." -ForegroundColor Cyan

# 1. Sync dependencies
Write-Host "📦 Syncing project dependencies with uv..." -ForegroundColor Cyan
uv sync --group dev --group automation

# 2. Start Optimized llama.cpp Engine
# Check if llama-server is already running on port 8080
$llamaProc = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue

if (!$llamaProc) {
    Write-Host "🚀 Starting Optimized llama.cpp Engine (4080 Super)..." -ForegroundColor Cyan
    
    $llamaArgs = @(
        "--models-dir", "C:\Users\Dada\.cache\lm-studio\models",
        "--n-gpu-layers", "99",
        "--ctx-size", "32768",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--flash-attn",
        "--parallel", "4",
        "--port", "8080"
    )
    
    # Start llama-server in a new minimized window
    Start-Process "C:\Path\To\llama.cpp\build\bin\Release\llama-server.exe" -ArgumentList $llamaArgs -WindowStyle Minimized
    Start-Sleep -Seconds 5
} else {
    Write-Host "✅ llama.cpp Engine is already active on port 8080." -ForegroundColor Green
}

# 3. Restart LiteLLM Proxy (Updated for llama.cpp backend)
Write-Host "♻️ Restarting LiteLLM Traffic Controller..." -ForegroundColor Cyan

# Clean up any existing LiteLLM processes
$liteLlmProcs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*litellm*" -and $_.CommandLine -like "*--port 4000*"
}
foreach ($proc in $liteLlmProcs) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uv run litellm --config .cursor/config/router.yaml --port 4000" -WindowStyle Minimized
Write-Host "✅ LiteLLM Proxy restarted on port 4000." -ForegroundColor Green

# 4. Handle ngrok Tunnel (Bypassing Cursor's localhost restriction)
if (!(Get-Process "ngrok" -ErrorAction SilentlyContinue)) {
    Write-Host "🌐 Starting ngrok Tunnel..." -ForegroundColor Cyan
    Start-Process "ngrok" -ArgumentList "http", "4000" -WindowStyle Minimized
    Write-Host "⚠️ Remember to update Cursor with the new ngrok URL!" -ForegroundColor Yellow
}

# 5. Directory Maintenance
$dirs = "src", "tests", "docs", "assets", "config"
foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir
        Write-Host "Created directory: $dir"
    }
}

Write-Host "🚀 Aetherlink ready! Use your 1300-line plan_exec.PY with maximum 4080 Super power." -ForegroundColor Magenta