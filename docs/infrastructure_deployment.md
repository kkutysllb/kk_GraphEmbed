# 动态图数据系统 - 基础设施部署指南

本文档详细记录GraphRAG统一查询层的基础设施部署过程，为项目团队成员提供指导。

## 基础设施概述

根据项目设计文档`dynamic_data_integration_design.md`，第一阶段需要部署以下基础组件：

1. **图数据库**：Neo4j 5.15
2. **时序数据库**：InfluxDB 2.0
3. **微软GraphRAG框架**

## 环境准备

### 先决条件

- Docker (版本 19.03+)
- Python (版本 3.10+)
- Conda (用于环境管理)
- Git

### Python环境设置

使用项目的Conda环境：

```bash
# 激活项目环境
conda activate kk_GraphEmbed

# 验证Python版本
python --version  # 应为3.10+
```

## 1. 部署Neo4j图数据库

我们使用Docker部署Neo4j 5.15版本。为避免与现有Neo4j实例冲突，使用不同的端口：

```bash
# 创建数据目录
mkdir -p $HOME/graphrag_neo4j/{data,logs,import,plugins}

# 部署Neo4j容器
docker run --name graphrag_neo4j \
    -p 7475:7474 -p 7688:7687 \
    -e NEO4J_AUTH=neo4j/graphrag_password \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    -v $HOME/graphrag_neo4j/data:/data \
    -v $HOME/graphrag_neo4j/logs:/logs \
    -v $HOME/graphrag_neo4j/import:/import \
    -v $HOME/graphrag_neo4j/plugins:/plugins \
    --restart always \
    -d neo4j:5.15.0
```

**端口说明**：
- Neo4j浏览器界面: http://localhost:7475
- Neo4j Bolt连接: bolt://localhost:7688

**凭据**：
- 用户名: neo4j
- 密码: graphrag_password

## 2. 部署InfluxDB时序数据库

使用Docker部署InfluxDB 2.0：

```bash
# 创建数据目录
mkdir -p $HOME/graphrag_influxdb

# 部署InfluxDB容器
docker run --name graphrag_influxdb \
    -p 8087:8086 \
    -v $HOME/graphrag_influxdb:/var/lib/influxdb2 \
    -e DOCKER_INFLUXDB_INIT_MODE=setup \
    -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
    -e DOCKER_INFLUXDB_INIT_PASSWORD=graphrag_password \
    -e DOCKER_INFLUXDB_INIT_ORG=graphrag_org \
    -e DOCKER_INFLUXDB_INIT_BUCKET=metrics \
    -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=graphrag_token \
    --restart always \
    -d influxdb:2.0
```

**访问信息**：
- InfluxDB界面: http://localhost:8087
- 组织: graphrag_org
- 存储桶: metrics
- API令牌: graphrag_token

## 3. 安装微软GraphRAG框架

```bash
# 克隆GraphRAG仓库
git clone --depth=1 https://github.com/microsoft/graphrag.git

# 安装Python依赖
pip install neo4j influxdb-client

# 安装GraphRAG
cd graphrag
pip install -e .
```

## 4. 项目配置

配置文件位置: `dynamic_graph_rag/config/settings.py`

此文件包含图数据库和时序数据库的连接信息以及节点类型配置。主要配置包括：

```python
# Neo4j配置
NEO4J_CONFIG = {
    "development": {
        "uri": "bolt://localhost:7688",
        "user": "neo4j",
        "password": "graphrag_password",
        "database": "neo4j"
    },
    ...
}

# InfluxDB配置
INFLUXDB_CONFIG = {
    "development": {
        "url": "http://localhost:8087",
        "token": "graphrag_token",
        "org": "graphrag_org",
        "bucket": "metrics"
    },
    ...
}

# 节点类型配置
NODE_TYPES = {
    "VM": {
        "metrics": ["cpu_usage", "memory_usage", "disk_io", "network_throughput"],
        "measurement": "vm_metrics",
        "default_sampling_interval": "1m",
        "retention_period": "30d"
    },
    ...
}
```

## 5. 连接测试

项目包含一个连接测试脚本，用于验证图数据库和时序数据库的连接：

```bash
# 运行连接测试
cd ~/kk_Projects/kk_GraphEmbed
python -m dynamic_graph_rag.tests.connection_test
```

测试脚本会：
1. 连接到Neo4j并执行简单查询
2. 连接到InfluxDB，创建测试数据点并查询
3. 输出连接状态和测试结果

如果测试成功，您将看到类似以下的输出：
```
INFO - Neo4j连接测试: 成功
INFO - InfluxDB连接测试: 成功
INFO - 所有连接测试通过!
```

## 6. 时序数据模型设计

根据项目设计，我们为不同类型的节点定义了时序数据模型，包含以下关键元素：

1. **节点类型**：VM、HOST、NE、STORAGEPOOL、HOSTGROUP
2. **度量指标**：每种节点类型的关键性能指标
3. **采样间隔**：数据收集频率
4. **保留策略**：数据保留时间

详细配置可参考`dynamic_graph_rag/config/settings.py`中的`NODE_TYPES`定义。

## 7. 数据导入准备

在第二阶段，我们将导入图数据和时序数据。目前，您需要准备：

1. 图数据导入脚本（项目规划中）
2. 时序数据采集脚本（项目规划中）

## 注意事项与故障排除

### 常见问题解决方案

1. **Neo4j连接失败**
   - 检查容器是否正在运行：`docker ps | grep graphrag_neo4j`
   - 检查端口是否正确：7688而非默认的7687
   - 检查防火墙设置

2. **InfluxDB连接失败**
   - 检查容器状态：`docker ps | grep graphrag_influxdb`
   - 验证访问令牌是否正确
   - 检查bucket是否存在：通过UI界面或API确认

### 安全提示

- 生产环境部署时，应更改默认密码和令牌
- 考虑使用环境变量而非硬编码的密码
- 限制数据库端口的外部访问

## 下一步

完成基础设施部署后，项目将进入第二阶段：
1. 生成模拟时序数据
2. 导入现有图数据
3. 开发简单集成层

团队成员应确保基础设施正常运行，然后才能进行后续开发工作。 