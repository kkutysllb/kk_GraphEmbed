# LLM集成指南

## 支持的模型

目前系统支持以下LLM模型：

1. Qwen2.5-14b-instruct
   - 默认模型
   - 支持流式输出
   - 支持系统提示词
   - 支持上下文管理
   - 支持温度控制
   - 支持最大token限制

2. DeepSeek-R1-Distill-Qwen-32B
   - 支持流式输出
   - 支持系统提示词
   - 支持上下文管理
   - 支持温度控制
   - 支持最大token限制


## 推理引擎

### 1. LM Studio

#### 配置说明

```python
LMSTUDIO_CONFIG = {
    "base_url": "http://localhost:12343",  # LM Studio服务地址
    "model": "qwen2.5-14b-instruct",      # 默认模型
    "max_tokens": 2048,                    # 最大token数
    "temperature": 0.7,                    # 温度参数
    "top_p": 0.9,                          # top_p参数
    "timeout": 30000                       # 超时时间(ms)
}
```

#### 环境变量配置

```bash
export LMSTUDIO_BASE_URL="http://localhost:12343"
export LMSTUDIO_MODEL="qwen2.5-14b-instruct"
export LMSTUDIO_MAX_TOKENS="2048"
export LMSTUDIO_TEMPERATURE="0.7"
export LMSTUDIO_TOP_P="0.9"
export LMSTUDIO_TIMEOUT="30000"
```

### 2. Ollama

#### 配置说明

```python
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",  # Ollama服务地址
    "model": "qwen2.5-14b-instruct",      # 默认模型
    "max_tokens": 2048,                    # 最大token数
    "temperature": 0.7,                    # 温度参数
    "top_p": 0.9,                          # top_p参数
    "timeout": 30000                       # 超时时间(ms)
}
```

#### 环境变量配置

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen2.5-14b-instruct"
export OLLAMA_MAX_TOKENS="2048"
export OLLAMA_TEMPERATURE="0.7"
export OLLAMA_TOP_P="0.9"
export OLLAMA_TIMEOUT="30000"
```

### 3. vLLM

#### 配置说明

```python
VLLM_CONFIG = {
    "base_url": "http://localhost:8000",   # vLLM服务地址
    "model": "qwen2.5-14b-instruct",      # 默认模型
    "max_tokens": 2048,                    # 最大token数
    "temperature": 0.7,                    # 温度参数
    "top_p": 0.9,                          # top_p参数
    "timeout": 30000                       # 超时时间(ms)
}
```

#### 环境变量配置

```bash
export VLLM_BASE_URL="http://localhost:8000"
export VLLM_MODEL="qwen2.5-14b-instruct"
export VLLM_MAX_TOKENS="2048"
export VLLM_TEMPERATURE="0.7"
export VLLM_TOP_P="0.9"
export VLLM_TIMEOUT="30000"
```

## 使用示例

### 基本使用

```python
from dynamic_graph_rag.rag.graph_rag_adapter import GraphRAGAdapter

# 初始化适配器
adapter = GraphRAGAdapter(
    model_type="lmstudio",  # 可选: "lmstudio", "ollama", "vllm"
    model_name="qwen2.5-14b-instruct"  # 可选，默认使用qwen2.5-14b-instruct
)

# 处理查询
response = adapter.process_query(
    query="你的问题",
    system_prompt="系统提示词",  # 可选
    temperature=0.7             # 可选
)
```

### 流式输出

```python
# 使用流式输出
for chunk in adapter.process_query_stream(
    query="你的问题",
    system_prompt="系统提示词"
):
    print(chunk, end="", flush=True)
```

## 注意事项

1. 确保相应的推理引擎服务已启动并可访问
2. 默认使用qwen2.5-14b-instruct模型，如需使用其他模型请通过model_name参数指定
3. 系统提示词是可选的，但建议提供以提高回答质量
4. 温度参数控制输出的随机性，值越高随机性越大
5. 最大token数限制单次请求的最大输出长度 