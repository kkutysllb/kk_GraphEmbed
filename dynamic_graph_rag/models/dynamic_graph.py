"""
动态图模型模块
集成图数据和时序数据，提供动态图的查询和分析功能
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

from .graph_data import GraphData
from ..db.influxdb_client import InfluxDBClient
from ..config.settings import NODE_TYPES, INFLUXDB_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DynamicGraph:
    """动态图模型类，集成图数据和时序数据的查询分析"""
    
    def __init__(self, graph_data=None, influxdb_client=None):
        """初始化动态图实例
        
        Args:
            graph_data: 可选的GraphData实例
            influxdb_client: 可选的InfluxDB客户端实例
        """
        # 初始化图数据组件
        self.graph = graph_data or GraphData()
        
        # 初始化时序数据组件
        self.influxdb = influxdb_client or InfluxDBClient(
            url=INFLUXDB_CONFIG["url"],
            token=INFLUXDB_CONFIG["token"],
            org=INFLUXDB_CONFIG["org"],
            bucket=INFLUXDB_CONFIG["bucket"]
        )
        
        # 设置日志级别
        self.logger = logging.getLogger(__name__)
    
    def get_node_with_metrics(self, node_id: str, start_time: str = None, 
                             end_time: str = None) -> Dict:
        """获取节点及其时序指标数据
        
        Args:
            node_id: 节点ID
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            包含节点属性和时序数据的字典
        """
        # 获取节点基本信息
        node = self.graph.get_node_by_id(node_id)
        if not node:
            logger.warning(f"找不到节点: {node_id}")
            return {}
            
        # 获取节点类型
        node_type = node.get('type')
        if not node_type:
            logger.warning(f"节点 {node_id} 没有类型信息")
            return node
            
        # 获取指标数据
        metrics = self.influxdb.query_metrics(
            node_id=node_id,
            node_type=node_type,
            start_time=start_time,
            end_time=end_time
        )
        
        # 构建结果
        result = dict(node)
        result['metrics'] = metrics
        
        return result
    
    def get_subgraph_with_metrics(self, center_node_id: str, depth: int = 1, 
                                start_time: str = None, end_time: str = None) -> Dict:
        """获取带有指标数据的子图
        
        Args:
            center_node_id: 中心节点ID
            depth: 遍历深度
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            包含子图和指标数据的字典
        """
        # 获取子图
        subgraph = self.graph.find_subgraph(center_node_id, depth)
        if not subgraph:
            logger.warning(f"找不到以 {center_node_id} 为中心的子图")
            return {}
            
        # 为每个节点添加指标数据
        nodes_with_metrics = []
        for node in subgraph['nodes']:
            node_id = node.get('id')
            node_type = node.get('type')
            
            if node_id and node_type and node_type.upper() in NODE_TYPES:
                # 获取该节点的指标数据
                metrics = self.influxdb.query_metrics(
                    node_id=node_id,
                    node_type=node_type,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # 复制节点属性并添加指标数据
                node_with_metrics = dict(node)
                node_with_metrics['metrics'] = metrics
                nodes_with_metrics.append(node_with_metrics)
            else:
                # 对于没有时序数据的节点，直接添加
                node_with_metrics = dict(node)
                node_with_metrics['metrics'] = []
                nodes_with_metrics.append(node_with_metrics)
        
        # 构建结果
        result = {
            'nodes': nodes_with_metrics,
            'relationships': subgraph['relationships']
        }
        
        return result
    
    def find_anomalous_nodes(self, node_type: str, metric: str, threshold: float = 2.0, 
                            window: str = "1h") -> List[Dict]:
        """查找具有异常指标的节点
        
        Args:
            node_type: 节点类型
            metric: 指标名称
            threshold: 异常阈值（标准差的倍数）
            window: 时间窗口
            
        Returns:
            异常节点列表
        """
        # 获取特定类型的所有节点
        nodes = self.graph.get_nodes_by_type(node_type)
        if not nodes:
            logger.warning(f"找不到类型为 {node_type} 的节点")
            return []
            
        anomalous_nodes = []
        for node in nodes:
            node_id = node.get('id')
            if not node_id:
                continue
                
            # 检测异常
            anomalies = self.influxdb.detect_anomalies(
                node_id=node_id,
                node_type=node_type,
                metric=metric,
                threshold=threshold,
                window=window
            )
            
            if anomalies:
                # 复制节点属性并添加异常信息
                node_with_anomalies = dict(node)
                node_with_anomalies['anomalies'] = anomalies
                anomalous_nodes.append(node_with_anomalies)
                
        return anomalous_nodes
    
    def get_node_history(self, node_id: str, node_type: str, metrics: List[str] = None, 
                        interval: str = "5m", start_time: str = None, 
                        end_time: str = None) -> Dict:
        """获取节点的历史指标数据
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            metrics: 指标列表，如果为None则获取所有指标
            interval: 重采样间隔
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            包含节点历史数据的字典
        """
        # 获取节点基本信息
        node = self.graph.get_node_by_id(node_id)
        if not node:
            logger.warning(f"找不到节点: {node_id}")
            return {}
            
        # 获取历史指标数据
        history = self.influxdb.query_metrics(
            node_id=node_id,
            node_type=node_type,
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        
        # 构建结果
        result = dict(node)
        result['history'] = history
        
        return result
    
    def find_related_anomalies(self, node_id: str, relationship_type: str = None, 
                             direction: str = "both", metric: str = None, 
                             threshold: float = 2.0, window: str = "1h") -> List[Dict]:
        """查找与节点相关的异常
        
        Args:
            node_id: 节点ID
            relationship_type: 关系类型
            direction: 关系方向
            metric: 指标名称
            threshold: 异常阈值
            window: 时间窗口
            
        Returns:
            相关异常节点列表
        """
        # 获取相关节点
        related_nodes = self.graph.get_connected_nodes(node_id, relationship_type, direction)
        if not related_nodes:
            logger.warning(f"找不到与节点 {node_id} 相关的节点")
            return []
            
        anomalous_nodes = []
        for related_node in related_nodes:
            related_id = related_node.get('id')
            related_type = related_node.get('type')
            
            if not related_id or not related_type or related_type.upper() not in NODE_TYPES:
                continue
                
            # 检测异常
            anomalies = self.influxdb.detect_anomalies(
                node_id=related_id,
                node_type=related_type,
                metric=metric,
                threshold=threshold,
                window=window
            )
            
            if anomalies:
                # 复制节点属性并添加异常信息
                node_with_anomalies = dict(related_node)
                node_with_anomalies['anomalies'] = anomalies
                anomalous_nodes.append(node_with_anomalies)
                
        return anomalous_nodes
    
    def analyze_impact_propagation(self, anomalous_node_id: str, 
                                 max_depth: int = 3) -> Dict:
        """分析异常影响传播
        
        Args:
            anomalous_node_id: 异常节点ID
            max_depth: 最大传播深度
            
        Returns:
            影响传播分析结果
        """
        # 获取节点信息
        anomalous_node = self.graph.get_node_by_id(anomalous_node_id)
        if not anomalous_node:
            logger.warning(f"找不到节点: {anomalous_node_id}")
            return {}
            
        # 获取下游节点
        descendants = self.graph.get_node_descendants(anomalous_node_id, max_depth=max_depth)
        if not descendants:
            logger.info(f"节点 {anomalous_node_id} 没有下游节点")
            return {
                'source': anomalous_node,
                'impacted_nodes': [],
                'propagation_paths': []
            }
            
        # 分析每个下游节点
        impacted_nodes = []
        for descendant in descendants:
            descendant_id = descendant.get('id')
            descendant_type = descendant.get('type')
            
            if not descendant_id or not descendant_type:
                continue
                
            # 获取从异常节点到该节点的路径
            paths = self.graph.get_path_between_nodes(anomalous_node_id, descendant_id, max_depth)
            
            # 添加到受影响节点列表
            impacted_node = dict(descendant)
            impacted_node['paths_from_source'] = len(paths)
            impacted_nodes.append(impacted_node)
            
        # 获取传播路径
        propagation_paths = []
        for descendant in descendants:
            descendant_id = descendant.get('id')
            if not descendant_id:
                continue
                
            paths = self.graph.get_path_between_nodes(anomalous_node_id, descendant_id, max_depth)
            propagation_paths.extend(paths)
            
        result = {
            'source': anomalous_node,
            'impacted_nodes': impacted_nodes,
            'propagation_paths': propagation_paths
        }
        
        return result
    
    def correlate_metrics(self, node_id: str, related_node_id: str, 
                        metrics: List[Tuple[str, str]], start_time: str = None, 
                        end_time: str = None) -> Dict:
        """关联两个节点的指标
        
        Args:
            node_id: 第一个节点ID
            related_node_id: 第二个节点ID
            metrics: 要关联的指标对列表，每个元组包含 (metric1, metric2)
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            关联分析结果
        """
        # 获取两个节点
        node1 = self.graph.get_node_by_id(node_id)
        node2 = self.graph.get_node_by_id(related_node_id)
        
        if not node1 or not node2:
            logger.warning("找不到指定的节点")
            return {}
            
        node1_type = node1.get('type')
        node2_type = node2.get('type')
        
        if not node1_type or not node2_type:
            logger.warning("节点缺少类型信息")
            return {}
            
        # 获取两个节点的指标数据
        df1 = self.influxdb.query_metrics(
            node_id=node_id,
            node_type=node1_type,
            metrics=[m for m, _ in metrics],
            start_time=start_time,
            end_time=end_time
        )
        df2 = self.influxdb.query_metrics(
            node_id=related_node_id,
            node_type=node2_type,
            metrics=[m for _, m in metrics],
            start_time=start_time,
            end_time=end_time
        )
        
        if df1.empty or df2.empty:
            logger.warning("缺少指标数据")
            return {
                'node1': node1,
                'node2': node2,
                'correlations': []
            }
            
        # 重设索引以便合并
        df1 = df1.reset_index()
        df2 = df2.reset_index()
        
        # 合并数据框，按时间戳对齐
        merged = pd.merge(df1, df2, on='timestamp', suffixes=('_1', '_2'))
        
        correlations = []
        for metric1, metric2 in metrics:
            col1 = f"{metric1}_1" if f"{metric1}_1" in merged.columns else metric1
            col2 = f"{metric2}_2" if f"{metric2}_2" in merged.columns else metric2
            
            if col1 not in merged.columns or col2 not in merged.columns:
                logger.warning(f"找不到指标: {col1} 或 {col2}")
                continue
                
            # 计算相关系数
            corr = merged[col1].corr(merged[col2])
            
            correlations.append({
                'metric1': metric1,
                'metric2': metric2,
                'correlation': corr,
                'samples': len(merged)
            })
            
        result = {
            'node1': node1,
            'node2': node2,
            'correlations': correlations
        }
        
        return result
    
    def find_resource_bottlenecks(self, node_type: str, metric: str, 
                                threshold: float, limit: int = 10) -> List[Dict]:
        """查找资源瓶颈
        
        Args:
            node_type: 节点类型
            metric: 指标名称
            threshold: 阈值
            limit: 结果数量限制
            
        Returns:
            瓶颈节点列表
        """
        # 获取特定类型的所有节点
        nodes = self.graph.get_nodes_by_type(node_type)
        if not nodes:
            logger.warning(f"找不到类型为 {node_type} 的节点")
            return []
            
        bottleneck_nodes = []
        for node in nodes:
            node_id = node.get('id')
            if not node_id:
                continue
                
            # 获取最近的指标数据
            recent_metrics = self.influxdb.query_metrics(
                node_id=node_id,
                node_type=node_type,
                metrics=[metric],
                limit=1
            )
            if recent_metrics.empty or metric not in recent_metrics.columns:
                continue
                
            # 检查是否超过阈值
            value = recent_metrics[metric].iloc[0]
            if value > threshold:
                # 复制节点属性
                bottleneck_node = dict(node)
                # 添加指标信息
                bottleneck_node['metric'] = metric
                bottleneck_node['value'] = value
                bottleneck_node['threshold'] = threshold
                bottleneck_nodes.append(bottleneck_node)
                
        # 按指标值排序
        bottleneck_nodes.sort(key=lambda x: x['value'], reverse=True)
        
        # 限制结果数量
        return bottleneck_nodes[:limit]
    
    def get_health_status(self, node_id: str = None, node_type: str = None, 
                        include_metrics: bool = True) -> Dict:
        """获取节点或节点类型的健康状态
        
        Args:
            node_id: 节点ID，如果为None则检查node_type的所有节点
            node_type: 节点类型
            include_metrics: 是否包含指标数据
            
        Returns:
            健康状态信息
        """
        if node_id:
            # 获取单个节点的健康状态
            node = self.graph.get_node_by_id(node_id)
            if not node:
                logger.warning(f"找不到节点: {node_id}")
                return {}
                
            node_type = node.get('type')
            if not node_type or node_type.upper() not in NODE_TYPES:
                logger.warning(f"节点 {node_id} 没有有效的类型信息")
                return node
                
            # 获取节点的指标数据
            health_status = dict(node)
            
            if include_metrics:
                recent_metrics = self.influxdb.query_metrics(
                    node_id=node_id,
                    node_type=node_type,
                    limit=1
                )
                if not recent_metrics.empty:
                    # 提取最新的指标值
                    metrics = recent_metrics.iloc[0].to_dict()
                    health_status['current_metrics'] = metrics
                    
                    # 检查是否有异常
                    for metric in NODE_TYPES[node_type.upper()]["metrics"]:
                        if metric in recent_metrics.columns:
                            anomalies = self.influxdb.detect_anomalies(
                                node_id=node_id,
                                node_type=node_type,
                                metric=metric
                            )
                            if anomalies:
                                if 'anomalies' not in health_status:
                                    health_status['anomalies'] = {}
                                health_status['anomalies'][metric] = anomalies
            
            return health_status
        elif node_type:
            # 获取节点类型的整体健康状态
            if node_type.upper() not in NODE_TYPES:
                logger.warning(f"未知的节点类型: {node_type}")
                return {}
                
            # 获取该类型的所有节点
            nodes = self.graph.get_nodes_by_type(node_type)
            if not nodes:
                logger.warning(f"找不到类型为 {node_type} 的节点")
                return {
                    'type': node_type,
                    'count': 0,
                    'nodes': []
                }
                
            # 检查每个节点的健康状态
            nodes_health = []
            anomalous_count = 0
            
            for node in nodes:
                node_id = node.get('id')
                if not node_id:
                    continue
                    
                node_health = {'id': node_id}
                
                if include_metrics:
                    has_anomaly = False
                    for metric in NODE_TYPES[node_type.upper()]["metrics"]:
                        anomalies = self.influxdb.detect_anomalies(
                            node_id=node_id,
                            node_type=node_type,
                            metric=metric
                        )
                        if anomalies:
                            has_anomaly = True
                            if 'anomalies' not in node_health:
                                node_health['anomalies'] = {}
                            node_health['anomalies'][metric] = len(anomalies)
                            
                    if has_anomaly:
                        anomalous_count += 1
                        node_health['status'] = 'anomalous'
                    else:
                        node_health['status'] = 'normal'
                
                nodes_health.append(node_health)
                
            overall_health = {
                'type': node_type,
                'count': len(nodes),
                'anomalous_count': anomalous_count,
                'normal_count': len(nodes) - anomalous_count,
                'nodes': nodes_health
            }
            
            return overall_health
        else:
            logger.error("必须提供node_id或node_type")
            return {}
    
    def get_metric_trend(self, node_id: str, metric: str, window: str = "7d") -> Dict:
        """获取节点指标的趋势分析
        
        Args:
            node_id: 节点ID
            metric: 指标名称
            window: 分析时间窗口
            
        Returns:
            趋势分析结果字典
        """
        # 获取节点信息
        node = self.graph.get_node_by_id(node_id)
        if not node:
            logger.warning(f"找不到节点: {node_id}")
            return {
                "status": "error",
                "message": f"找不到节点: {node_id}"
            }
            
        # 获取节点类型
        node_type = node.get('type')
        if not node_type or node_type.upper() not in NODE_TYPES:
            logger.warning(f"节点 {node_id} 没有有效的类型信息")
            return {
                "status": "error",
                "message": f"节点类型无效: {node_type}"
            }
            
        # 获取趋势分析
        trend_analysis = self.influxdb.analyze_trend(
            node_id=node_id,
            node_type=node_type,
            metric=metric,
            window=window
        )
        
        # 如果分析成功，添加节点信息
        if trend_analysis.get("status") == "success":
            trend_analysis["node"] = {
                "id": node_id,
                "type": node_type,
                "level": node.get("level"),
                "properties": {k: v for k, v in node.items() if k not in ['id', 'type', 'level']}
            }
            
        return trend_analysis
    
    def predict_node_metrics(self, node_id: str, metric: str, 
                          prediction_horizon: str = "24h", 
                          history_window: str = "7d") -> Dict:
        """预测节点的未来指标值
        
        Args:
            node_id: 节点ID
            metric: 指标名称
            prediction_horizon: 预测时间范围
            history_window: 历史数据窗口
            
        Returns:
            预测结果字典
        """
        # 获取节点信息
        node = self.graph.get_node_by_id(node_id)
        if not node:
            logger.warning(f"找不到节点: {node_id}")
            return {
                "status": "error",
                "message": f"找不到节点: {node_id}"
            }
            
        # 获取节点类型
        node_type = node.get('type')
        if not node_type or node_type.upper() not in NODE_TYPES:
            logger.warning(f"节点 {node_id} 没有有效的类型信息")
            return {
                "status": "error",
                "message": f"节点类型无效: {node_type}"
            }
            
        # 获取预测结果
        prediction = self.influxdb.predict_metrics(
            node_id=node_id,
            node_type=node_type,
            metric=metric,
            prediction_horizon=prediction_horizon,
            history_window=history_window
        )
        
        # 如果预测成功，添加节点信息
        if prediction.get("status") == "success":
            prediction["node"] = {
                "id": node_id,
                "type": node_type,
                "level": node.get("level"),
                "properties": {k: v for k, v in node.items() if k not in ['id', 'type', 'level']}
            }
            
            # 获取相关节点，了解潜在影响
            related_nodes = []
            relations = self.graph.get_node_relationships(node_id, direction="both")
            
            for relation in relations:
                related_id = relation.get("other_id")
                if related_id:
                    related_node = self.graph.get_node_by_id(related_id)
                    if related_node:
                        related_nodes.append({
                            "id": related_id,
                            "type": related_node.get("type"),
                            "relation": relation.get("rel_type")
                        })
            
            prediction["related_nodes"] = related_nodes
            
            # 如果有异常预测值，分析可能的影响传播
            predicted_values = [p["predicted_value"] for p in prediction["predictions"]]
            current_stats = self.influxdb.get_metric_statistics(node_type, metric, f"-{history_window}")
            
            if current_stats and "mean" in current_stats and "stddev" in current_stats:
                mean = current_stats["mean"]
                stddev = current_stats["stddev"] or 0.1
                
                # 检查是否有预测值超出正常范围(均值±2个标准差)
                anomaly_threshold = 2.0
                upper_limit = mean + (anomaly_threshold * stddev)
                lower_limit = mean - (anomaly_threshold * stddev)
                
                potential_anomalies = [p for p in prediction["predictions"] 
                                    if p["predicted_value"] > upper_limit or p["predicted_value"] < lower_limit]
                
                if potential_anomalies:
                    # 如果有潜在异常，分析可能的影响
                    prediction["potential_anomalies"] = potential_anomalies
                    prediction["impact_analysis"] = {
                        "threshold": anomaly_threshold,
                        "upper_limit": upper_limit,
                        "lower_limit": lower_limit,
                        "affected_nodes": self.find_related_anomalies(node_id, metric=metric)
                    }
        
        return prediction
    
    def compare_node_trends(self, node_ids: List[str], metric: str, window: str = "7d") -> Dict:
        """比较多个节点的指标趋势
        
        Args:
            node_ids: 节点ID列表
            metric: 指标名称
            window: 分析时间窗口
            
        Returns:
            比较结果字典
        """
        results = {}
        for node_id in node_ids:
            results[node_id] = self.get_metric_trend(node_id, metric, window)
            
        # 比较结果分析
        valid_results = {k: v for k, v in results.items() if v.get("status") == "success"}
        
        if not valid_results:
            return {
                "status": "error",
                "message": "没有有效的节点趋势数据进行比较"
            }
            
        # 提取趋势信息进行比较
        trends = {k: v.get("trend") for k, v in valid_results.items()}
        strengths = {k: v.get("strength") for k, v in valid_results.items()}
        slopes = {k: v.get("slope") for k, v in valid_results.items()}
        r_squared = {k: v.get("r_squared") for k, v in valid_results.items()}
        
        # 计算整体趋势一致性
        unique_trends = set(trends.values())
        if len(unique_trends) == 1:
            trend_consistency = "high"
        elif len(unique_trends) == 2:
            trend_consistency = "medium"
        else:
            trend_consistency = "low"
            
        # 找出变化最大的节点
        max_change_node = max(valid_results.items(), key=lambda x: abs(x[1].get("relative_change", 0)))
        min_change_node = min(valid_results.items(), key=lambda x: abs(x[1].get("relative_change", 0)))
        
        return {
            "status": "success",
            "node_count": len(valid_results),
            "results": results,
            "trend_consistency": trend_consistency,
            "unique_trends": list(unique_trends),
            "max_change_node": max_change_node[0],
            "min_change_node": min_change_node[0],
            "comparative_analysis": {
                "trends": trends,
                "strengths": strengths,
                "slopes": {k: float(v) for k, v in slopes.items() if v is not None}
            }
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，确保资源释放"""
        pass 