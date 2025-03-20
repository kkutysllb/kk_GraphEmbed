# 图数据导入指南

本文档提供了如何将JSON格式的图数据导入到Neo4j数据库的详细说明，包括准备数据、运行导入脚本以及验证导入结果。

## 1. 数据准备

导入脚本接受特定格式的JSON文件，包含`nodes`和`edges`两个主要部分。

### 1.1 JSON格式要求

```json
{
  "nodes": [
    {
      "id": "唯一标识符",
      "type": "节点类型",
      "name": "节点名称",
      "level": 层级数值,
      ...其他属性...
    },
    ...更多节点...
  ],
  "edges": [
    {
      "source": "源节点ID",
      "target": "目标节点ID",
      "type": "边类型",
      ...其他属性...
    },
    ...更多边...
  ]
}
```

### 1.2 节点类型

系统支持的节点类型包括：

- `DC`: 数据中心
- `TENANT`: 租户
- `NE`: 网元
- `VM`: 虚拟机
- `HOST`: 物理主机
- `HOSTGROUP`: 主机组
- `STORAGEPOOL`: 存储池

### 1.3 边类型

系统支持的边类型包括：

- `HAS_TENANT`: 拥有租户关系
- `HAS_NE`: 拥有网元关系
- `HAS_VM`: 拥有虚拟机关系
- `DEPLOYED_ON`: 部署于关系
- `BELONGS_TO`: 属于关系
- `HAS_STORAGE`: 拥有存储关系

### 1.4 示例数据

项目中已包含一个示例拓扑图数据文件：`dynamic_graph_rag/data/raw/sample_topology.json`，可以作为参考。

## 2. 运行导入脚本

### 2.1 确认环境设置

在运行导入脚本前，请确保：

1. 已正确设置Python环境（建议使用项目提供的环境设置脚本）
2. Neo4j数据库已启动并可访问
3. 配置文件中的Neo4j连接参数正确(`dynamic_graph_rag/config/settings.py`)

### 2.2 命令行选项

导入脚本支持以下命令行选项：

```
python data_import/run_graph_import.py [选项]
```

选项说明：

| 选项 | 短选项 | 必需 | 说明 |
|------|-------|-----|------|
| `--input` | `-i` | 是 | 输入JSON文件路径 |
| `--clear` | `-c` | 否 | 是否清空Neo4j数据库中的现有数据 |
| `--report` | `-r` | 否 | 导入报告输出路径（默认为输入文件同目录下的.report.md文件） |
| `--uri` | - | 否 | Neo4j数据库URI（默认使用配置文件中的值） |
| `--user` | - | 否 | Neo4j用户名（默认使用配置文件中的值） |
| `--password` | - | 否 | Neo4j密码（默认使用配置文件中的值） |
| `--database` | - | 否 | Neo4j数据库名（默认使用配置文件中的值） |

### 2.3 运行示例

导入示例拓扑图数据：

```bash
cd dynamic_graph_rag
python data_import/run_graph_import.py --input data/raw/sample_topology.json --clear
```

导入自定义数据并指定Neo4j连接参数：

```bash
cd dynamic_graph_rag
python data_import/run_graph_import.py \
  --input path/to/your/data.json \
  --uri bolt://localhost:7688 \
  --user neo4j \
  --password your_password \
  --report custom_report.md
```

## 3. 验证导入结果

### 3.1 导入报告

导入完成后，脚本会生成一个Markdown格式的导入报告，包含以下内容：

- 导入统计（节点和边的总数、成功导入数、错误数）
- 节点类型分布
- 边类型分布
- 数据完整性验证结果
- 导入结果摘要

### 3.2 使用Neo4j Browser验证

您也可以使用Neo4j Browser直接验证导入的数据：

1. 打开Neo4j Browser（通常是http://localhost:7475或http://localhost:7474）
2. 登录到Neo4j数据库
3. 运行以下查询验证数据导入结果：

```cypher
// 查看所有节点
MATCH (n:Node) RETURN n.id, n.type, n.name LIMIT 25;

// 按节点类型统计
MATCH (n:Node) RETURN n.type, count(*) AS count;

// 按边类型统计
MATCH ()-[r:RELATES]->() RETURN r.type, count(*) AS count;

// 查看完整的图
MATCH p=()-[r:RELATES]->() RETURN p LIMIT 100;
```

### 3.3 常见问题排查

如果导入过程中遇到问题，请检查：

1. **连接问题**：
   - Neo4j数据库是否正在运行
   - URI、用户名和密码是否正确
   - 网络连接是否通畅

2. **数据格式问题**：
   - JSON文件格式是否正确
   - 节点ID是否唯一
   - 边的source和target是否指向存在的节点

3. **权限问题**：
   - 用户是否有足够的权限执行写操作

## 4. 自定义导入脚本

如果您需要修改或扩展导入脚本以满足特定需求，请参考以下文件：

- `dynamic_graph_rag/data_import/graph_data_importer.py`: 包含导入逻辑的主类
- `dynamic_graph_rag/data_import/run_graph_import.py`: 命令行接口
- `dynamic_graph_rag/config/settings.py`: 配置参数

## 5. 后续步骤

成功导入图数据后，您可以：

1. 生成和导入时序数据
2. 开发图查询接口
3. 将Neo4j与InfluxDB集成，构建混合查询功能

有关更多信息，请参阅项目文档的其他部分。 