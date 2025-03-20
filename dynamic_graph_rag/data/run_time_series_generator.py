#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
执行时序数据生成器的脚本
用于生成模拟时序数据并导入到InfluxDB
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from dynamic_graph_rag.data.simulated.time_series_generator import TimeSeriesGenerator

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成并导入模拟时序数据')
    
    parser.add_argument('--days', type=int, default=30, help='生成多少天的数据')
    parser.add_argument('--csv', action='store_true', help='导出为CSV文件')
    parser.add_argument('--no-influxdb', action='store_true', help='不导入到InfluxDB')
    parser.add_argument('--output-dir', type=str, default='./output', help='CSV输出目录')
    parser.add_argument('--node-types', type=str, nargs='+', help='要生成数据的节点类型')
    parser.add_argument('--no-anomalies', action='store_true', help='不生成异常数据')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    print("\n===== 时序数据生成 =====")
    print("开始生成模拟时序数据并导入到InfluxDB...")
    
    # 设置时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.days)
    print(f"时间范围: {start_time} 到 {end_time}")
    
    if args.node_types:
        print(f"节点类型: {', '.join(args.node_types)}")
    else:
        print("节点类型: 全部可用类型")
    
    # 创建生成器实例
    generator = TimeSeriesGenerator()
    
    # 加载节点信息
    print("\n正在从Neo4j加载节点信息...")
    nodes = generator.load_nodes_from_neo4j(node_types=args.node_types)
    print(f"已加载 {len(nodes)} 个节点")
    
    # 运行生成过程
    print("\n正在生成时序数据...")
    result = generator.run(
        start_time=start_time,
        end_time=end_time,
        export_csv=args.csv,
        import_influxdb=not args.no_influxdb,
        output_dir=args.output_dir,
        include_anomalies=not args.no_anomalies
    )
    
    # 打印结果
    print("\n===== 时序数据生成结果 =====")
    print(f"状态: {result['status']}")
    print(f"节点数量: {result['node_count']}")
    print(f"指标类型数量: {result['metrics_count']}")
    print(f"数据点总数: {result['data_points']}")
    
    if 'csv_files' in result:
        print(f"CSV文件: {result['csv_files']['count']} 个文件已导出到 {result['csv_files']['directory']}")
        
    if 'influxdb_import' in result:
        print(f"InfluxDB导入: {result['influxdb_import']['count']} 个数据点")
        
    print("===========================\n")
    
    if result['status'] == 'success':
        print("时序数据生成完成!")
        
        # 提供查询InfluxDB的示例
        if 'influxdb_import' in result and result['influxdb_import']['success']:
            print("\n要查询生成的时序数据，可以使用以下Flux查询示例:")
            print("```flux")
            print("from(bucket: \"metrics\")")
            print("  |> range(start: -30d)")
            print("  |> filter(fn: (r) => r._measurement == \"vm_metrics\")")
            print("  |> filter(fn: (r) => r.node_id == \"<节点ID>\")")
            print("  |> filter(fn: (r) => r._field == \"cpu_usage\")")
            print("  |> yield(name: \"mean\")")
            print("```")
    else:
        print(f"时序数据生成失败: {result.get('error', '未知错误')}")
    
if __name__ == "__main__":
    main() 