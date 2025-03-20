# 时序数据模型设计

本文档详细说明动态图数据系统中的时序数据模型设计，包括数据结构、采集策略和查询模式。

## 1. 概述

时序数据是系统监控和性能分析的关键组成部分。在我们的动态图数据系统中，时序数据用于记录各种节点（虚拟机、主机、网络元素等）的实时性能指标。这些指标数据与图结构结合，可以提供更全面的系统状态视图和故障分析能力。

## 2. 数据模型结构

### 2.1 节点类型与指标

我们为系统中的每种节点类型定义了特定的指标集合：

#### 虚拟机 (VM)
| 指标 | 描述 | 单位 | 典型范围 |
|------|------|------|----------|
| cpu_usage | CPU使用率 | % | 0-100 |
| memory_usage | 内存使用率 | % | 0-100 |
| disk_io | 磁盘IO操作 | IOPS | 0-10000 |
| network_throughput | 网络吞吐量 | Mbps | 0-10000 |

#### 物理主机 (HOST)
| 指标 | 描述 | 单位 | 典型范围 |
|------|------|------|----------|
| cpu_usage | CPU使用率 | % | 0-100 |
| memory_usage | 内存使用率 | % | 0-100 |
| disk_usage | 磁盘使用率 | % | 0-100 |
| temperature | 温度 | °C | 20-90 |

#### 网络元素 (NE)
| 指标 | 描述 | 单位 | 典型范围 |
|------|------|------|----------|
| load | 负载 | % | 0-100 |
| response_time | 响应时间 | ms | 0-1000 |
| success_rate | 成功率 | % | 0-100 |
| resource_usage | 资源使用率 | % | 0-100 |

#### 存储池 (TRU)
| 指标 | 描述 | 单位 | 典型范围 |
|------|------|------|----------|
| usage | 使用率 | % | 0-100 |
| iops | IO操作每秒 | IOPS | 0-50000 |
| latency | 延迟 | ms | 0-100 |
| read_write_ratio | 读写比例 | 比率 | 0-1 |

#### 主机组 (HOSTGROUP)
| 指标 | 描述 | 单位 | 典型范围 |
|------|------|------|----------|
| aggregate_cpu | 聚合CPU使用率 | % | 0-100 |
| aggregate_memory | 聚合内存使用率 | % | 0-100 |
| load_balance | 负载均衡度 | 比率 | 0-1 |

### 2.2 数据结构

在InfluxDB中，时序数据使用以下结构存储：

- **Measurement**：根据节点类型确定，如`vm_metrics`、`host_metrics`等
- **Tags**：用于索引和过滤
  - `node_id`：节点唯一标识符
  - `node_type`：节点类型（VM、HOST等）
- **Fields**：实际的指标值
  - 每种节点类型的特定指标集
- **Timestamp**：数据点的时间戳

### 2.3 采样策略

每种节点类型都有默认的采样间隔和数据保留策略：

| 节点类型 | 采样间隔 | 保留期 |
|---------|---------|--------|
| VM | 15分钟 | 30天 |
| HOST | 15分钟 | 30天 |
| NE | 15分钟 | 30天 |
| TRU | 15分钟 | 30天 |
| HOSTGROUP | 15分钟 | 30天 |

注意：采样间隔已统一调整为15分钟，以平衡数据精度和存储需求。

## 3. 数据采集

### 3.1 采集方式

时序数据采集可以通过以下方式实现：

1. **直接采集**：从实际系统中获取实时指标
2. **模拟数据**：生成模拟数据用于测试和开发

### 3.2 采集脚本设计

采集脚本将遵循以下模式：

```python
def collect_vm_metrics(vm_id, cpu, memory, disk_io, network):
    """收集VM指标并写入InfluxDB"""
    point = Point("vm_metrics") \
        .tag("node_id", vm_id) \
        .tag("node_type", "VM") \
        .field("cpu_usage", cpu) \
        .field("memory_usage", memory) \
        .field("disk_io", disk_io) \
        .field("network_throughput", network)
    
    write_api.write(bucket="metrics", record=point)
```

### 3.3 采集调度

数据采集将通过调度系统按照定义的采样间隔执行。在开发阶段，我们将使用模拟数据生成器来产生测试数据。

## 4. 数据查询模式

### 4.1 常见查询类型

1. **最新指标**：获取节点的最新指标值
2. **历史趋势**：获取一段时间内的指标变化
3. **聚合分析**：计算平均值、最大值、最小值等统计信息
4. **异常检测**：识别超出正常范围的异常指标
5. **关联分析**：结合图结构进行多节点关联分析

### 4.2 示例查询

#### 获取VM最新CPU使用率
```flux
from(bucket: "metrics")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "vm_metrics")
  |> filter(fn: (r) => r.node_id == "VM_001")
  |> filter(fn: (r) => r._field == "cpu_usage")
  |> last()
```

