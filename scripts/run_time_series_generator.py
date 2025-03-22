#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
执行时序数据生成器的脚本
用于生成模拟时序数据并导入到InfluxDB
这是一个简单的包装脚本，调用time_series_generator模块
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# 直接从time_series_generator模块导入main函数
from dynamic_graph_rag.data.simulated.generators.time_series_generator import main

if __name__ == "__main__":
    # 直接调用TimeSeriesGenerator的main函数
    main()

"""
使用示例:

1. 生成最近3天的数据并导入到InfluxDB:
   python run_time_series_generator.py --days 3

2. 生成指定日期范围的数据:
   python run_time_series_generator.py --start-date 2025-01-01 --end-date 2025-01-07

3. 生成指定日期至今的数据:
   python run_time_series_generator.py --start-date 2025-01-01

4. 限制节点数量（用于测试）:
   python run_time_series_generator.py --max-nodes 5

5. 仅生成特定类型节点的数据:
   python run_time_series_generator.py --node-types VM HOST

6. 仅生成CSV数据文件，不导入InfluxDB（解决超时问题）:
   python run_time_series_generator.py --csv-only --output-dir ./output/timeseries_data
""" 