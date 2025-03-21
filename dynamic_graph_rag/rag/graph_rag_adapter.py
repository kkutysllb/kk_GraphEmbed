"""
GraphRAG适配器模块
用于集成LLM与Neo4j和InfluxDB数据源
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient

from ..llm.vllm_client import VLLMClient
from ..llm.ollama_client import OllamaClient
from ..llm.lmstudio_client import LMStudioClient
import json

class GraphRAGAdapter:
    """GraphRAG适配器类，用于处理图数据和时序数据的统一查询"""
    
    def __init__(
        self,
        model_type: str = "ollama",  # 'ollama', 'vllm', 或 'lmstudio'
        model_name: str = "deepseek-r1:32b",
        api_base: Optional[str] = None,
        neo4j_config: Optional[Dict] = None,
        influxdb_config: Optional[Dict] = None,
        **kwargs
    ):
        """
        初始化GraphRAG适配器
        
        Args:
            model_type: 使用的模型类型，可选 'ollama'、'vllm' 或 'lmstudio'
            model_name: 模型名称
            api_base: API基础URL
            neo4j_config: Neo4j配置字典，可选
            influxdb_config: InfluxDB配置字典，可选
            **kwargs: 其他参数
        """
        self.model_type = model_type
        
        # 初始化LLM客户端
        if model_type == "ollama":
            self.llm_client = OllamaClient(
                model_name=model_name,
                api_base=api_base or "http://localhost:11434"
            )
        elif model_type == "vllm":
            self.llm_client = VLLMClient(
                model_name=model_name,
                api_url=api_base or "http://localhost:8000/v1",
                **kwargs
            )
        elif model_type == "lmstudio":
            self.llm_client = LMStudioClient(
                base_url=api_base or "http://localhost:12343"
            )
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
            
        # 初始化数据库连接（如果提供了配置）
        self.neo4j_driver = None
        self.influx_client = None
        
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
            
        # 加载提示模板
        self._load_chinese_prompts()
            
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
        # 构建完整的提示
        messages = []
        
        # 添加系统提示
        if system_prompt:
            # 强化系统提示
            enhanced_system_prompt = f"""你是一个专业的系统分析师。请严格按照以下角色设定和职责来回答所有问题：

{system_prompt}

重要提示：
1. 你必须始终以系统分析师的身份回答
2. 回答必须围绕系统分析、故障诊断和性能优化
3. 不要偏离系统分析师的专业领域
4. 如果问题超出系统分析范围，请明确指出
5. 回答要简洁专业，不要包含思考过程
6. 使用清晰的结构和专业的术语"""
            messages.append({"role": "system", "content": enhanced_system_prompt})
            
        # 构建用户提示
        user_prompt = f"""查询：{query}\n\n"""
        if context:
            user_prompt += f"""上下文信息：
{context}

基于上述上下文信息回答用户的查询。如果上下文信息不足以回答问题，请明确指出。
"""
        messages.append({"role": "user", "content": user_prompt})
        
        # 使用LLM生成响应
        if self.model_type == "ollama":
            return self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=enhanced_system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif self.model_type == "vllm":
            # 更新客户端的参数
            self.llm_client.temperature = temperature
            self.llm_client.max_tokens = max_tokens
            return self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
        else:  # lmstudio
            return self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=enhanced_system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
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
            
            "result_synthesis": """
            基于以下信息生成查询结果：
            
            图数据：
            {graph_data}
            
            时序数据：
            {metric_data}
            
            请提供：
            1. 数据摘要
            2. 关键发现
            3. 可能的建议
            """
        }
        
    def close(self):
        """关闭数据库连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.influx_client:
            self.influx_client.close()
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close() 