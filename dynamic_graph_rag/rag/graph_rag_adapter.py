"""
GraphRAG适配器模块
用于集成LLM与Neo4j和InfluxDB数据源
"""

from typing import Dict, List, Optional, Any, Iterator
from datetime import datetime, timedelta
import json

from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient

from ..llm.vllm_client import VLLMClient
from ..llm.ollama_client import OllamaClient
from ..llm.lmstudio_client import LMStudioClient

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
            
    def process_query_stream(
        self,
        query: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Iterator[str]:
        """
        处理查询并流式返回响应
        
        Args:
            query: 用户查询
            context: 上下文信息，可选
            system_prompt: 系统提示，可选
            temperature: 采样温度
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            生成的响应流
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
        
        # 流式生成响应
        if self.model_type == "ollama":
            yield from self.llm_client.generate_stream(
                prompt=user_prompt,
                system_prompt=enhanced_system_prompt if system_prompt else None,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif self.model_type == "vllm":
            yield from self.llm_client.generate_stream(
                prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        else:  # lmstudio
            yield from self.llm_client.generate_stream(
                prompt=user_prompt,
                system_prompt=enhanced_system_prompt if system_prompt else None,
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
            return {"error": "Neo4j连接未初始化"}
            
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
                        # 处理Neo4j节点
                        if hasattr(value, "labels") and hasattr(value, "items"):
                            node_dict = dict(value.items())
                            node_dict["_labels"] = list(value.labels)
                            record_dict[key] = node_dict
                        # 处理Neo4j关系
                        elif hasattr(value, "type") and hasattr(value, "items") and callable(getattr(value, "type")):
                            rel_dict = dict(value.items())
                            rel_dict["_type"] = value.type
                            rel_dict["_start_node_id"] = value.start_node.id
                            rel_dict["_end_node_id"] = value.end_node.id
                            record_dict[key] = rel_dict
                        # 处理基本类型
                        else:
                            record_dict[key] = value
                    records.append(record_dict)
                
                # 获取查询的元数据
                summary = result.consume()
                metadata = {
                    "contains_updates": summary.counters.contains_updates(),
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                    "execution_time_ms": summary.result_available_after
                }
                
                return {
                    "success": True,
                    "records": records,
                    "record_count": len(records),
                    "metadata": metadata
                }
                
        except Exception as e:
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
        if not self.influx_client:
            return {"error": "InfluxDB连接未初始化"}
            
        try:
            # 设置默认时间范围
            if end_time is None:
                end_time = datetime.now()
            if start_time is None:
                start_time = end_time - timedelta(hours=24)
                
            # 构建Flux查询
            measurement = f"{node_type.lower()}_metrics"
            
            # 基本查询
            query = f"""
            from(bucket: "{self.influx_client._bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "{measurement}")
            """
            
            # 添加节点ID过滤
            if node_id:
                query += f'|> filter(fn: (r) => r["node_id"] == "{node_id}")\n'
                
            # 添加指标过滤
            if metrics and len(metrics) > 0:
                metrics_filter = " or ".join([f'r["metric"] == "{m}"' for m in metrics])
                query += f'|> filter(fn: (r) => {metrics_filter})\n'
                
            # 添加聚合
            query += f"""
                |> aggregateWindow(every: {interval}, fn: {aggregation}, createEmpty: false)
                |> yield(name: "{aggregation}")
            """
            
            # 执行查询
            tables = self.influx_client.query_api().query(query, org=self.influx_client._org)
            
            # 处理结果
            results = {}
            for table in tables:
                for record in table.records:
                    # 获取记录信息
                    node_id = record.values.get("node_id", "unknown")
                    metric = record.values.get("metric", "unknown")
                    timestamp = record.get_time()
                    value = record.get_value()
                    
                    # 初始化结果结构
                    if node_id not in results:
                        results[node_id] = {}
                    if metric not in results[node_id]:
                        results[node_id][metric] = []
                        
                    # 添加数据点
                    results[node_id][metric].append({
                        "timestamp": timestamp.isoformat(),
                        "value": value
                    })
            
            # 添加查询元数据
            metadata = {
                "node_type": node_type,
                "metrics": metrics,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "aggregation": aggregation,
                "interval": interval
            }
            
            return {
                "success": True,
                "results": results,
                "node_count": len(results),
                "metadata": metadata
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query_params": {
                    "node_type": node_type,
                    "node_id": node_id,
                    "metrics": metrics,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None
                }
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
        if not self.neo4j_driver or not self.influx_client:
            return {"error": "数据库连接未完全初始化"}
            
        try:
            # 1. 执行图数据查询
            graph_results = self.execute_graph_query(graph_query, params)
            
            if not graph_results.get("success", False):
                return graph_results
                
            # 2. 为每个查询到的节点获取时序数据
            records = graph_results.get("records", [])
            enriched_records = []
            
            for record in records:
                enriched_record = record.copy()
                
                # 确保记录中有需要的字段
                for field_name, fields in record.items():
                    # 检查是否是节点记录
                    if isinstance(fields, dict) and "_labels" in fields:
                        node_type = None
                        node_id = None
                        
                        # 尝试从节点属性中获取节点类型和ID
                        if node_type_field in fields:
                            node_type = fields[node_type_field]
                        elif "_labels" in fields and len(fields["_labels"]) > 0:
                            # 如果节点类型字段不存在，尝试使用标签
                            node_type = fields["_labels"][0]
                            
                        if node_id_field in fields:
                            node_id = fields[node_id_field]
                        elif "id" in fields:
                            # 如果节点ID字段不存在，尝试使用id字段
                            node_id = fields["id"]
                            
                        # 如果找到节点类型和ID，查询时序数据
                        if node_type and node_id:
                            # 执行时序数据查询
                            time_series_results = self.execute_time_series_query(
                                node_type=node_type,
                                node_id=node_id,
                                metrics=metrics,
                                start_time=start_time,
                                end_time=end_time
                            )
                            
                            # 将时序数据添加到节点记录中
                            if time_series_results.get("success", False):
                                ts_data = time_series_results.get("results", {}).get(node_id, {})
                                if ts_data:
                                    fields["metrics"] = ts_data
                
                enriched_records.append(enriched_record)
                
            # 3. 构建最终结果
            return {
                "success": True,
                "records": enriched_records,
                "record_count": len(enriched_records),
                "graph_metadata": graph_results.get("metadata", {}),
                "time_series_metadata": {
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "metrics": metrics
                }
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query_params": {
                    "graph_query": graph_query,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "metrics": metrics
                }
            } 

    def process_nlquery(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        include_context: bool = True,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        处理自然语言查询，转换为结构化查询并执行
        
        Args:
            query: 自然语言查询
            system_prompt: 系统提示，可选
            include_context: 是否在最终回答中包含查询结果作为上下文
            temperature: 采样温度，用于解析查询时
            
        Returns:
            包含查询结果的字典
        """
        try:
            # 1. 使用提示模板解析查询
            understanding_prompt = self.prompts["query_understanding"].format(query=query)
            
            # 使用较低温度保证解析的准确性
            understanding_response = self.llm_client.generate(
                prompt=understanding_prompt,
                system_prompt="你是一个专业的查询分析器，擅长将自然语言查询转换为结构化查询。请严格按要求提取信息。",
                temperature=temperature,
                max_tokens=512
            )
            
            # 2. 解析响应，提取关键参数
            query_info = self._parse_understanding_response(understanding_response)
            
            # 3. 根据查询类型执行相应的操作
            query_type = query_info.get("query_type", "unknown")
            result = None
            context = None
            
            if query_type == "graph":
                # 执行图查询
                cypher_query = query_info.get("cypher_query")
                if not cypher_query:
                    # 如果没有直接提供Cypher查询，尝试构建一个
                    cypher_query = self._build_cypher_query(query_info)
                    
                result = self.execute_graph_query(cypher_query)
                if include_context and result.get("success", False):
                    context = self._format_graph_results(result)
                    
            elif query_type == "metric":
                # 执行时序数据查询
                node_type = query_info.get("node_type")
                node_id = query_info.get("node_id")
                metrics = query_info.get("metrics", [])
                time_range = query_info.get("time_range", {})
                
                start_time = None
                end_time = None
                
                if "start" in time_range:
                    try:
                        start_time = datetime.fromisoformat(time_range["start"])
                    except:
                        start_time = datetime.now() - timedelta(hours=24)
                        
                if "end" in time_range:
                    try:
                        end_time = datetime.fromisoformat(time_range["end"])
                    except:
                        end_time = datetime.now()
                
                result = self.execute_time_series_query(
                    node_type=node_type,
                    node_id=node_id,
                    metrics=metrics,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if include_context and result.get("success", False):
                    context = self._format_time_series_results(result)
                    
            elif query_type == "hybrid":
                # 执行混合查询
                cypher_query = query_info.get("cypher_query")
                metrics = query_info.get("metrics", [])
                time_range = query_info.get("time_range", {})
                
                start_time = None
                end_time = None
                
                if "start" in time_range:
                    try:
                        start_time = datetime.fromisoformat(time_range["start"])
                    except:
                        start_time = datetime.now() - timedelta(hours=24)
                        
                if "end" in time_range:
                    try:
                        end_time = datetime.fromisoformat(time_range["end"])
                    except:
                        end_time = datetime.now()
                
                if not cypher_query:
                    # 如果没有直接提供Cypher查询，尝试构建一个
                    cypher_query = self._build_cypher_query(query_info)
                
                result = self.execute_hybrid_query(
                    graph_query=cypher_query,
                    metrics=metrics,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if include_context and result.get("success", False):
                    context = self._format_hybrid_results(result)
            
            # 4. 根据查询结果生成最终回答
            final_response = {}
            
            if result:
                final_response["query_result"] = result
                final_response["query_info"] = query_info
                
                if include_context and context:
                    # 使用LLM基于上下文生成回答
                    system_prompt = system_prompt or "你是一个专业的数据分析师，擅长解读数据并提供洞察。"
                    answer = self.process_query(
                        query=query,
                        context=context,
                        system_prompt=system_prompt
                    )
                    final_response["answer"] = answer
            
            return final_response
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
            
    def _parse_understanding_response(self, response: str) -> Dict[str, Any]:
        """解析查询理解响应，提取关键参数"""
        lines = response.strip().split("\n")
        query_info = {
            "query_type": "unknown",
            "time_range": {},
            "metrics": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是章节标题
            if "查询类型" in line or "1." in line:
                current_section = "query_type"
            elif "时间范围" in line or "2." in line:
                current_section = "time_range"
            elif "节点类型" in line or "3." in line:
                current_section = "node_type"
            elif "指标" in line or "4." in line:
                current_section = "metrics"
            elif "查询意图" in line or "5." in line:
                current_section = "intent"
            elif "Cypher" in line:
                current_section = "cypher"
            else:
                # 根据当前章节处理内容
                if current_section == "query_type":
                    if "图" in line:
                        query_info["query_type"] = "graph"
                    elif "指标" in line or "时序" in line:
                        query_info["query_type"] = "metric"
                    elif "混合" in line:
                        query_info["query_type"] = "hybrid"
                elif current_section == "time_range":
                    if "开始" in line or "起始" in line:
                        # 尝试解析开始时间
                        query_info["time_range"]["start"] = line.split(":", 1)[-1].strip()
                    elif "结束" in line or "终止" in line:
                        # 尝试解析结束时间
                        query_info["time_range"]["end"] = line.split(":", 1)[-1].strip()
                    elif "过去" in line:
                        # 处理相对时间表述
                        if "小时" in line:
                            hours = int(''.join(filter(str.isdigit, line)))
                            query_info["time_range"]["start"] = (datetime.now() - timedelta(hours=hours)).isoformat()
                        elif "天" in line:
                            days = int(''.join(filter(str.isdigit, line)))
                            query_info["time_range"]["start"] = (datetime.now() - timedelta(days=days)).isoformat()
                        query_info["time_range"]["end"] = datetime.now().isoformat()
                elif current_section == "node_type":
                    if ":" in line:
                        query_info["node_type"] = line.split(":", 1)[-1].strip()
                    else:
                        query_info["node_type"] = line
                elif current_section == "metrics":
                    metrics = []
                    if ":" in line:
                        metrics_text = line.split(":", 1)[-1].strip()
                    else:
                        metrics_text = line
                    
                    # 尝试解析指标列表
                    if "," in metrics_text:
                        metrics = [m.strip() for m in metrics_text.split(",")]
                    elif "、" in metrics_text:
                        metrics = [m.strip() for m in metrics_text.split("、")]
                    else:
                        metrics = [metrics_text.strip()]
                        
                    # 过滤空值
                    metrics = [m for m in metrics if m]
                    if metrics:
                        query_info["metrics"] = metrics
                elif current_section == "intent":
                    query_info["intent"] = line
                elif current_section == "cypher":
                    if "cypher_query" not in query_info:
                        query_info["cypher_query"] = ""
                    query_info["cypher_query"] += line + "\n"
        
        return query_info
        
    def _build_cypher_query(self, query_info: Dict[str, Any]) -> str:
        """根据查询信息构建Cypher查询"""
        node_type = query_info.get("node_type")
        
        if not node_type:
            # 默认查询所有节点
            return "MATCH (n) RETURN n LIMIT 10"
            
        # 构建基本查询
        cypher = f"MATCH (n:{node_type}) "
        
        # 添加条件过滤
        filters = []
        if "node_id" in query_info:
            filters.append(f"n.id = '{query_info['node_id']}'")
        
        if filters:
            cypher += "WHERE " + " AND ".join(filters) + " "
            
        # 返回结果
        cypher += "RETURN n LIMIT 20"
        
        return cypher
        
    def _format_graph_results(self, result: Dict[str, Any]) -> str:
        """格式化图查询结果为文本上下文"""
        if not result.get("success", False):
            return f"查询失败: {result.get('error', '未知错误')}"
            
        records = result.get("records", [])
        if not records:
            return "查询成功，但未找到匹配的数据。"
            
        text = f"查询结果 ({len(records)} 条记录):\n\n"
        
        for i, record in enumerate(records, 1):
            text += f"记录 {i}:\n"
            for field_name, value in record.items():
                # 处理节点
                if isinstance(value, dict) and "_labels" in value:
                    labels = value.get("_labels", [])
                    text += f"  - {field_name} (类型: {', '.join(labels)}):\n"
                    
                    # 添加节点属性
                    for attr, attr_value in value.items():
                        if not attr.startswith("_"):
                            text += f"    * {attr}: {attr_value}\n"
                # 处理关系
                elif isinstance(value, dict) and "_type" in value:
                    rel_type = value.get("_type", "UNKNOWN")
                    text += f"  - {field_name} (关系类型: {rel_type}):\n"
                    
                    # 添加关系属性
                    for attr, attr_value in value.items():
                        if not attr.startswith("_"):
                            text += f"    * {attr}: {attr_value}\n"
                # 处理基本值
                else:
                    text += f"  - {field_name}: {value}\n"
            text += "\n"
            
        return text
        
    def _format_time_series_results(self, result: Dict[str, Any]) -> str:
        """格式化时序数据查询结果为文本上下文"""
        if not result.get("success", False):
            return f"查询失败: {result.get('error', '未知错误')}"
            
        node_results = result.get("results", {})
        if not node_results:
            return "查询成功，但未找到匹配的数据。"
            
        # 获取元数据
        metadata = result.get("metadata", {})
        node_type = metadata.get("node_type", "未知类型")
        start_time = metadata.get("start_time", "未知")
        end_time = metadata.get("end_time", "未知")
        
        text = f"时序数据查询结果 (节点类型: {node_type}, 时间范围: {start_time} 到 {end_time}):\n\n"
        
        for node_id, metrics in node_results.items():
            text += f"节点 {node_id}:\n"
            
            for metric_name, data_points in metrics.items():
                # 计算统计信息
                if data_points:
                    values = [dp["value"] for dp in data_points if dp["value"] is not None]
                    if values:
                        avg_value = sum(values) / len(values)
                        max_value = max(values)
                        min_value = min(values)
                        
                        text += f"  - 指标: {metric_name}\n"
                        text += f"    * 数据点数: {len(data_points)}\n"
                        text += f"    * 平均值: {avg_value:.2f}\n"
                        text += f"    * 最大值: {max_value:.2f}\n"
                        text += f"    * 最小值: {min_value:.2f}\n"
                        
                        # 添加最近几个数据点
                        recent_points = data_points[-3:] if len(data_points) > 3 else data_points
                        text += "    * 最近数据点:\n"
                        for point in recent_points:
                            timestamp = point["timestamp"]
                            value = point["value"]
                            text += f"      - {timestamp}: {value}\n"
                    else:
                        text += f"  - 指标: {metric_name} (无有效数据)\n"
                else:
                    text += f"  - 指标: {metric_name} (无数据)\n"
                    
            text += "\n"
            
        return text
        
    def _format_hybrid_results(self, result: Dict[str, Any]) -> str:
        """格式化混合查询结果为文本上下文"""
        if not result.get("success", False):
            return f"查询失败: {result.get('error', '未知错误')}"
            
        records = result.get("records", [])
        if not records:
            return "查询成功，但未找到匹配的数据。"
            
        # 获取元数据
        graph_metadata = result.get("graph_metadata", {})
        time_series_metadata = result.get("time_series_metadata", {})
        
        text = f"混合查询结果 ({len(records)} 条记录):\n\n"
        
        for i, record in enumerate(records, 1):
            text += f"记录 {i}:\n"
            
            for field_name, value in record.items():
                # 处理节点
                if isinstance(value, dict) and "_labels" in value:
                    labels = value.get("_labels", [])
                    text += f"  - {field_name} (类型: {', '.join(labels)}):\n"
                    
                    # 添加节点属性
                    for attr, attr_value in value.items():
                        if attr == "metrics":
                            # 处理指标数据
                            text += f"    * 指标数据:\n"
                            for metric_name, data_points in attr_value.items():
                                if data_points:
                                    values = [dp["value"] for dp in data_points if dp["value"] is not None]
                                    if values:
                                        avg_value = sum(values) / len(values)
                                        max_value = max(values)
                                        min_value = min(values)
                                        
                                        text += f"      - {metric_name}:\n"
                                        text += f"        * 平均值: {avg_value:.2f}\n"
                                        text += f"        * 最大值: {max_value:.2f}\n"
                                        text += f"        * 最小值: {min_value:.2f}\n"
                        elif not attr.startswith("_"):
                            text += f"    * {attr}: {attr_value}\n"
                # 处理基本值
                else:
                    text += f"  - {field_name}: {value}\n"
            text += "\n"
            
        return text 