#!/bin/zsh
set -e

echo "\e[36mInitializing Aetherlink 4080 Super Environment (WSL Native)...\e[0m"

# 1. Sync dependencies with uv
echo "\e[36mSyncing project dependencies with uv...\e[0m"
uv sync --group dev --group automation

# 2. Check if llama-server is already active
if ! lsof -i :8080 > /dev/null; then
    echo "\e[36mStarting llama.cpp Engine (RTX 4080 Super + Speculative Decoding)...\e[0m"

    # Native WSL paths to your tools and Windows-hosted models
    LLAMA_BIN="$HOME/Projects/ai-tools/llama.cpp/build/bin/llama-server"
    MAIN_MODEL="/mnt/c/Users/Dada/.lmstudio/models/lmstudio-community/Qwen2.5-Coder-14B-Instruct-GGUF/Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"
    DRAFT_MODEL="/mnt/c/Users/Dada/.lmstudio/models/lmstudio-community/Qwen2.5-Coder-0.5B-Instruct-GGUF/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf"

    # Launch llama-server in the background with the WSL Bridge fix
    LD_PRELOAD=/usr/lib/wsl/drivers/nv_dispi.inf_amd64_adc55ecfca814224/libnvidia-ptxjitcompiler.so.1 \
    $LLAMA_BIN \
        --model "$MAIN_MODEL" \
        --model-draft "$DRAFT_MODEL" \
        --n-gpu-layers 99 \
        --n-gpu-layers-draft 99 \
        --flash-attn \
        --port 8080 > llama_server.log 2>&1 &

    echo "\e[33mWaiting for llama-server to initialize...\e[0m"
    
    # Health check loop (Max 60s)
    for i in {1..30}; do
        sleep 2
        if curl -s -f "http://127.0.0.1:8080/health" > /dev/null; then
            echo "\e[32mllama-server is ready on port 8080.\e[0m"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "\e[31mERROR: llama-server did not respond within 60s. Check llama_server.log\e[0m"
            exit 1
        fi
    done
else
    echo "\e[32mllama-server already active on port 8080.\e[0m"
fi