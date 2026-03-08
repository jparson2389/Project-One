$ErrorActionPreference = "Stop"

Write-Host "Initializing Aetherlink 4080 Super Environment..." -ForegroundColor Cyan

# 1. Sync dependencies
Write-Host "Syncing project dependencies with uv..." -ForegroundColor Cyan
uv sync --group dev --group automation

# 2. Start llama.cpp Engine with Speculative Decoding
$llamaProc = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue

if (!$llamaProc) {
    Write-Host "Starting llama.cpp Engine (RTX 4080 Super + Speculative Decoding)..." -ForegroundColor Cyan

    $llamaExe = "C:\Users\Dada\AI_Tools\llama.cpp\build\bin\Release\llama-server.exe"
    $mainModel = "C:\Users\Dada\.lmstudio\models\lmstudio-community\Qwen2.5-Coder-14B-Instruct-GGUF\Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"
    $draftModel = "C:\Users\Dada\.lmstudio\models\lmstudio-community\Qwen2.5-Coder-0.5B-Instruct-GGUF\Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf"

    $llamaArgs = @(
        "--model", $mainModel,
        "--model-draft", $draftModel,
        "--n-gpu-layers", "99",
        "--n-gpu-layers-draft", "99",
        "--ctx-size", "32768",
        "--flash-attn", "on",
        "--parallel", "4",
        "--draft", "8",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--port", "8080",
        "--host", "127.0.0.1"
    )

    Start-Process $llamaExe -ArgumentList $llamaArgs -WindowStyle Normal

    Write-Host "Waiting for llama-server to initialize..." -ForegroundColor Yellow
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {}
    }

    if ($ready) {
        Write-Host "llama-server is ready on port 8080." -ForegroundColor Green
    } else {
        Write-Host "ERROR: llama-server did not respond within 60s. Check the server window." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "llama-server already active on port 8080." -ForegroundColor Green
}

# NOTE: ngrok is not started by default.
# Uncomment below only if Cursor is blocking localhost connections.
#
# if (!(Get-Process "ngrok" -ErrorAction SilentlyContinue)) {
#     Start-Process "ngrok" -ArgumentList "http", "8080" -WindowStyle Minimized
#     Write-Host "Update Cursor with the new ngrok URL." -ForegroundColor Yellow
# }

# 3. Directory Maintenance
$dirs = "src", "tests", "docs", "assets", "config"
foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Created directory: $dir"
    }
}

Write-Host "Aetherlink ready. Engine running at http://127.0.0.1:8080/v1" -ForegroundColor Magenta