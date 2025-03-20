#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
运行图数据导入 - 命令行工具
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from dynamic_graph_rag.data_import.graph_data_importer import GraphDataImporter, main
from dynamic_graph_rag.config.settings import GRAPH_DB_CONFIG
from neo4j import GraphDatabase

def clean_database_completely():
    """使用原始Neo4j查询彻底清理数据库中的所有数据、标签和元数据"""
    print("正在彻底清除Neo4j数据库...")
    
    # 连接到Neo4j
    driver = GraphDatabase.driver(
        GRAPH_DB_CONFIG["uri"],
        auth=(GRAPH_DB_CONFIG["user"], GRAPH_DB_CONFIG["password"])
    )
    
    with driver.session(database=GRAPH_DB_CONFIG["database"]) as session:
        # 删除所有节点和关系
        print("删除所有节点和关系...")
        session.run("MATCH (n) DETACH DELETE n")
        
        try:
            # 删除所有索引
            print("删除所有索引...")
            session.run("CALL db.indexes() YIELD name, type WHERE type <> 'LOOKUP' CALL db.dropIndex(name) YIELD name as dropped RETURN count(*)")
            
            # 删除所有约束
            print("删除所有约束...")
            session.run("CALL db.constraints() YIELD name CALL db.dropConstraint(name) YIELD name as dropped RETURN count(*)")
            
            # 强制移除Node标签
            print("强制移除Node标签...")
            session.run("CREATE (n:Node {id: 'temp'}) DELETE n")
            
            # 强制移除RELATES关系
            print("强制移除RELATES关系类型...")
            session.run("CREATE (a {id: 'temp1'})-[r:RELATES]->(b {id: 'temp2'}) DELETE a, b, r")
            
            # 确保不再有Node标签
            print("确认Node标签已清除...")
            session.run("MATCH (n:Node) REMOVE n:Node")
        except Exception as e:
            print(f"清理过程中出错: {str(e)}")
    
    driver.close()
    print("数据库清理完成")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='图数据导入工具')
    
    parser.add_argument('--input', '-i', required=True, type=str,
                        help='输入JSON文件路径')
    
    parser.add_argument('--clear', '-c', action='store_true',
                        help='清空Neo4j数据库中的现有数据')
    
    parser.add_argument('--report', '-r', type=str,
                        help='导入报告输出路径（默认为输入文件同目录下的.report.md文件）')
    
    parser.add_argument('--uri', type=str,
                        help='Neo4j数据库URI（默认使用配置文件中的值）')
    
    parser.add_argument('--user', type=str,
                        help='Neo4j用户名（默认使用配置文件中的值）')
    
    parser.add_argument('--password', type=str,
                        help='Neo4j密码（默认使用配置文件中的值）')
    
    parser.add_argument('--database', type=str,
                        help='Neo4j数据库名（默认使用配置文件中的值）')
    
    return parser.parse_args()

def main():
    """主函数，执行导入"""
    args = parse_arguments()
    
    # 检查输入文件是否存在
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"错误: 输入文件 {input_file} 不存在")
        sys.exit(1)
    
    # 确定报告文件路径
    report_file = args.report or input_file.with_suffix('.report.md')
    
    print(f"开始导入数据从 {input_file} 到Neo4j...")
    
    # 创建导入器实例
    importer = GraphDataImporter(
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    # 执行导入
    stats = importer.import_data(
        json_file_path=str(input_file),
        clear_existing=args.clear,
        report_file=report_file
    )
    
    # 输出结果摘要
    print("\n导入摘要:")
    print(f"节点: {stats['nodes_imported']}/{stats['nodes_total']} 导入成功")
    print(f"边: {stats['edges_imported']}/{stats['edges_total']} 导入成功")
    print(f"错误数: {stats.get('errors', 0)}")
    print(f"用时: {stats.get('duration', 0):.2f} 秒")
    
    verification = stats.get("verification", {})
    if verification:
        all_good = (verification.get("nodes_count_match", False) and 
                    verification.get("edges_count_match", False) and 
                    verification.get("node_types_consistent", False) and 
                    verification.get("edge_types_consistent", False) and 
                    verification.get("orphan_edges", 1) == 0)
        
        if all_good:
            print("\n✅ 导入成功，所有验证通过")
        else:
            print("\n❌ 导入完成，但存在一些验证问题")
    
    # 输出报告位置
    print(f"\n完整报告已保存到: {report_file}")
    
    # 返回导入的节点和边数量，用于可能的脚本集成
    return stats['nodes_imported'], stats['edges_imported']

if __name__ == "__main__":
    # 执行基本清理
    clean_database_completely()
    
    # 然后运行导入程序
    main() 