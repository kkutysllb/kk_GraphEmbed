# GraphRAG统一查询层

## 项目概述
本项目旨在实现一个动态数据集成系统，支持图数据和时序数据的实时集成与查询。系统基于微软开源的 GraphRAG 框架，扩展其功能以支持时序数据，并实现动态数据集成。

## 系统架构
系统主要包含以下组件：
1. 数据源适配器
   - Neo4j 适配器：处理图数据
   - InfluxDB 适配器：处理时序数据
2. LLM 接口
   - vLLM 接口：支持本地部署的大模型
   - Ollama 接口：支持本地部署的模型
3. GraphRAG 适配器
   - 继承 GraphRAG 框架的核心功能
   - 扩展支持时序数据
   - 实现动态数据集成

## 开发进度

### 第一阶段：基础功能实现 ✅
1. 数据源适配器
   - [x] Neo4j 适配器实现
   - [x] InfluxDB 适配器实现
   - [x] 基础查询功能
   - [x] 数据同步机制

2. LLM 接口
   - [x] vLLM 接口实现
   - [x] Ollama 接口实现
   - [x] 基础文本生成功能
   - [x] 系统提示词支持

### 第二阶段：GraphRAG 集成 🔄
1. GraphRAG 框架集成
   - [x] 核心文件恢复
   - [x] 基础功能验证
   - [ ] GraphRAGAdapter 实现
   - [ ] 动态数据集成
   - [ ] 时序数据支持

2. 查询处理
   - [ ] 查询意图识别
   - [ ] 查询类型分类
   - [ ] 查询参数提取
   - [ ] 结果优化

### 第三阶段：系统优化
1. 性能优化
   - [ ] 缓存机制
   - [ ] 并发处理
   - [ ] 资源管理

2. 可用性优化
   - [ ] 错误处理
   - [ ] 日志记录
   - [ ] 监控告警

## 下一步计划
1. 实现 GraphRAGAdapter 类
   - 继承 GraphRAG 框架的核心功能
   - 扩展支持时序数据
   - 实现动态数据集成

2. 实现 DynamicDataIntegrator 类
   - 实现数据源管理
   - 实现数据同步
   - 实现数据更新

3. 实现 QueryProcessor 类
   - 利用 GraphRAG 的查询处理能力
   - 扩展支持时序查询
   - 实现查询优化

## 技术栈
- Python 3.8+
- Neo4j
- InfluxDB
- vLLM
- Ollama
- GraphRAG 框架

## 环境配置
1. 数据源配置
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   INFLUXDB_URL=http://localhost:8086
   INFLUXDB_TOKEN=your-token
   INFLUXDB_ORG=your-org
   INFLUXDB_BUCKET=your-bucket
   ```

2. LLM 配置
   ```env
   # vLLM 配置
   VLLM_API_URL=http://localhost:8000
   VLLM_MODEL_NAME=/path/to/model
   VLLM_TEMPERATURE=0.7
   VLLM_MAX_TOKENS=2048

   # Ollama 配置
   OLLAMA_API_BASE=http://localhost:11434
   OLLAMA_MODEL_NAME=deepseek-r1:32b
   ```

## 使用说明
1. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入必要的配置信息
   ```

3. 启动服务
   ```bash
   # 启动 vLLM 服务
   ./scripts/start_vllm.sh

   # 启动示例程序
   python examples/graphrag_demo.py
   ```

## 注意事项
1. 确保所有依赖服务（Neo4j、InfluxDB、vLLM、Ollama）都已正确启动
2. 检查环境变量配置是否正确
3. 确保有足够的系统资源（内存、GPU等）

## 贡献指南
1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证
MIT License