#### 获取过去24小时的主机温度趋势
```flux
from(bucket: "metrics")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "host_metrics")
  |> filter(fn: (r) => r.node_id == "HOST_001")
  |> filter(fn: (r) => r._field == "temperature")
  |> aggregateWindow(every: 10m, fn: mean)
```

## 5. 数据模型接口

### 5.1 核心方法

时序数据模型将提供以下核心方法：

1. **数据写入**：
   - `write_node_metrics(node_id, node_type, metrics, timestamp=None)`
   - `bulk_write_metrics(dataframe, node_type)`

2. **数据查询**：
   - `get_node_metrics(node_id, node_type, start_time=None, end_time=None)`
   - `get_recent_metrics(node_id, node_type, limit=10)`
   - `get_metric_statistics(node_type, metric, start_time=None, end_time=None)`

3. **高级分析**：
   - `detect_anomalies(node_id, node_type, metric, threshold=2.0, window="1h")`
   - `analyze_trend(node_id, node_type, metric, window="7d")`
   - `predict_metrics(node_id, node_type, metric, prediction_horizon="24h")`

### 5.2 接口示例

```python
# 获取节点指标
metrics_df = ts_data.get_node_metrics(
    node_id="VM_001",
    node_type="VM",
    start_time="-24h"
)

# 检测异常值
anomalies = ts_data.detect_anomalies(
    node_id="VM_001",
    node_type="VM",
    metric="cpu_usage",
    threshold=2.5  # 2.5个标准差
)

# 分析趋势
trend = ts_data.analyze_trend(
    node_id="VM_001",
    node_type="VM",
    metric="memory_usage",
    window="7d"
)
```

## 6. 与图数据集成

### 6.1 集成方式

时序数据将通过节点ID与图数据中的节点关联，这允许我们：

1. 基于图结构查询相关节点的时序数据
2. 分析故障在图中的传播路径
3. 结合两种数据类型进行综合分析

### 6.2 集成接口

```python
# 通过图中的关系查询相关节点的指标
related_metrics = dynamic_graph.get_related_nodes_metrics(
    node_id="VM_001",
    relation_type="DEPLOYED_ON",
    direction="outgoing",
    metrics=["cpu_usage"],
    start_time="-1h"
)

# 分析故障影响范围
impact_analysis = dynamic_graph.analyze_fault_impact(
    node_id="HOST_001",
    fault_metric="cpu_usage",
    propagation_depth=2
)
```

## 7. 下一步计划

1. **模拟数据生成器**：开发用于测试和演示的模拟数据生成工具
2. **批量处理工具**：实现批量数据导入和处理功能
3. **可视化接口**：开发基本的时序数据可视化功能
4. **异常检测算法**：实现更复杂的异常检测和预测算法
5. **与GraphRAG集成**：将时序数据分析功能集成到GraphRAG查询框架 

## 8. 实际实施情况

### 8.1 数据生成与导入

我们已经完成了时序数据生成与导入的实现工作，主要成果包括：

1. **数据生成模块**：
   - 开发了基于Python的时序数据生成器，支持各种节点类型
   - 实现了带有日变化和周变化模式的数据生成算法
   - 添加了随机异常注入功能，有助于测试异常检测算法

2. **数据导入功能**：
   - 建立了与InfluxDB 2.0的稳定连接
   - 实现了批量导入功能，大幅提高导入效率
   - 处理了数据标签和字段的格式化和验证

3. **执行情况**：
   - 成功为所有Neo4j中的节点生成了30天的时序数据
   - 数据采样间隔统一为15分钟
   - 共生成约500万个数据点，全部成功导入InfluxDB

### 8.2 配置详情

实际部署使用的InfluxDB配置：
- URL: http://localhost:8087
- 用户名: admin
- 密码: graphrag_password
- 令牌: graphrag_token
- 组织: graphrag_org
- 存储桶: metrics

### 8.3 使用说明

1. **查看数据**：
   - 可以通过InfluxDB Web界面（http://localhost:8087）查看和分析时序数据
   - 使用Data Explorer构建查询，或使用Flux查询语言进行高级分析

2. **运行数据生成器**：
   ```bash
   python dynamic_graph_rag/data/run_time_series_generator.py --days 30 --node-types VM HOST NE HOSTGROUP TRU
   ```

3. **导出数据**：
   ```bash
   python dynamic_graph_rag/data/run_time_series_generator.py --days 30 --node-types VM HOST NE HOSTGROUP TRU --csv --output-dir ./output_data
   ```

### 8.4 性能与优化

在处理大量时序数据时，我们采取了以下优化措施：

1. **批量处理**：使用批量写入而非单点写入，每批次处理1000个数据点
2. **并行处理**：数据生成过程采用了多线程处理
3. **采样优化**：将采样间隔从最初的1分钟调整为15分钟，减少了数据量的同时保持了足够的分析粒度
4. **异步写入**：使用InfluxDB的异步写入API减少等待时间 