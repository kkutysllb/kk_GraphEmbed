# kk_GraphEmbed
一个用于5GC资源图谱的图嵌入模型设计

## 项目概述

本项目旨在构建5G核心网资源图谱，通过图嵌入技术对网络资源进行建模、分析和优化。项目将原始的数据中心资源拓扑信息转换为图数据结构，并应用图嵌入算法进行表示学习，支持资源管理、故障分析和容量规划等应用场景。

## 项目结构

```
kk_GraphEmbed/
├── data_preprocessing/     # 数据预处理代码
│   └── excel_to_gaph_json.py  # Excel转图数据JSON工具
├── datasets/               # 数据集目录
│   ├── raw/                # 原始数据
│   │   └── xbxa_dc4_topology.xlsx  # 原始拓扑数据
│   └── processed/          # 处理后的数据
│       └── topology_graph.json  # 处理后的图数据
├── docs/                   # 文档目录
│   └── data_preprocessing_design.md  # 数据预处理设计文档
└── README.md               # 项目说明文件
```

## 项目进展

1. **数据预处理（已完成）**
   - 设计并实现了从Excel表格到图数据结构的转换流程
   - 建立了包含7个层级的资源拓扑模型
   - 实现了节点和边的中文属性增强
   - 完成了资源配额属性的映射和处理

2. **图结构设计（已完成）**
   - 设计了层次化节点类型体系
   - 定义了各类资源间的关系边类型
   - 实现了节点和边的去重和属性处理

3. **后续规划**
   - 数据可视化：开发基于图数据的可视化界面
   - 图嵌入模型：实现节点和边的向量表示
   - 资源分析：开发基于图的资源使用和故障分析算法
   - 应用集成：设计API接口，支持与资源管理系统集成

## 使用说明

### 数据预处理

将原始Excel拓扑数据转换为图数据结构：

```bash
cd data_preprocessing
python excel_to_gaph_json.py
```

生成的图数据将保存在`datasets/processed/topology_graph.json`。

## 文档

- [数据预处理设计文档](docs/data_preprocessing_design.md) - 详细描述了数据预处理的设计思路和实现方法
