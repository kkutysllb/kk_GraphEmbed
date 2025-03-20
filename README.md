# GraphRAG统一查询层项目

本项目实现了一个基于图数据和时序数据的统一查询层，结合Microsoft GraphRAG框架，用于复杂系统的数据分析、故障诊断和智能查询。

## 项目概述

GraphRAG统一查询层将图数据库（Neo4j）和时序数据库（InfluxDB）结合起来，为复杂系统提供全面的查询和分析能力。项目通过以下关键组件实现：

1. **图数据存储**：使用Neo4j存储网络拓扑结构，包括节点和关系
2. **时序数据存储**：使用InfluxDB存储性能指标和监控数据
3. **GraphRAG集成**：利用Microsoft GraphRAG框架实现自然语言查询
4. **混合查询引擎**：支持同时查询图数据和时序数据
5. **故障分析模块**：基于图结构和时序数据分析故障传播

## 项目结构

```
dynamic_graph_rag/
├── config/               # 配置文件
├── data/                 # 数据文件
│   ├── raw/              # 原始数据
│   ├── processed/        # 处理后的数据
│   └── simulated/        # 模拟数据
├── data_import/          # 数据导入模块
├── db/                   # 数据库连接模块
├── models/               # 数据模型
├── tests/                # 测试脚本
└── utils/                # 工具函数
```

## 文档索引

- [基础设施部署指南](docs/infrastructure_deployment.md)
- [时序数据模型设计](docs/time_series_data_model.md)
- [图数据导入指南](docs/graph_data_import_guide.md)
- [项目状态更新](docs/project_status_update.md)

## 快速开始

### 1. 准备环境

确保您已安装以下依赖：
- Docker
- Python 3.10+
- Conda (可选，用于环境管理)
- Poetry (可选，用于依赖管理)

### 2. 克隆仓库

```bash
git clone https://github.com/yourusername/dynamic_graph_rag.git
cd dynamic_graph_rag
```

### 3. 设置Python环境

#### 使用pip

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 使用Conda

```bash
# 创建Conda环境
conda create -n graphrag python=3.10
conda activate graphrag

# 安装依赖
pip install -r requirements.txt
```

#### 使用Poetry

```bash
# 安装项目依赖
poetry install

# 启动Poetry shell
poetry shell
```

### 4. 部署基础设施

按照[基础设施部署指南](docs/infrastructure_deployment.md)部署Neo4j和InfluxDB。

### 5. 运行连接测试

```bash
python -m dynamic_graph_rag.tests.connection_test
```

### 6. 导入图数据

按照[图数据导入指南](docs/graph_data_import_guide.md)将图数据导入到Neo4j中。

```bash
cd dynamic_graph_rag
python data_import/run_graph_import.py --input data/raw/sample_topology.json --clear
```

## 项目阶段

1. **阶段1**: 基础架构建立 ✅
   - 建立项目结构和配置
   - 部署Neo4j图数据库
   - 部署InfluxDB时序数据库
   - 配置GraphRAG框架

2. **阶段2**: 数据导入 ✅
   - 设计图数据结构和导入流程
   - 实现图数据导入工具
   - 测试图数据完整性
   - 参考[图数据导入指南](docs/graph_data_import_guide.md)

3. **阶段3**: 时序数据生成与导入 ✅
   - 设计时序数据模型
   - 实现时序数据生成器
   - 将生成的数据导入InfluxDB
   - 验证时序数据的可查询性
   - 参考[时序数据模型设计](docs/time_series_data_model.md)

4. **阶段4**: 统一查询层开发 🔄
   - 设计GraphRAG查询接口
   - 实现图数据查询功能
   - 实现时序数据查询功能
   - 开发混合查询能力
   - 完成API文档

## 项目开发路线图

本项目将分四个阶段开发：

1. **阶段1**：基础架构建立（已完成）
   - 部署基础组件
   - 设计时序数据模型
   - 创建项目依赖和安装脚本

2. **阶段2**：数据导入和生成（进行中）
   - 导入现有图数据（已完成）
   - 生成模拟时序数据
   - 导入时序数据

3. **阶段3**：扩展GraphRAG能力
   - 增强查询解析
   - 开发混合查询转换器
   - 构建上下文生成器

4. **阶段4**：故障分析功能实现
   - 开发故障检测模块
   - 实现故障传播分析
   - 构建诊断推理能力

## 依赖管理

项目使用以下关键依赖：

- **核心组件**
  - neo4j==5.15.0
  - influxdb-client==1.36.1
  - graphrag==0.1.0

- **数据处理**
  - pandas, numpy, scipy

- **Web API** (可选)
  - fastapi, uvicorn

完整依赖列表请参见`requirements.txt`或`pyproject.toml`。

## 许可证

[MIT License](LICENSE)
