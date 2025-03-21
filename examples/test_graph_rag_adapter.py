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

# 配置日志 - 设置为DEBUG级别以查看更多信息
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    metrics = ["cpu_usage"]  # 只使用一个确定存在的指标
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
    metrics = ["cpu_usage"]  # 只使用一个确定存在的指标
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

def test_lm_studio_direct():
    """直接测试LM Studio连接"""
    logger.info("=== 直接测试LM Studio连接 ===")
    
    # 初始化适配器
    adapter = GraphRAGAdapter(
        model_type="lmstudio",
        neo4j_config=get_neo4j_config(),
        influxdb_config=get_influxdb_config()
    )
    
    # 确保LLM客户端已初始化
    if adapter.llm_client is None:
        logger.error("LM Studio客户端未初始化")
        return
    
    # 先获取一些图数据作为上下文
    graph_data = adapter.execute_graph_query("MATCH (n:VM) RETURN n LIMIT 5")
    time_series_data = adapter.execute_time_series_query(node_type="VM", metrics=["cpu_usage"])
    
    # 构建丰富的上下文
    context = "基于系统中已有的数据:\n\n"
    
    # 添加图数据
    if graph_data.get("success", False) and graph_data.get("records", []):
        context += "==图数据==\n"
        vm_nodes = []
        for record in graph_data.get("records", []):
            if "n" in record and "_labels" in record["n"] and "VM" in record["n"]["_labels"]:
                vm_info = {
                    "name": record["n"].get("name", ""),
                    "id": record["n"].get("id", ""),
                    "vcpu": record["n"].get("vcpu", ""),
                    "vmem": record["n"].get("vmem", ""),
                }
                vm_nodes.append(vm_info)
        
        context += f"系统中有{len(vm_nodes)}个虚拟机节点，包括：\n"
        for vm in vm_nodes:
            context += f"- VM: {vm['name']}, ID: {vm['id']}, vCPU: {vm['vcpu']}, vMem: {vm['vmem']}GB\n"
    
    # 添加时序数据
    if time_series_data.get("success", False):
        context += "\n==时序数据==\n"
        context += "系统记录了以下时序指标：\n"
        
        for node_id, metrics in time_series_data.get("results", {}).items():
            context += f"{node_id}的CPU使用率数据：\n"
            for point in metrics.get("cpu_usage", [])[:3]:  # 只显示前3个数据点
                context += f"- 时间: {point['timestamp']}, 值: {point['value']}%\n"
            context += "...(更多数据省略)\n"
    
    # 添加查询能力说明
    context += "\n==查询能力说明==\n"
    context += "系统能够通过以下方式查询虚拟机数据：\n"
    context += "1. 图查询：使用Cypher语句查询Neo4j数据库中的图数据\n"
    context += "2. 时序查询：查询InfluxDB中存储的时序指标数据\n"
    context += "3. 混合查询：同时获取图数据和相关的时序数据\n"
    
    # 使用更详细的系统提示，引导模型根据上下文数据回答
    system_prompt = """你是一个智能数据分析助手，专门负责分析IT基础设施数据。
你可以访问Neo4j图数据库中的基础设施拓扑信息和InfluxDB中的性能指标数据。
当用户询问有关虚拟机、CPU使用率等问题时，请基于提供的上下文数据进行回答。
如果需要查询过去24小时CPU利用率超过90%的虚拟机，你应该：
1. 分析时序数据中的CPU使用率记录
2. 筛选出超过90%阈值的记录
3. 关联这些记录到相应的VM节点
4. 提供清晰的结果列表，包括VM名称、ID和具体的CPU使用率
请保持简洁专业，直接回答用户问题。"""
    
    # 发送查询
    prompt = "请查询过去24小时cpu利用率超过90%的虚机"
    logger.info(f"发送查询: {prompt}")
    logger.info(f"提供的上下文长度: {len(context)} 字符")
    
    response = adapter.process_query(
        query=prompt,
        context=context,
        system_prompt=system_prompt,
        temperature=0.3,  # 降低温度以获得更确定性的回答
        max_tokens=1024
    )
    
    logger.info("LM Studio响应:")
    print(response)
    
    logger.info("\n")

def main():
    """主函数"""
    logger.info("开始测试 GraphRAG 适配器功能...")
    
    # 测试各种查询功能
    test_graph_query()
    test_time_series_query()
    test_hybrid_query()
    test_natural_language_query()
    
    # 直接测试LM Studio连接
    test_lm_studio_direct()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 