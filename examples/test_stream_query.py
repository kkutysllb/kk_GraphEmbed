#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GraphRAG适配器流式查询测试脚本
展示如何使用GraphRAG适配器的流式响应功能
"""

import os
import sys
import time
import logging

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dynamic_graph_rag.rag.graph_rag_adapter import GraphRAGAdapter
from dynamic_graph_rag.config.settings import get_neo4j_config, get_influxdb_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_stream():
    """测试简单的流式响应功能"""
    logger.info("=== 测试简单流式响应 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",  # 使用LM Studio作为LLM后端
        neo4j_config=get_neo4j_config(),  # 从配置文件获取Neo4j连接信息
        influxdb_config=get_influxdb_config()  # 从配置文件获取InfluxDB连接信息
    )
    
    # 设置查询
    query = "请介绍虚拟机的主要性能指标有哪些，以及它们对系统性能的影响。"
    system_prompt = """你是一个专业的系统分析师，精通虚拟化技术和系统性能分析。
请详细介绍各种系统指标和它们的意义。"""
    
    logger.info(f"执行流式查询: {query}")
    print("\n开始生成回答:\n" + "-" * 50)
    
    # 流式生成回答
    for chunk in adapter.process_query_stream(
        query=query,
        system_prompt=system_prompt,
        temperature=0.7
    ):
        print(chunk, end="", flush=True)
        time.sleep(0.02)  # 模拟网络延迟
    
    print("\n" + "-" * 50 + "\n")
    
def test_context_aware_stream():
    """测试基于上下文的流式响应功能"""
    logger.info("=== 测试基于上下文的流式响应 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",
        neo4j_config=get_neo4j_config(),
        influxdb_config=get_influxdb_config()
    )
    
    # 先执行图查询获取上下文
    graph_query = "MATCH (n:VM) RETURN n LIMIT 3"
    logger.info(f"获取上下文数据: {graph_query}")
    graph_result = adapter.execute_graph_query(graph_query)
    
    # 构建上下文
    context = None
    if graph_result.get("success", False):
        context = adapter._format_graph_results(graph_result)
        logger.info("成功获取上下文数据")
    else:
        logger.error("获取上下文数据失败，将使用空上下文")
    
    # 设置查询
    query = "基于这些虚拟机的信息，你能分析出什么？"
    system_prompt = "你是一个专业的系统分析师，擅长从有限的信息中得出见解。"
    
    logger.info(f"执行基于上下文的流式查询: {query}")
    print("\n开始生成回答:\n" + "-" * 50)
    
    # 流式生成回答
    for chunk in adapter.process_query_stream(
        query=query,
        context=context,
        system_prompt=system_prompt,
        temperature=0.7
    ):
        print(chunk, end="", flush=True)
        time.sleep(0.02)  # 模拟网络延迟
    
    print("\n" + "-" * 50 + "\n")

def main():
    """主函数"""
    logger.info("开始测试 GraphRAG 适配器的流式查询功能...")
    
    # 测试流式响应功能
    test_simple_stream()
    test_context_aware_stream()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 