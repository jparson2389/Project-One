$ErrorActionPreference = "Stop"

Write-Host "Initializing Aetherlink..." -ForegroundColor Cyan

uv sync --group dev --group automation

if (!(Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue)) {
    Write-Host "Starting llama-server (RTX 4080 Super + Speculative Decoding)..." -ForegroundColor Cyan

    $llamaExe  = "C:\Users\Dada\AI_Tools\llama.cpp\build\bin\Release\llama-server.exe"
    $mainModel = "C:\Users\Dada\.lmstudio\models\lmstudio-community\Qwen2.5-Coder-14B-Instruct-GGUF\Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"
    $draftModel = "C:\Users\Dada\.lmstudio\models\lmstudio-community\Qwen2.5-Coder-0.5B-Instruct-GGUF\Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf"

    $llamaArgs = @(
        "--model",              $mainModel,
        "--model-draft",        $draftModel,
        "--n-gpu-layers",       "99",
        "--n-gpu-layers-draft", "99",
        "--ctx-size",           "32768",
        "--flash-attn",         "on",
        "--parallel",           "1",
        "--draft",              "8",
        "--cache-type-k",       "q8_0",
        "--cache-type-v",       "q8_0",
        "--port",               "8080",
        "--host",               "127.0.0.1"
    )

    Start-Process $llamaExe -ArgumentList $llamaArgs -WindowStyle Normal

    Write-Host "Waiting for llama-server..." -ForegroundColor Yellow
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        try {
            if ((Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -ErrorAction Stop).StatusCode -eq 200) {
                $ready = $true; break
            }
        } catch {}
    }

    if ($ready) {
        Write-Host "llama-server ready on http://127.0.0.1:8080/v1" -ForegroundColor Green
    } else {
        Write-Host "ERROR: llama-server did not respond within 60s." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "llama-server already active on port 8080." -ForegroundColor Green
}