# 数据中心资源拓扑图构建设计文档

## 1. 项目概述

### 1.1 项目背景

本项目旨在将数据中心资源拓扑信息从原始Excel表格转换为图数据结构，以支持更高效的资源管理、故障分析和容量规划。通过建立各种资源实体（如租户、网元、虚拟机等）之间的关系图，可以提供更直观的资源视图和更深入的分析能力。

### 1.2 项目目标

1. 设计并实现从Excel表格到图数据结构的转换流程
2. 确保转换后的图数据能准确表达资源间的层级关系
3. 优化节点和边的属性设计，提高数据可用性和可理解性
4. 支持多语言（中英文）环境下的资源描述和展示

## 2. 数据预处理设计

### 2.1 原始数据分析

原始数据存储在`xbxa_dc4_topology.xlsx`文件中，包含了数据中心各类资源的详细信息和关联关系：

- **资源类型**：数据中心、租户、网元、虚拟机、主机、主机组、存储池
- **属性信息**：名称、配额（CPU、内存、存储等）
- **关联关系**：多对多和一对多关系（如租户与网元、网元与虚拟机等）

### 2.2 图模型设计

#### 2.2.1 节点设计

节点代表资源实体，设计为七个层级：

| 层级 | 节点类型 | ID格式 | 中文名称 | 描述 |
|------|---------|-------|---------|------|
| 0 | DC | `DC_XBXA_DC4` | 数据中心 | 物理数据中心，是所有IT资源的顶层容器 |
| 1 | TENANT | `TENANT_{名称}` | 租户 | 数据中心中的逻辑隔离单元，拥有独立的资源配额和网络元素 |
| 2 | NE | `NE_{名称}` | 网元 | 网络功能虚拟化(NFV)部署的功能单元，如AMF、SMF等5G核心网功能 |
| 3 | VM | `VM_{名称}` | 虚拟机 | 承载网元功能的虚拟计算资源，由虚拟CPU、内存和存储组成 |
| 4 | HOST | `HOST_{名称}` | 物理主机 | 提供计算资源的物理服务器，用于运行虚拟机 |
| 5 | HOSTGROUP | `HOSTGROUP_{名称}` | 主机组 | 物理主机的逻辑分组，通常基于硬件配置、位置或用途进行分组 |
| 6 | STORAGEPOOL/TRU | `STORAGEPOOL_{名称}` | 存储池 | 提供持久化存储资源的逻辑单元，为虚拟机提供存储空间 |

#### 2.2.2 边关系设计

边表示资源间的关系，设计了六种关系类型：

| 边类型 | 中文名称 | 方向 | 描述 |
|--------|---------|------|------|
| HAS_TENANT | 拥有租户 | DC → TENANT | 表示数据中心拥有或管理某个租户，这是资源分配的第一层级关系 |
| HAS_NE | 拥有网元 | TENANT → NE | 表示某个租户拥有或管理特定的网络元素 |
| HAS_VM | 拥有虚拟机 | NE → VM | 表示网络元素通过一个或多个虚拟机来实现其功能 |
| DEPLOYED_ON | 部署于 | VM → HOST | 表示虚拟机部署或运行在特定的物理主机上 |
| BELONGS_TO | 属于 | HOST → HOSTGROUP | 表示物理主机属于特定的主机组集合 |
| HAS_STORAGE | 拥有存储 | HOSTGROUP → STORAGEPOOL | 表示主机组关联或使用特定的存储池资源 |

### 2.3 预处理算法设计

#### 2.3.1 转换流程

1. 加载Excel数据文件
2. 创建数据中心根节点
3. 按层级依次处理各类资源节点
4. 建立节点间的关系边
5. 保存为JSON格式的图数据结构

#### 2.3.2 去重策略

- 使用集合(`Set`)存储已处理的节点ID，避免重复创建节点
- 使用`source-target-type`格式的复合键唯一标识边，避免重复创建边
- 为多对多关系中的每对关系创建唯一的边

#### 2.3.3 属性处理

- 保留原始数据中的资源配额信息
- 统一处理缺失值，设定默认值为0
- 为节点和边添加中文名称和描述信息
- 为节点添加层级属性，便于层次化分析

## 3. 实现细节

### 3.1 代码结构

主要实现文件位于`data_preprocessing/excel_to_gaph_json.py`，实现了`TopologyConverter`类来处理转换逻辑：

```python
class TopologyConverter:
    def __init__(self, excel_path):
        # 初始化数据结构和配置
        # 定义节点层级和描述
        # 定义边类型描述
        
    def load_data(self):
        # 加载Excel数据
        
    def create_dc_node(self):
        # 创建数据中心根节点
        
    def process_tenant_node(self, row):
        # 处理租户节点
        
    def process_ne_node(self, row):
        # 处理网元节点
        
    def process_vm_node(self, row):
        # 处理虚拟机节点
        
    def process_host_node(self, row):
        # 处理主机节点
        
    def process_hostgroup_node(self, row):
        # 处理主机组节点
        
    def process_storagepool_node(self, row):
        # 处理存储池节点
        
    def extract_node_type(self, name, base_type):
        # 提取节点类型
        
    def save_to_json(self, output_path):
        # 保存为JSON文件
        
    def run(self):
        # 执行转换流程
```

