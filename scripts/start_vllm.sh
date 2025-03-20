#!/bin/bash

# 设置模型路径
MODEL_PATH="/home/libing/kk_LLMs/Qwen2.5-vl-7b"

# 启动vLLM服务
python -m vllm.entrypoints.openai.api_server \
    --model $MODEL_PATH \
    --host "0.0.0.0" \
    --port 8000 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9 \
    --max-num-batched-tokens 131072 \
    --max-model-len 128000 