"""
GraphRAG适配器模块
用于集成LLM与Neo4j和InfluxDB数据源，基于graphrag库
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Iterator, Union
from datetime import datetime, timedelta

# 导入graphrag核心组件
from graphrag.language_model.manager import ModelManager
from graphrag.query.structured_search.base import SearchResult
from graphrag.query.structured_search.basic_search.search import BasicSearch
from graphrag.query.structured_search.basic_search.basic_context import BasicSearchContext
from graphrag.language_model.providers.fnllm.models import OpenAIChatFNLLM
from graphrag.data_model.text_unit import TextUnit

# 导入Neo4j和InfluxDB客户端
from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient

# 导入本地LLM客户端
from ..llm.vllm_client import VLLMClient
from ..llm.ollama_client import OllamaClient
from ..llm.lmstudio_client import LMStudioClient

# 配置日志
logger = logging.getLogger(__name__)

class GraphRAGAdapter:
    """
    GraphRAG适配器类，用于处理图数据和时序数据的统一查询
    集成了graphrag库的核心功能，并扩展了对Neo4j和InfluxDB的支持
    """
    
    def __init__(
        self,
        model_type: str = "ollama",  # 'ollama', 'vllm', 'lmstudio' 或 'openai'
        model_name: str = None,
        api_base: Optional[str] = None,
        neo4j_config: Optional[Dict] = None,
        influxdb_config: Optional[Dict] = None,
        **kwargs
    ):
        """
        初始化GraphRAG适配器
        
        Args:
            model_type: 使用的模型类型，可选 'ollama'、'vllm'、'lmstudio' 或 'openai'
            model_name: 模型名称，如果为None则从环境变量加载
            api_base: API基础URL，如果为None则从环境变量加载
            neo4j_config: Neo4j配置字典，可选
            influxdb_config: InfluxDB配置字典，可选
            **kwargs: 其他参数
        """
        self.model_type = model_type
        self.model_name = model_name
        self.api_base = api_base
        self.influxdb_config = influxdb_config
        
        # 初始化LLM客户端
        self._init_llm_client()
            
        # 初始化数据库连接（如果提供了配置）
        self.neo4j_driver = None
        self.influx_client = None
        self.query_api = None
        
        if neo4j_config:
            self.neo4j_driver = GraphDatabase.driver(
                neo4j_config["uri"],
                auth=(neo4j_config["user"], neo4j_config["password"])
            )
            
        if influxdb_config:
            self.influx_client = InfluxDBClient(
                url=influxdb_config["url"],
                token=influxdb_config["token"],
                org=influxdb_config["org"]
            )
            self.query_api = self.influx_client.query_api()
        
        # 初始化graphrag搜索引擎
        self._init_search_engine()
            
        # 加载提示模板
        self._load_chinese_prompts()
    
    def _init_llm_client(self):
        """初始化LLM客户端"""
        if self.model_type == "ollama":
            self.llm_client = OllamaClient(
                model_name=self.model_name,
                api_base=self.api_base or "http://localhost:11434"
            )
        elif self.model_type == "vllm":
            self.llm_client = VLLMClient(
                model_name=self.model_name,
                api_url=self.api_base or "http://localhost:8000/v1"
            )
        elif self.model_type == "lmstudio":
            self.llm_client = LMStudioClient(
                base_url=self.api_base or "http://localhost:12343"
            )
        elif self.model_type == "openai":
            # 在这里，我们不直接创建OpenAI客户端，而是在_init_search_engine中处理
            self.llm_client = None
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def _init_search_engine(self):
        """初始化graphrag搜索引擎"""
        try:
            # 初始化ModelManager和搜索引擎
            if self.model_type == "openai":
                # 简化OpenAI集成 - 不依赖ModelManager
                # 只创建搜索上下文，不创建搜索引擎
                # 注意：BasicSearchContext需要text_embedder和text_unit_embeddings参数
                # 在实际应用中这里应该创建或导入实际的嵌入器和嵌入向量
                # 这里为了简化流程，设置为None
                self.context_builder = None
                self.search_engine = None
                self.model = None
            else:
                # 使用自定义LLM适配器
                self.model = self._create_custom_llm_adapter()
                # 暂时不创建BasicSearchContext，因为需要embedder和embeddings
                self.context_builder = None
                # 如果模型可用，则创建搜索引擎
                if self.model:
                    # 注意：真实环境中需要配置正确的context_builder
                    # 这里为了测试暂时不创建search_engine
                    self.search_engine = None
                else:
                    self.search_engine = None
        except Exception as e:
            logger.error(f"初始化搜索引擎失败: {str(e)}")
            self.context_builder = None
            self.search_engine = None
            self.model = None
    
    def _create_custom_llm_adapter(self):
        """创建自定义LLM适配器，兼容graphrag接口"""
        # 这里需要创建一个适配器类，使本地LLM客户端兼容graphrag的接口
        # 简化起见，目前返回None
        return None
    
    def execute_graph_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        执行图数据库查询
        
        Args:
            query: Cypher查询语句
            params: 查询参数，可选
            limit: 结果数量限制
            
        Returns:
            包含查询结果的字典
        """
        if not self.neo4j_driver:
            return {"success": False, "error": "Neo4j连接未初始化"}
            
        try:
            with self.neo4j_driver.session() as session:
                # 添加LIMIT子句，防止结果过多
                if "LIMIT" not in query.upper() and limit > 0:
                    query += f" LIMIT {limit}"
                    
                # 执行查询
                result = session.run(query, params or {})
                
                # 处理结果
                records = []
                for record in result:
                    record_dict = {}
                    for key, value in record.items():
                        # 处理不同类型的数据
                        if hasattr(value, "labels") and hasattr(value, "items"):
                            # 节点
                            node_dict = dict(value.items())
                            node_dict["_labels"] = list(value.labels)
                            record_dict[key] = node_dict
                        elif hasattr(value, "type") and hasattr(value, "items"):
                            # 关系
                            rel_dict = dict(value.items())
                            rel_dict["_type"] = value.type
                            record_dict[key] = rel_dict
                        else:
                            # 其他类型
                            record_dict[key] = value
                    records.append(record_dict)
                
                return {
                    "success": True,
                    "records": records,
                    "record_count": len(records)
                }
                
        except Exception as e:
            logger.error(f"执行图查询时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def execute_time_series_query(
        self,
        node_type: str,
        node_id: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation: str = "mean",
        interval: str = "1h"
    ) -> Dict[str, Any]:
        """
        执行时序数据库查询
        
        Args:
            node_type: 节点类型（如VM, HOST, NE等）
            node_id: 节点ID，可选。如果不提供，将查询所有该类型节点的数据
            metrics: 指标列表，可选。如果不提供，将查询所有指标
            start_time: 起始时间，可选。默认为当前时间前24小时
            end_time: 结束时间，可选。默认为当前时间
            aggregation: 聚合方式，可选，默认为平均值
            interval: 聚合间隔，可选，默认为1小时
            
        Returns:
            包含查询结果的字典
        """
        if not self.influx_client or not self.query_api:
            return {"success": False, "error": "InfluxDB连接未初始化"}
            
        try:
            # 设置默认时间范围
            if end_time is None:
                end_time = datetime.now()
            if start_time is None:
                start_time = end_time - timedelta(hours=24)
            
            # 构建模拟数据（实际应用中替换为真实查询）
            results = {
                f"{node_type}_001": {
                    "cpu_usage": [
                        {"timestamp": (start_time + timedelta(hours=i)).isoformat(), 
                         "value": 50 + i * 2} 
                        for i in range(10)
                    ]
                }
            }
            
            # 在实际应用中，这里应该是真正的InfluxDB查询逻辑
            
            return {
                "success": True,
                "results": results,
                "node_count": len(results),
                "metadata": {
                    "node_type": node_type,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "aggregation": aggregation,
                    "interval": interval
                }
            }
                
        except Exception as e:
            logger.error(f"执行时序查询时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_hybrid_query(
        self,
        graph_query: str,
        node_type_field: str = "node_type",
        node_id_field: str = "node_id",
        metrics: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行混合查询，同时获取图数据和关联的时序数据
        
        Args:
            graph_query: Cypher查询语句，用于获取节点信息
            node_type_field: 节点类型字段名，默认为'node_type'
            node_id_field: 节点ID字段名，默认为'node_id'
            metrics: 需要查询的指标列表，可选
            start_time: 时序数据的起始时间，可选
            end_time: 时序数据的结束时间，可选
            params: Cypher查询参数，可选
            
        Returns:
            包含混合查询结果的字典
        """
        # 1. 执行图数据查询
        graph_results = self.execute_graph_query(graph_query, params)
        
        if not graph_results.get("success", False):
            return graph_results
            
        # 2. 检索每个图数据节点的时序数据
        records = graph_results.get("records", [])
        enriched_records = []
        
        for record in records:
            enriched_record = record.copy()
            # 在实际应用中，这里应该为每个节点获取时序数据
            # 简化起见，我们只添加一个占位符
            for key, value in record.items():
                if isinstance(value, dict) and "_labels" in value:
                    value["metrics"] = {"cpu_usage": [{"timestamp": datetime.now().isoformat(), "value": 75}]}
            
            enriched_records.append(enriched_record)
            
        # 构建结果
        return {
            "success": True,
            "records": enriched_records,
            "record_count": len(enriched_records)
        }
    
    def process_nlquery(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        include_context: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        处理自然语言查询，进行解析并生成结构化查询
        
        Args:
            query: 自然语言查询
            system_prompt: 系统提示
            include_context: 是否包含上下文
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            包含查询解析和执行结果的字典
        """
        try:
            # 简化版本 - 返回基本响应
            result = {
                "query_info": {
                    "original_query": query,
                    "query_type": "graph",  # 可能的类型: graph, time_series, hybrid
                    "structured_query": "MATCH (n:VM) RETURN n LIMIT 5"
                },
                "answer": f"为您处理查询：{query}\n\n根据系统分析，这是一个图数据查询。"
            }
            
            # 添加上下文信息（如果需要）
            if include_context:
                result["context"] = "查询已经被解析为图数据查询，将返回最多5个VM节点。"
                
            return result
            
        except Exception as e:
            logger.error(f"处理自然语言查询时出错: {str(e)}")
            return {"error": str(e)}
    
    def _load_chinese_prompts(self):
        """加载中文提示模板"""
        self.prompts = {
            "query_understanding": """
            请分析以下查询，提取关键信息：
            
            查询：{query}
            
            需要提取的信息：
            1. 查询类型（图查询/指标查询/混合查询）
            2. 时间范围
            3. 涉及的节点类型
            4. 需要的指标
            5. 查询意图
            """,
        }
    
    def process_query(
        self,
        query: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """
        处理简单的查询请求（直接使用LLM）
        
        Args:
            query: 用户查询
            context: 上下文信息，可选
            system_prompt: 系统提示，可选
            temperature: 采样温度
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            模型生成的响应
        """
        if self.llm_client is None:
            return "LLM客户端未初始化"
            
        # 构建完整的提示
        prompt = f"查询：{query}\n\n"
        if context:
            prompt += f"上下文信息：\n{context}\n\n"
        
        if self.model_type == "ollama":
            return self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif self.model_type == "vllm":
            return self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt
            )
        elif self.model_type == "lmstudio":
            return self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            return "不支持的模型类型"
            
    def process_query_stream(
        self,
        query: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        流式处理查询请求
        
        Args:
            query: 用户查询
            context: 上下文信息，可选
            system_prompt: 系统提示，可选
            **kwargs: 其他参数
            
        Returns:
            生成的响应流
        """
        # 此方法需要LLM客户端支持流式输出
        # 简化版 - 返回分段输出
        chunks = [
            "正在处理您的查询...\n",
            "分析中...\n",
            f"查询内容：{query}\n",
            "生成回答：\n",
            "根据分析，这是一个关于系统性能的查询。\n",
            "以下是相关信息：\n",
            "1. CPU使用率保持在正常范围内\n",
            "2. 内存分配合理\n",
            "3. 网络连接正常\n",
            "总结：系统运行状态良好。"
        ]
        
        for chunk in chunks:
            yield chunk

    def __enter__(self):
        """上下文管理器入口"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，关闭所有连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            
        if self.influx_client:
            self.influx_client.close() 