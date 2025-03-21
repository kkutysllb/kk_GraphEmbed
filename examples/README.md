# GraphRAG 示例脚本

本目录包含多个示例脚本，用于演示 GraphRAG 适配器的各种功能和用法。

## 示例脚本清单

### LLM 模型测试
- `test_lmstudio.py`: 测试 LM Studio 模型集成
- `test_vllm.py`: 测试 vLLM 模型集成
- `test_ollama.py`: 测试 Ollama 模型集成

### GraphRAG 功能测试
- `graphrag_demo.py`: GraphRAG 基本功能演示
- `test_graph_rag_adapter.py`: 测试 GraphRAG 适配器的各种查询功能
- `test_stream_query.py`: 测试 GraphRAG 适配器的流式响应功能

## 使用方法

### 环境配置

在运行示例前，请确保已正确配置环境变量或`config/settings.py`中的配置项：
- LM Studio、vLLM 或 Ollama 服务已启动
- Neo4j 和 InfluxDB 服务已启动并正确配置

### 运行示例

```bash
# 测试 LM Studio 模型
python examples/test_lmstudio.py

# 测试 vLLM 模型
python examples/test_vllm.py

# 测试 Ollama 模型
python examples/test_ollama.py

# GraphRAG 适配器功能演示
python examples/graphrag_demo.py

# 测试 GraphRAG 适配器的查询功能
python examples/test_graph_rag_adapter.py

# 测试流式响应功能
python examples/test_stream_query.py
```

## 示例说明

### test_graph_rag_adapter.py

这个脚本演示了如何使用 GraphRAG 适配器执行不同类型的查询：
- 图数据查询：使用 Cypher 查询 Neo4j 图数据库
- 时序数据查询：查询 InfluxDB 中的时序数据
- 混合查询：同时查询图数据和时序数据
- 自然语言查询：将自然语言转换为结构化查询并执行

### test_stream_query.py

这个脚本演示了如何使用 GraphRAG 适配器的流式响应功能：
- 简单流式响应：直接流式输出 LLM 生成的内容
- 基于上下文的流式响应：先获取数据作为上下文，然后流式生成回答

## 自定义测试

您可以参考这些示例脚本来创建自己的测试场景。这些示例展示了：
- 如何初始化 GraphRAG 适配器
- 如何执行不同类型的查询
- 如何处理查询结果
- 如何使用流式响应功能 