#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GraphRAG适配器测试脚本
展示如何使用GraphRAG适配器进行图查询、时序查询和混合查询
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dynamic_graph_rag.rag.graph_rag_adapter import GraphRAGAdapter
from dynamic_graph_rag.config.settings import get_neo4j_config, get_influxdb_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def pretty_print_json(data):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def test_graph_query():
    """测试图数据查询功能"""
    logger.info("=== 测试图数据查询 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",  # 使用LM Studio作为LLM后端
        neo4j_config=get_neo4j_config(),  # 从配置文件获取Neo4j连接信息
        influxdb_config=get_influxdb_config()  # 从配置文件获取InfluxDB连接信息
    )
    
    # 执行Cypher查询
    logger.info("执行Cypher查询: MATCH (n:VM) RETURN n LIMIT 5")
    result = adapter.execute_graph_query("MATCH (n:VM) RETURN n LIMIT 5")
    
    # 打印结果
    if result.get("success", False):
        logger.info(f"查询成功，返回 {result.get('record_count', 0)} 条记录")
        logger.info("查询结果示例:")
        pretty_print_json(result)
    else:
        logger.error(f"查询失败: {result.get('error', 'Unknown error')}")
    
    logger.info("\n")
    
def test_time_series_query():
    """测试时序数据查询功能"""
    logger.info("=== 测试时序数据查询 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",
        neo4j_config=get_neo4j_config(),
        influxdb_config=get_influxdb_config()
    )
    
    # 设置查询参数
    node_type = "VM"
    metrics = ["cpu_usage", "memory_usage"]
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    
    # 执行时序数据查询
    logger.info(f"查询节点类型 {node_type} 的 {', '.join(metrics)} 指标数据")
    result = adapter.execute_time_series_query(
        node_type=node_type,
        metrics=metrics,
        start_time=start_time,
        end_time=end_time
    )
    
    # 打印结果
    if result.get("success", False):
        logger.info(f"查询成功，返回 {result.get('node_count', 0)} 个节点的数据")
        logger.info("查询结果示例:")
        pretty_print_json(result)
    else:
        logger.error(f"查询失败: {result.get('error', 'Unknown error')}")
    
    logger.info("\n")
    
def test_hybrid_query():
    """测试混合查询功能"""
    logger.info("=== 测试混合查询 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",
        neo4j_config=get_neo4j_config(),
        influxdb_config=get_influxdb_config()
    )
    
    # 设置查询参数
    graph_query = "MATCH (n:VM) RETURN n LIMIT 2"
    metrics = ["cpu_usage", "memory_usage"]
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    
    # 执行混合查询
    logger.info(f"执行混合查询: {graph_query}")
    result = adapter.execute_hybrid_query(
        graph_query=graph_query,
        metrics=metrics,
        start_time=start_time,
        end_time=end_time
    )
    
    # 打印结果
    if result.get("success", False):
        logger.info(f"查询成功，返回 {result.get('record_count', 0)} 条记录")
        logger.info("查询结果示例:")
        pretty_print_json(result)
    else:
        logger.error(f"查询失败: {result.get('error', 'Unknown error')}")
    
    logger.info("\n")
    
def test_natural_language_query():
    """测试自然语言查询功能"""
    logger.info("=== 测试自然语言查询 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",
        neo4j_config=get_neo4j_config(),
        influxdb_config=get_influxdb_config()
    )
    
    # 执行自然语言查询
    nl_query = "查找过去24小时内CPU使用率超过80%的虚拟机"
    logger.info(f"执行自然语言查询: {nl_query}")
    
    result = adapter.process_nlquery(
        query=nl_query,
        system_prompt="你是一个专业的系统分析师，擅长诊断性能问题和解读系统数据。",
        include_context=True
    )
    
    # 打印结果
    if "error" not in result:
        logger.info("查询解析结果:")
        logger.info(f"查询类型: {result.get('query_info', {}).get('query_type', 'unknown')}")
        
        if "answer" in result:
            logger.info("生成的回答:")
            print(result["answer"])
    else:
        logger.error(f"查询失败: {result.get('error', 'Unknown error')}")
    
    logger.info("\n")

def main():
    """主函数"""
    logger.info("开始测试 GraphRAG 适配器功能...")
    
    # 测试各种查询功能
    test_graph_query()
    test_time_series_query()
    test_hybrid_query()
    test_natural_language_query()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 