### 3.2 关键实现要点

1. **节点ID和类型设计**：
   - 使用前缀+名称的格式统一节点ID，确保唯一性
   - 节点类型反映资源类别，便于分类和查询

2. **边关系处理**：
   - 只建立Excel中存在的关系，严格遵循原始数据
   - 通过复合键识别边唯一性，避免重复

3. **属性增强**：
   - 为节点和边添加中英文名称和描述
   - 保留所有原始配额属性值

4. **数据完整性**：
   - 处理缺失值，确保数据一致性
   - 保持原始数据的业务逻辑关系

5. **执行流程**：
   ```python
   def run(self):
       """执行转换流程"""
       self.load_data()
       self.create_dc_node()
       
       # 按层级处理每一行数据
       for _, row in self.df.iterrows():
           self.process_tenant_node(row)
           self.process_ne_node(row)
           self.process_vm_node(row)
           self.process_host_node(row)
           self.process_hostgroup_node(row)
           self.process_storagepool_node(row)
       
       # 打印统计信息
       tenant_count = len(self.processed_nodes['tenant'])
       ne_count = len(self.processed_nodes['ne'])
       vm_count = len(self.processed_nodes['vm'])
       host_count = len(self.processed_nodes['host'])
       hostgroup_count = len(self.processed_nodes['hostgroup'])
       storagepool_count = len(self.processed_nodes['storagepool'])
       edge_count = len(self.processed_edges)
       
       print(f"共生成节点数量: {1 + tenant_count + ne_count + vm_count + host_count + hostgroup_count + storagepool_count}")
       print(f"  - 数据中心节点: 1")
       print(f"  - 租户节点: {tenant_count}")
       print(f"  - 网元节点: {ne_count}")
       print(f"  - 虚拟机节点: {vm_count}")
       print(f"  - 主机节点: {host_count}")
       print(f"  - 主机组节点: {hostgroup_count}")
       print(f"  - 存储池节点: {storagepool_count}")
       print(f"边关系数量: {edge_count}")
       
       # 保存到JSON文件
       self.save_to_json("datasets/processed/topology_graph.json")
       print("已保存图数据到 datasets/processed/topology_graph.json")
   ```

## 4. 结果分析

### 4.1 图数据结构

生成的JSON文件(`datasets/processed/topology_graph.json`)包含两个主要部分：
- `nodes`数组：包含所有节点信息
- `edges`数组：包含所有边关系信息

#### 节点示例：
```json
{
  "id": "DC_XBXA_DC4",
  "type": "DC",
  "level": 0,
  "properties": {
    "name": "XBXA_DC4",
    "chinese_name": "数据中心",
    "description": "物理数据中心，是所有IT资源的顶层容器"
  }
}
```

#### 边示例：
```json
{
  "source": "DC_XBXA_DC4",
  "target": "TENANT_NFV-P-XBXA-04A-HW-01-gs-B5G-HW",
  "type": "HAS_TENANT",
  "properties": {
    "name": "拥有租户",
    "description": "表示数据中心拥有或管理某个租户，这是资源分配的第一层级关系"
  }
}
```

### 4.2 数据质量分析

1. **完整性**：
   - 保留了原始Excel表格中的所有关键属性
   - 所有节点和关系都被正确转换

2. **结构清晰**：
   - 通过层级属性明确标识节点在资源层次中的位置
   - 节点之间的关系清晰，便于遍历和查询

3. **可用性提升**：
   - 添加了中文描述，提高了数据可理解性
   - 规范化的节点ID和类型便于查找和引用

4. **业务语义增强**：
   - 边和节点的描述反映了业务含义
   - 属性设计符合电信NFV领域的专业术语和概念

### 4.3 应用价值

1. **资源可视化**：
   - 直观展示数据中心资源拓扑结构
   - 支持按层级、类型等多维度展示

2. **资源分析**：
   - 分析各类资源的分配和使用情况
   - 识别资源过度分配或未充分利用的情况

3. **故障分析**：
   - 追踪故障在不同层级间的传播路径
   - 评估单点故障对整体系统的影响

4. **容量规划**：
   - 基于当前资源使用情况进行容量预测
   - 模拟不同资源配置对系统性能的影响

## 5. 后续工作

基于当前的数据预处理成果，后续工作将集中在以下几个方面：

1. **数据可视化**：
   - 开发基于图数据的可视化界面
   - 支持交互式导航和过滤

2. **数据分析**：
   - 实现资源使用分析算法
   - 开发故障影响分析模型

3. **图嵌入模型**：
   - 为节点和边开发向量表示
   - 实现图嵌入算法，支持相似度计算和推荐

4. **应用集成**：
   - 开发API接口，支持外部系统调用
   - 与资源管理系统集成 