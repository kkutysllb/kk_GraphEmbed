#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
时序数据生成器模块
生成用于测试和开发的模拟时序数据
"""

import os
import sys
import logging
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from influxdb_client import Point
import time
import threading
from queue import Queue, Empty
import random

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from dynamic_graph_rag.config.settings import NODE_TYPES, INFLUXDB_CONFIG, GRAPH_DB_CONFIG
from dynamic_graph_rag.db.neo4j_connector import Neo4jConnector
from dynamic_graph_rag.db.influxdb_client import InfluxDBManager
from .log_generator import LogGenerator


logger = logging.getLogger('time_series_generator')

class TimeSeriesGenerator:
    """时序数据生成器，用于生成模拟的时序数据"""
    
    def __init__(self, nodes_info: Optional[List[Dict]] = None):
        """
        初始化时序数据生成器
        
        Args:
            nodes_info: 可选的节点信息列表，包含节点ID和类型
        """
        self.nodes_info = nodes_info or []
        
        # 配置节点类型的指标定义
        self._init_metrics_config()
        
        # 采样间隔配置（分钟）
        self.sample_intervals = {
            'VM': 15,
            'HOST': 15,
            'NE': 15,
            'HOSTGROUP': 15,
            'TRU': 15
        }
        
        # 尝试连接到InfluxDB和Neo4j（可能会失败，但不影响其他功能）
        self.influxdb_client = None
        self.neo4j_connector = None
        try:
            self.influxdb_client = InfluxDBManager(
                url=INFLUXDB_CONFIG["url"],
                token=INFLUXDB_CONFIG["token"],
                org=INFLUXDB_CONFIG["org"],
                bucket=INFLUXDB_CONFIG["bucket"]
            )
            # 注意：这里只创建客户端对象，不实际连接
            # 实际连接会在导入数据时进行
            self.influxdb_available = True
        except Exception as e:
            logger.warning(f"无法初始化InfluxDB客户端: {str(e)}")
            self.influxdb_available = False
        
        try:
            self.neo4j_connector = Neo4jConnector(
                uri=GRAPH_DB_CONFIG["uri"],
                user=GRAPH_DB_CONFIG["user"],
                password=GRAPH_DB_CONFIG["password"]
            )
            self.neo4j_available = True
        except Exception as e:
            logger.warning(f"无法初始化Neo4j连接器: {str(e)}")
            self.neo4j_available = False

    def _init_metrics_config(self):
        """初始化各节点类型的指标定义"""
        self.metrics_config = {
            'VM': {
                'cpu_usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'medium'},
                'memory_usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'low'},
                'disk_io': {'min': 0, 'max': 10000, 'unit': 'IOPS', 'volatility': 'high'},
                'network_throughput': {'min': 0, 'max': 10000, 'unit': 'Mbps', 'volatility': 'high'}
            },
            'HOST': {
                'cpu_usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'medium'},
                'memory_usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'low'},
                'disk_usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'low'},
                'temperature': {'min': 20, 'max': 90, 'unit': '°C', 'volatility': 'low'}
            },
            'NE': {
                'load': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'medium'},
                'response_time': {'min': 0, 'max': 1000, 'unit': 'ms', 'volatility': 'high'},
                'success_rate': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'low'},
                'resource_usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'medium'}
            },
            'HOSTGROUP': {
                'aggregate_cpu': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'medium'},
                'aggregate_memory': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'low'},
                'load_balance': {'min': 0, 'max': 1, 'unit': 'ratio', 'volatility': 'medium'}
            },
            'TRU': {
                'usage': {'min': 0, 'max': 100, 'unit': '%', 'volatility': 'low'},
                'iops': {'min': 0, 'max': 50000, 'unit': 'IOPS', 'volatility': 'high'},
                'latency': {'min': 0, 'max': 100, 'unit': 'ms', 'volatility': 'medium'},
                'read_write_ratio': {'min': 0, 'max': 1, 'unit': 'ratio', 'volatility': 'medium'}
            }
        }
        
        # 采样间隔和保留策略
        self.sampling_intervals = {
            'VM': '15m',
            'HOST': '15m',
            'NE': '15m',
            'TRU': '15m',
            'HOSTGROUP': '15m'
        }
    
    def load_nodes_from_neo4j(self, node_types: Optional[List[str]] = None) -> List[Dict]:
        """
        从Neo4j数据库加载节点信息
        
        Args:
            node_types: 可选的要加载的节点类型列表
            
        Returns:
            包含节点信息的字典列表
        """
        logger.info("从Neo4j加载节点信息...")
        
        # 如果未指定节点类型，则加载所有类型
        if node_types is None:
            node_types = NODE_TYPES
        
        loaded_nodes = []
        failed_types = []
        
        # 检查Neo4j是否可用
        if not self.neo4j_available:
            logger.error("Neo4j连接器不可用，无法加载节点")
            return []
        
        try:
            # 对每个节点类型执行查询
            for node_type in node_types:
                try:
                    # 查询Neo4j获取指定类型的节点
                    with self.neo4j_connector.driver.session() as session:
                        result = session.run(f"""
                            MATCH (n:{node_type})
                            RETURN n.id as id, '{node_type}' as type, 
                                   COALESCE(n.name, n.id) as name
                        """)
                        
                        count = 0
                        for record in result:
                            node_info = {
                                'id': record['id'],
                                'type': record['type'],
                                'name': record['name']
                            }
                            loaded_nodes.append(node_info)
                            count += 1
                        
                        logger.info(f"已加载 {count} 个 {node_type} 类型的节点")
                    
                except Exception as e:
                    logger.error(f"加载 {node_type} 类型节点失败: {str(e)}")
                    failed_types.append(node_type)
            
            # 保存加载的节点
            self.nodes_info = loaded_nodes
            
            # 日志输出
            if loaded_nodes:
                logger.info(f"共加载了 {len(loaded_nodes)} 个节点")
            else:
                logger.warning("未加载任何节点")
                
            if failed_types:
                logger.warning(f"以下节点类型加载失败: {', '.join(failed_types)}")
            
        except Exception as e:
            logger.error(f"从Neo4j加载节点时出错: {str(e)}")
        
        return loaded_nodes
    
    def generate_periodic_pattern(self, 
                                 base_value: float, 
                                 volatility: str,
                                 time_range: pd.DatetimeIndex,
                                 daily_pattern: bool = True,
                                 weekly_pattern: bool = False) -> np.ndarray:
        """
        生成带有周期性模式的数据
        
        Args:
            base_value: 基础值
            volatility: 波动性 ('low', 'medium', 'high')
            time_range: 时间范围
            daily_pattern: 是否包含日变化模式
            weekly_pattern: 是否包含周变化模式
            
        Returns:
            包含周期性模式的数值数组
        """
        # 根据波动性设置标准差
        volatility_factors = {
            'low': 0.05,
            'medium': 0.15,
            'high': 0.3
        }
        std_dev = base_value * volatility_factors.get(volatility, 0.1)
        
        # 创建基础随机数据
        values = np.random.normal(base_value, std_dev, len(time_range))
        
        # 添加日变化模式
        if daily_pattern:
            # 创建基于一天24小时的周期性变化
            hours = np.array([t.hour for t in time_range])
            # 工作时间（8-18点）负载较高
            daily_pattern = np.sin(hours * (2 * np.pi / 24) - np.pi/2) * 0.2 + 0.1
            values += base_value * daily_pattern
            
        # 添加周变化模式
        if weekly_pattern:
            # 创建基于一周7天的周期性变化
            days = np.array([t.dayofweek for t in time_range])
            # 工作日（0-4）负载较高，周末（5-6）负载较低
            weekly_factor = np.where(days < 5, 0.1, -0.1)
            values += base_value * weekly_factor
            
        # 确保值不为负
        values = np.maximum(values, 0)
        
        return values
    
    def add_anomalies(self, 
                     values: np.ndarray, 
                     anomaly_probability: float = 0.05,
                     anomaly_severity: str = 'medium',
                     anomaly_duration: int = 5) -> np.ndarray:
        """
        在时序数据中添加异常点
        
        Args:
            values: 原始数值数组
            anomaly_probability: 异常发生的概率
            anomaly_severity: 异常严重程度 ('low', 'medium', 'high')
            anomaly_duration: 异常持续的数据点数量
            
        Returns:
            添加异常后的数值数组
        """
        # 复制原始数组
        result = values.copy()
        
        # 设置异常严重程度
        severity_factors = {
            'low': 1.5,
            'medium': 2.5,
            'high': 4.0
        }
        factor = severity_factors.get(anomaly_severity, 2.0)
        
        # 随机选择异常发生的起始位置
        if len(values) <= anomaly_duration:
            return result
            
        anomaly_candidates = np.random.random(len(values) - anomaly_duration)
        anomaly_starts = np.where(anomaly_candidates < anomaly_probability)[0]
        
        # 添加异常值
        for start in anomaly_starts:
            # 50%概率为突增，50%概率为突降
            if np.random.random() > 0.5:
                # 突增
                result[start:start+anomaly_duration] *= factor
            else:
                # 突降
                result[start:start+anomaly_duration] /= factor
                
        return result
    
    def generate_metrics_for_node(self, 
                                 node_info: Dict, 
                                 start_time: datetime,
                                 end_time: datetime,
                                 include_anomalies: bool = True) -> Dict[str, pd.DataFrame]:
        """
        为单个节点生成指标数据
        
        Args:
            node_info: 节点信息，包含id, type
            start_time: 开始时间
            end_time: 结束时间
            include_anomalies: 是否包含异常值
            
        Returns:
            包含各指标时序数据的字典，格式为 {metric_name: DataFrame}
        """
        node_id = node_info['id']
        node_type = node_info['type']
        
        # DC和TENANT类型节点不需要生成指标
        if node_type in ['DC', 'TENANT']:
            return {}
        
        # 获取该节点类型的指标定义
        metrics = self.metrics_config.get(node_type)
        if not metrics:
            logger.warning(f"未找到节点类型 {node_type} 的指标定义")
            return {}
        
        # 获取采样间隔
        interval_minutes = self.sample_intervals.get(node_type, 1)
        
        # 创建时间点列表
        time_range = pd.date_range(
            start=start_time, 
            end=end_time, 
            freq=f'{interval_minutes}min'
        )
        
        # 为每个指标生成数据
        results = {}
        for metric_name, metric_config in metrics.items():
            # 设置基础值和波动性
            base_value = (metric_config['min'] + metric_config['max']) / 2
            volatility = metric_config.get('volatility', 'medium')
            
            # 生成基本的时序模式
            values = self.generate_periodic_pattern(
                base_value=base_value,
                volatility=volatility,
                time_range=time_range,
                daily_pattern=True,
                weekly_pattern=True
            )
            
            # 添加异常值
            if include_anomalies:
                values = self.add_anomalies(values, anomaly_probability=0.05)
            
            # 确保值在有效范围内
            values = np.clip(values, metric_config['min'], metric_config['max'])
            
            # 创建DataFrame
            df = pd.DataFrame({
                'timestamp': time_range,
                'value': values,
                'node_id': node_id,
                'node_type': node_type,
                'unit': metric_config['unit']
            })
            
            results[metric_name] = df
        
        return results
    
    def generate_metrics_data(self, 
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None,
                            include_anomalies: bool = True) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        为所有加载的节点生成时序数据
        
        Args:
            start_time: 开始时间，默认为当前时间前30天
            end_time: 结束时间，默认为当前时间
            include_anomalies: 是否包含异常数据
            
        Returns:
            包含所有节点的时序数据的嵌套字典
        """
        if not self.nodes_info:
            logger.warning("未加载节点信息，无法生成时序数据")
            return {}
            
        # 设置默认时间范围
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=30)
            
        logger.info(f"生成时序数据，时间范围: {start_time} 到 {end_time}")
        
        # 为每个节点生成指标数据
        all_metrics = {}
        for node_info in self.nodes_info:
            node_id = node_info['id']
            node_metrics = self.generate_metrics_for_node(
                node_info=node_info,
                start_time=start_time,
                end_time=end_time,
                include_anomalies=include_anomalies
            )
            all_metrics[node_id] = node_metrics
            
        return all_metrics
    
    def export_to_csv(self, metrics_data: Dict, output_dir: str) -> List[str]:
        """
        将生成的时序数据导出为CSV文件
        
        Args:
            metrics_data: 生成的时序数据
            output_dir: 输出目录
            
        Returns:
            生成的CSV文件路径列表
        """
        if not metrics_data:
            logger.warning("没有数据可导出")
            return []
            
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        generated_files = []
        for node_id, node_metrics in metrics_data.items():
            for metric_name, df in node_metrics.items():
                # 创建文件名
                file_name = f"{node_id}_{metric_name}.csv"
                file_path = os.path.join(output_dir, file_name)
                
                # 导出为CSV
                df.to_csv(file_path, index=False)
                generated_files.append(file_path)
                
                logger.info(f"已导出 {file_path}")
                
        return generated_files
    
    def import_to_influxdb(self, metrics_data: Dict) -> int:
        """将生成的指标数据导入到InfluxDB
        
        Args:
            metrics_data: 生成的指标数据，格式为 {node_id: {metric_name: DataFrame}}
            
        Returns:
            成功导入的数据点数量
        """
        if not metrics_data:
            logger.warning("没有数据可导入InfluxDB")
            return 0
        
        # 检查InfluxDB是否可用
        if not self.influxdb_available or self.influxdb_client is None:
            logger.warning("InfluxDB不可用，跳过导入")
            return 0
        
        # 连接到InfluxDB
        # 不提前关闭连接，这可能导致之后的所有操作失败
        if not self.influxdb_client.connect():
            logger.error("无法连接到InfluxDB，跳过导入")
            return 0
        
        # 获取配置的超时值，用于日志显示
        config = INFLUXDB_CONFIG
        timeout_ms = config.get("timeout", 60000)
        logger.info(f"开始导入数据到InfluxDB - 连接成功 - 地址: {config['url']}, 桶: {config['bucket']}, 超时: {timeout_ms}ms")
        
        # 计算总数据点
        total_points = sum(sum(len(df) for df in node_metrics.values()) for node_metrics in metrics_data.values())
        logger.info(f"总计准备导入 {total_points} 个数据点，共 {len(metrics_data)} 个节点")
        
        # 准备存储所有数据点的列表
        all_points = []
        
        # 1. 准备数据点
        logger.info("正在准备数据点...")
        for node_id, metrics in metrics_data.items():
            for metric_name, df in metrics.items():
                if df.empty or not all(col in df.columns for col in ['timestamp', 'value', 'node_type']):
                    continue
                    
                # 将数据转换为适合导入的格式
                ts_df = df.copy()
                ts_df['node_id'] = node_id
                ts_df['metric'] = metric_name
                
                # 生成Point对象
                for _, row in ts_df.iterrows():
                    measurement = f"{row['node_type'].lower()}_metrics"
                    
                    # 创建Point对象
                    point = Point(measurement)
                    point = point.tag("node_id", row['node_id'])
                    point = point.tag("node_type", row['node_type'])
                    point = point.tag("metric", row['metric'])
                    point = point.field("value", float(row['value']))
                    if 'unit' in row:
                        point = point.field("unit", row['unit'])
                    point = point.time(row['timestamp'])
                    
                    all_points.append(point)
                    
                # 每100万点进度报告
                if len(all_points) % 1000000 == 0:
                    logger.info(f"已准备 {len(all_points):,}/{total_points:,} 个数据点 ({len(all_points)/total_points*100:.1f}%)")
        
        logger.info(f"数据点准备完成，共 {len(all_points):,} 个点")
        
        # 2. 使用优化的批处理模式导入数据
        
        # 导入配置 - 优化批次大小
        batch_size = 5000  # 增加到5000个点每批次
        max_workers = min(8, os.cpu_count())  # 适当减少线程数，降低资源竞争
        max_retries = 3  # 每个批次最大重试次数
        retry_delay = 5  # 重试延迟（秒）
        
        # 任务队列和结果
        task_queue = Queue(maxsize=max_workers * 2)  # 降低队列最大长度，减少内存占用
        result_lock = threading.Lock()  # 保护共享变量的锁
        success_count = 0  # 成功导入的数据点
        failed_count = 0  # 失败的数据点
        in_progress = 0  # 正在处理的任务数
        
        # 分割数据点为批次
        batches = []
        for i in range(0, len(all_points), batch_size):
            batches.append(all_points[i:i+batch_size])
        
        total_batches = len(batches)
        logger.info(f"将 {len(all_points):,} 个数据点分成 {total_batches} 个批次进行导入")
        
        # 创建InfluxDB客户端连接池
        # 预先创建连接，避免每个任务创建连接的开销
        client_pool = []
        for _ in range(max_workers):
            try:
                client = InfluxDBManager(
                    url=config["url"],
                    token=config["token"],
                    org=config["org"],
                    bucket=config["bucket"]
                )
                if client.connect():
                    client_pool.append(client)
                else:
                    logger.warning("无法创建InfluxDB连接")
            except Exception as e:
                logger.error(f"创建InfluxDB连接时出错: {str(e)}")
        
        if not client_pool:
            logger.error("无法创建任何InfluxDB连接，放弃导入")
            return 0
        
        logger.info(f"创建了 {len(client_pool)} 个InfluxDB连接")
        
        # 任务完成事件，用于同步完成状态
        all_tasks_submitted = threading.Event()
        all_tasks_completed = threading.Event()
        
        # 设置进度跟踪
        start_time = time.time()
        last_progress_time = start_time
        progress_update_interval = 5  # 延长进度更新间隔（秒）减少日志量
        submitted_batches = 0  # 已提交的批次
        completed_batches = 0  # 已完成的批次
        
        # 进度更新函数
        def update_progress():
            nonlocal last_progress_time
            current_time = time.time()
            if current_time - last_progress_time >= progress_update_interval:
                with result_lock:
                    total_processed = success_count + failed_count
                    progress = total_processed / total_points * 100
                    elapsed = current_time - start_time
                    
                    if elapsed > 0 and total_processed > 0:
                        points_per_second = total_processed / elapsed
                        remaining_points = total_points - total_processed
                        remaining_seconds = remaining_points / points_per_second if points_per_second > 0 else 0
                        
                        logger.info(f"导入进度: {progress:.1f}% ({total_processed:,}/{total_points:,} 点), "
                                    f"批次: {completed_batches}/{total_batches}, "
                                    f"速率: {points_per_second:.1f} 点/秒, "
                                    f"剩余: {remaining_seconds/60:.1f} 分钟")
                
                last_progress_time = current_time
        
        # 线程状态监控 - 新增函数，用于定期打印线程状态
        def monitor_status():
            while not all_tasks_completed.is_set():
                with result_lock:
                    logger.info(f"线程状态: 已提交批次={submitted_batches}/{total_batches}, "
                               f"已完成批次={completed_batches}, 进行中={in_progress}, "
                               f"队列大小={task_queue.qsize()}")
                time.sleep(30)  # 每30秒更新一次状态
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_status, daemon=True, name="monitor-thread")
        monitor_thread.start()
        
        # 消费者函数：从队列获取任务并执行
        def worker():
            nonlocal success_count, failed_count, completed_batches, in_progress
            
            # 从连接池获取一个客户端
            client = None
            with result_lock:
                if client_pool:
                    client = client_pool.pop()
            
            # 如果无法获取连接，创建新连接
            if client is None:
                try:
                    client = InfluxDBManager(
                        url=config["url"],
                        token=config["token"],
                        org=config["org"],
                        bucket=config["bucket"]
                    )
                    client.connect()
                except Exception as e:
                    logger.error(f"工作线程无法创建InfluxDB连接: {str(e)}")
                    return
            
            try:
                while not (task_queue.empty() and all_tasks_submitted.is_set()):
                    try:
                        # 尝试从队列获取任务，设置超时避免一直等待
                        batch_index, points, retry_count = task_queue.get(timeout=5)  # 增大超时时间
                        
                        # 标记一个任务正在处理
                        with result_lock:
                            in_progress += 1
                        
                        try:
                            # 写入数据
                            success = client.write_metrics_batch(points)
                            
                            with result_lock:
                                if success:
                                    success_count += len(points)
                                    logger.debug(f"批次 {batch_index+1}/{total_batches} 导入成功: {len(points)} 点")
                                else:
                                    # 写入失败，但可能需要重试
                                    if retry_count < max_retries:
                                        logger.warning(f"批次 {batch_index+1}/{total_batches} 导入失败，将重试 ({retry_count+1}/{max_retries})")
                                        # 延迟后重新放入队列
                                        threading.Timer(
                                            retry_delay * (retry_count + 1), 
                                            lambda: task_queue.put((batch_index, points, retry_count + 1))
                                        ).start()
                                    else:
                                        # 超过最大重试次数，标记为失败
                                        failed_count += len(points)
                                        logger.error(f"批次 {batch_index+1}/{total_batches} 在 {max_retries} 次尝试后导入失败")
                                
                                # 记录完成的批次
                                completed_batches += 1
                                in_progress -= 1
                                
                                # 每完成5个批次更新一次进度，减少锁竞争
                                if completed_batches % 5 == 0:
                                    update_progress()
                                
                                # 检查是否所有任务都已完成
                                if completed_batches >= total_batches:
                                    all_tasks_completed.set()
                                    
                        except Exception as e:
                            with result_lock:
                                # 处理异常
                                logger.error(f"批次 {batch_index+1}/{total_batches} 导入异常: {str(e)}")
                                
                                # 如果是可恢复的错误(如网络问题)则重试，否则标记失败
                                recoverable = "timeout" in str(e).lower() or "connection" in str(e).lower()
                                if recoverable and retry_count < max_retries:
                                    logger.warning(f"可恢复错误，批次 {batch_index+1}/{total_batches} 将重试 ({retry_count+1}/{max_retries})")
                                    # 指数退避重试
                                    delay = retry_delay * (2 ** retry_count) * (0.5 + random.random())
                                    threading.Timer(
                                        delay, 
                                        lambda: task_queue.put((batch_index, points, retry_count + 1))
                                    ).start()
                                else:
                                    # 不可恢复或达到最大重试次数
                                    failed_count += len(points)
                                    logger.error(f"批次 {batch_index+1}/{total_batches} 最终导入失败")
                                    completed_batches += 1
                                
                                in_progress -= 1
                        
                        # 标记任务完成
                        task_queue.task_done()
                        
                    except Empty:
                        # 队列暂时为空，但可能有新任务加入，继续循环
                        pass
                    except Exception as e:
                        # 处理其他异常
                        logger.error(f"工作线程遇到未预期的错误: {str(e)}")
                        with result_lock:
                            in_progress -= 1
                        break
            finally:
                # 放回连接时确保连接是可用的
                try:
                    # 不关闭连接，只检查健康状态
                    if client.verify_connection():
                        with result_lock:
                            client_pool.append(client)
                    else:
                        logger.warning("连接不可用，不放回连接池")
                except:
                    logger.warning("检查连接状态时出错，不放回连接池")
        
        # 启动工作线程
        threads = []
        for i in range(max_workers):
            thread = threading.Thread(target=worker, daemon=True, name=f"influx-worker-{i}")
            thread.start()
            threads.append(thread)
        
        logger.info(f"启动了 {len(threads)} 个工作线程")
        
        # 生产者：将数据批次放入队列
        try:
            # 提交所有批次到队列
            for i, batch in enumerate(batches):
                # 限制队列大小，避免内存占用过多
                while task_queue.qsize() >= max_workers:
                    time.sleep(0.5)  # 增加等待时间，减少CPU使用
                
                # 提交一个批次 (批次索引, 数据点列表, 重试次数)
                task_queue.put((i, batch, 0))
                submitted_batches += 1
                
                # 每提交50个批次更新一次进度
                if i % 50 == 0 or i == len(batches) - 1:
                    logger.info(f"已提交 {submitted_batches}/{total_batches} 个批次到队列")
            
            logger.info(f"所有 {total_batches} 个批次已提交到队列")
            all_tasks_submitted.set()
            
            # 等待所有任务完成
            # 设置超时，避免无限等待
            total_timeout = max(3600, total_points * 0.0005)  # 调整超时计算，至少1小时
            logger.info(f"等待所有批次导入完成，超时时间: {total_timeout/60:.1f} 分钟")
            
            # 等待所有任务完成，同时更新进度
            wait_start = time.time()
            while not all_tasks_completed.is_set():
                # 检查超时
                if time.time() - wait_start > total_timeout:
                    logger.warning("等待任务完成超时，强制退出")
                    break
                
                # 检查是否所有任务已提交且已完成
                with result_lock:
                    if (completed_batches >= total_batches) or (task_queue.empty() and in_progress == 0):
                        all_tasks_completed.set()
                        break
                
                # 定期更新进度
                update_progress()
                time.sleep(5)  # 增加睡眠时间，减少CPU使用
            
        except KeyboardInterrupt:
            logger.warning("用户中断，正在优雅停止...")
        except Exception as e:
            logger.error(f"导入过程中发生错误: {str(e)}")
        finally:
            # 导入完成或出错时，确保释放资源
            
            # 等待所有线程完成当前任务
            logger.info("等待工作线程完成当前任务...")
            all_tasks_completed.set()  # 确保设置完成标志
            for _ in range(10):  # 最多等待10秒
                with result_lock:
                    if in_progress == 0:
                        break
                time.sleep(1)
            
            # 关闭所有连接 - 只在最后操作完成时关闭
            logger.info("正在关闭所有InfluxDB连接...")
            for client in client_pool:
                try:
                    client.close()
                except Exception as e:
                    logger.error(f"关闭连接时出错: {str(e)}")
                    pass
            
            # 最后关闭主连接
            try:
                # 确保最后才关闭主连接
                if self.influxdb_client:
                    self.influxdb_client.close()
            except Exception as e:
                logger.error(f"关闭主连接时出错: {str(e)}")
                pass
        
        # 导入完成，显示摘要
        total_elapsed = time.time() - start_time
        logger.info(f"====== InfluxDB导入摘要 ======")
        logger.info(f"总计成功导入: {success_count:,} 个数据点")
        logger.info(f"总计失败导入: {failed_count:,} 个数据点")
        logger.info(f"成功率: {success_count/(success_count+failed_count)*100 if success_count+failed_count > 0 else 0:.2f}%")
        logger.info(f"总耗时: {total_elapsed:.1f} 秒 ({total_elapsed/60:.1f} 分钟)")
        if success_count > 0:
            logger.info(f"平均速率: {success_count/total_elapsed:.1f} 点/秒")
        logger.info(f"=============================")
        
        return success_count
    
    def import_logs_to_influxdb(self, logs_data: Dict) -> int:
        """将生成的日志数据导入到InfluxDB
        
        Args:
            logs_data: 生成的日志数据，格式为 {node_id: DataFrame}
            
        Returns:
            成功导入的日志条目数量
        """
        if not logs_data:
            logger.warning("没有日志数据可导入InfluxDB")
            return 0
        
        # 检查InfluxDB连接
        if not self.influxdb_available:
            logger.warning("InfluxDB不可用，跳过日志导入")
            return 0
        
        # 创建一个新的连接，不复用可能已经关闭的连接
        influxdb_client = None
        try:
            config = INFLUXDB_CONFIG
            logger.info(f"为日志导入创建新的InfluxDB连接: {config['url']}")
            influxdb_client = InfluxDBManager(
                url=config["url"],
                token=config["token"],
                org=config["org"],
                bucket=config["bucket"]
            )
            if not influxdb_client.connect():
                logger.error("无法为日志导入创建InfluxDB连接")
                return 0
        except Exception as e:
            logger.error(f"创建InfluxDB连接时出错: {str(e)}")
            return 0
        
        try:
            # 计算总日志条目
            total_logs = sum(len(df) for df in logs_data.values())
            logger.info(f"准备导入 {total_logs} 条日志记录到InfluxDB")
            
            # 使用日志生成器准备Point对象
            log_generator = LogGenerator()
            points = log_generator.prepare_logs_for_influxdb(logs_data)
            
            # 如果没有点，直接返回
            if not points:
                logger.warning("没有日志数据点可导入")
                return 0
            
            # 使用优化的批处理方法导入日志
            batch_size = 2000  # 增大日志批次大小
            
            # 分割成更大的批次
            batches = []
            for i in range(0, len(points), batch_size):
                batches.append(points[i:i+batch_size])
            
            total_batches = len(batches)
            logger.info(f"将 {len(points)} 条日志记录分成 {total_batches} 个批次进行导入")
            
            # 设置进度跟踪
            start_time = time.time()
            success_count = 0
            
            # 导入每个批次
            for i, batch in enumerate(batches):
                batch_num = i + 1
                retry_count = 0
                max_retries = 3
                batch_success = False
                
                # 重试循环
                while retry_count <= max_retries and not batch_success:
                    try:
                        # 写入数据
                        if retry_count > 0:
                            logger.info(f"重试日志批次 {batch_num}/{total_batches} (尝试 {retry_count}/{max_retries})")
                        
                        # 写入批次
                        success = influxdb_client.write_metrics_batch(batch)
                        if success:
                            success_count += len(batch)
                            batch_success = True
                            # 减少日志输出频率
                            if batch_num % 5 == 0 or batch_num == 1 or batch_num == total_batches:
                                logger.info(f"成功导入日志批次: {batch_num}/{total_batches}, "
                                           f"{success_count}/{len(points)} 条记录 "
                                           f"({success_count/len(points)*100:.1f}%)")
                            break  # 成功，退出重试循环
                        else:
                            logger.warning(f"日志批次 {batch_num}/{total_batches} 导入失败")
                            retry_count += 1
                            time.sleep(retry_count * 2)  # 指数退避
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"导入日志批次 {batch_num} 时出错: {error_msg}")
                        
                        # 判断是否可重试
                        if ("timeout" in error_msg.lower() or "connection" in error_msg.lower()) and retry_count < max_retries:
                            retry_count += 1
                            delay = retry_count * 2
                            logger.warning(f"将在 {delay} 秒后重试日志批次 {batch_num}...")
                            time.sleep(delay)
                        else:
                            # 不可重试或达到最大重试次数
                            if retry_count < max_retries:
                                retry_count += 1
                                time.sleep(2)
                            else:
                                logger.error(f"日志批次 {batch_num} 在 {max_retries} 次尝试后仍然失败")
                                break  # 放弃这个批次
            
            # 计算时间和统计
            total_elapsed = time.time() - start_time
            
            if success_count:
                logger.info(f"总计成功导入 {success_count}/{len(points)} 条日志记录到InfluxDB")
                logger.info(f"日志导入耗时: {total_elapsed:.1f} 秒，平均速率: {success_count/total_elapsed:.1f} 条/秒")
            else:
                logger.error("所有日志导入失败")
            
            return success_count
        except Exception as e:
            logger.error(f"导入日志过程中发生未预期的错误: {str(e)}")
            return 0
        finally:
            # 确保在函数结束前关闭连接
            if influxdb_client:
                try:
                    # 确保所有数据都已写入
                    if hasattr(influxdb_client.write_api, 'flush'):
                        influxdb_client.write_api.flush()
                    
                    # 可选：添加短暂延时
                    time.sleep(1)
                    
                    # 关闭连接
                    influxdb_client.close()
                    logger.info("日志导入完成，已关闭InfluxDB连接")
                except Exception as e:
                    logger.warning(f"关闭InfluxDB连接时出错: {str(e)}")
                    
    def run(self, 
           start_time: Optional[datetime] = None,
           end_time: Optional[datetime] = None,
           export_csv: bool = False,
           import_influxdb: bool = True,
           output_dir: str = './output',
           include_anomalies: bool = True,
           generate_logs: bool = True,   # 新增参数：是否生成日志
           test_mode: bool = False      # 新增参数：测试模式，只处理少量数据点
          ) -> Dict:
        """
        运行数据生成过程
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            export_csv: 是否导出为CSV
            import_influxdb: 是否导入到InfluxDB
            output_dir: 导出CSV的输出目录
            include_anomalies: 是否包含异常数据
            generate_logs: 是否生成对应的日志状态数据
            test_mode: 测试模式，只处理少量数据进行验证
            
        Returns:
            运行结果统计
        """
        # 如果节点信息为空，尝试从Neo4j加载
        if not self.nodes_info:
            self.load_nodes_from_neo4j()
            
        if not self.nodes_info:
            logger.error("无法获取节点信息，无法生成时序数据")
            return {
                'status': 'failed',
                'error': '无法获取节点信息'
            }
        
        # 测试模式下只使用部分节点
        if test_mode:
            max_test_nodes = 5  # 测试模式下处理的最大节点数
            if len(self.nodes_info) > max_test_nodes:
                logger.info(f"测试模式：将只处理 {max_test_nodes} 个节点")
                self.nodes_info = self.nodes_info[:max_test_nodes]
            
        # 生成时序数据
        metrics_data = self.generate_metrics_data(
            start_time=start_time,
            end_time=end_time,
            include_anomalies=include_anomalies
        )
        
        # 运行结果
        result = {
            'status': 'success',
            'node_count': len(self.nodes_info),
            'metrics_count': sum(len(metrics) for metrics in metrics_data.values()),
            'data_points': sum(len(df) for node_metrics in metrics_data.values() for df in node_metrics.values()),
            'time_range': {
                'start': start_time,
                'end': end_time
            }
        }
        
        # 生成对应的日志状态数据
        logs_data = {}
        if generate_logs:
            logger.info("开始生成对应的日志状态数据...")
            log_generator = LogGenerator()
            logs_data = log_generator.generate_logs_for_metrics(
                metrics_data=metrics_data,
                nodes_info=self.nodes_info,
                random_events=True,
                info_log_frequency=15  # 每15个数据点生成一条INFO日志
            )
            
            total_logs = sum(len(df) for df in logs_data.values())
            logger.info(f"成功生成 {total_logs} 条日志记录，覆盖 {len(logs_data)} 个节点")
            
            result['logs_count'] = total_logs
        
        # 导出为CSV
        if export_csv:
            # 导出性能指标
            metrics_csv_files = self.export_to_csv(metrics_data, os.path.join(output_dir, 'metrics'))
            
            # 导出日志数据
            logs_csv_files = []
            if generate_logs and logs_data:
                # 创建日志输出目录
                logs_output_dir = os.path.join(output_dir, 'logs')
                os.makedirs(logs_output_dir, exist_ok=True)
                
                # 导出每个节点的日志
                for node_id, logs_df in logs_data.items():
                    file_path = os.path.join(logs_output_dir, f"{node_id}_logs.csv")
                    logs_df.to_csv(file_path, index=False)
                    logs_csv_files.append(file_path)
                    logger.info(f"已导出日志到 {file_path}")
            
            result['csv_files'] = {
                'metrics': {
                    'count': len(metrics_csv_files),
                    'directory': os.path.join(output_dir, 'metrics')
                },
                'logs': {
                    'count': len(logs_csv_files),
                    'directory': os.path.join(output_dir, 'logs')
                } if logs_csv_files else None
            }
            
        # 导入到InfluxDB
        if import_influxdb:
            # 检查InfluxDB是否可用
            if not self.influxdb_available:
                logger.warning("InfluxDB不可用，跳过导入")
                result['influxdb_import'] = {
                    'metrics_count': 0,
                    'logs_count': 0,
                    'success': False,
                    'error': 'InfluxDB连接不可用'
                }
            else:
                try:
                    # 导入性能指标
                    imported_metrics = self.import_to_influxdb(metrics_data)
                    
                    # 导入日志数据 - 确保日志数据在性能指标导入后单独导入
                    imported_logs = 0
                    if generate_logs and logs_data:
                        # 在此处单独处理日志导入
                        imported_logs = self.import_logs_to_influxdb(logs_data)
                    
                    result['influxdb_import'] = {
                        'metrics_count': imported_metrics,
                        'logs_count': imported_logs,
                        'success': imported_metrics > 0 or imported_logs > 0
                    }
                except Exception as e:
                    logger.error(f"数据导入过程中发生未预期的错误: {str(e)}")
                    result['influxdb_import'] = {
                        'metrics_count': 0,
                        'logs_count': 0,
                        'success': False,
                        'error': str(e)
                    }
                finally:
                    # 确保在函数结束前关闭所有连接
                    if self.influxdb_client:
                        try:
                            self.influxdb_client.close()
                            logger.info("已关闭所有InfluxDB连接")
                        except Exception as e:
                            logger.warning(f"关闭主InfluxDB连接时出错: {str(e)}")
            
        return result

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成模拟时序数据')
    
    # 天数相关参数
    time_group = parser.add_argument_group('时间范围参数（两种方式二选一）')
    time_group.add_argument('--days', type=int, default=5, help='生成多少天的数据（从当前时间往前推）')
    time_group.add_argument('--start-date', type=str, help='开始日期，格式: YYYY-MM-DD')
    time_group.add_argument('--end-date', type=str, help='结束日期，格式: YYYY-MM-DD，默认为当前日期')
    
    # 其他参数
    parser.add_argument('--csv', action='store_true', help='导出为CSV文件')
    parser.add_argument('--no-influxdb', action='store_true', help='不导入到InfluxDB')
    parser.add_argument('--csv-only', action='store_true', help='仅导出CSV，不写入InfluxDB（自动设置--csv和--no-influxdb）')
    parser.add_argument('--output-dir', type=str, default='./output', help='CSV输出目录')
    parser.add_argument('--node-types', type=str, nargs='+', help='要生成数据的节点类型')
    parser.add_argument('--no-anomalies', action='store_true', help='不生成异常数据')
    parser.add_argument('--max-nodes', type=int, default=None, help='最大节点数量限制，用于测试')
    parser.add_argument('--sample-interval', type=int, default=15, 
                       help='数据采样间隔（分钟），增大此值可减少数据点数量，提高导入速度')
    parser.add_argument('--no-logs', action='store_true', help='不生成日志状态数据')
    parser.add_argument('--test', action='store_true', help='测试模式，仅处理少量数据验证功能')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 处理csv-only参数
    if args.csv_only:
        args.csv = True
        args.no_influxdb = True
        print("已启用仅CSV模式，数据将不会导入到InfluxDB")
    
    print("\n===== 时序数据生成 =====")
    if args.no_influxdb:
        print("开始生成模拟时序数据...")
    else:
        print("开始生成模拟时序数据并导入到InfluxDB...")
    
    # 设置时间范围
    end_time = datetime.now()
    
    # 处理时间范围参数
    if args.start_date:
        # 使用指定的日期范围
        try:
            start_time = datetime.strptime(args.start_date, '%Y-%m-%d')
            if args.end_date:
                end_time = datetime.strptime(args.end_date, '%Y-%m-%d')
                # 设置为当天结束时间
                end_time = end_time.replace(hour=23, minute=59, second=59)
            print(f"使用指定日期范围: {start_time.strftime('%Y-%m-%d')} 到 {end_time.strftime('%Y-%m-%d')}")
        except ValueError as e:
            print(f"日期格式错误: {str(e)}")
            print("将使用默认时间范围...")
            start_time = end_time - timedelta(days=args.days)
    else:
        # 使用天数参数
        start_time = end_time - timedelta(days=args.days)
        print(f"使用最近 {args.days} 天数据: {start_time.strftime('%Y-%m-%d')} 到 {end_time.strftime('%Y-%m-%d')}")
    
    print(f"详细时间范围: {start_time} 到 {end_time}")
    
    if args.node_types:
        print(f"节点类型: {', '.join(args.node_types)}")
    else:
        print("节点类型: 全部可用类型")
    
    # 创建生成器实例
    generator = TimeSeriesGenerator()
    
    # 设置采样间隔
    if args.sample_interval:
        # 更新各节点类型的采样间隔
        for node_type in generator.sample_intervals:
            generator.sample_intervals[node_type] = args.sample_interval
        print(f"已设置采样间隔为: {args.sample_interval}分钟")
    
    # 加载节点信息
    print("\n正在从Neo4j加载节点信息...")
    nodes = generator.load_nodes_from_neo4j(node_types=args.node_types)
    print(f"已加载 {len(nodes)} 个节点")
    
    # 限制节点数量
    if args.max_nodes and len(nodes) > args.max_nodes:
        print(f"节点数量超过限制，将仅使用前 {args.max_nodes} 个节点进行测试")
        generator.nodes_info = nodes[:args.max_nodes]
        print(f"已限制为 {len(generator.nodes_info)} 个节点")
    
    # 运行生成过程
    print("\n正在生成时序数据...")
    result = generator.run(
        start_time=start_time,
        end_time=end_time,
        export_csv=args.csv,
        import_influxdb=not args.no_influxdb,
        output_dir=args.output_dir,
        include_anomalies=not args.no_anomalies,
        generate_logs=not args.no_logs,
        test_mode=args.test
    )
    
    # 打印结果
    print("\n===== 时序数据生成结果 =====")
    print(f"状态: {result['status']}")
    print(f"节点数量: {result['node_count']}")
    print(f"指标类型数量: {result['metrics_count']}")
    print(f"性能指标数据点总数: {result['data_points']}")
    
    if 'logs_count' in result:
        print(f"日志状态条目总数: {result['logs_count']}")
    
    if 'csv_files' in result:
        if result['csv_files']['metrics']:
            print(f"性能指标CSV文件: {result['csv_files']['metrics']['count']} 个文件已导出到 {result['csv_files']['metrics']['directory']}")
        if result['csv_files'].get('logs'):
            print(f"日志状态CSV文件: {result['csv_files']['logs']['count']} 个文件已导出到 {result['csv_files']['logs']['directory']}")
        
    if 'influxdb_import' in result:
        print(f"InfluxDB导入: {result['influxdb_import']['metrics_count']} 个性能指标数据点")
        if 'logs_count' in result['influxdb_import']:
            print(f"InfluxDB导入: {result['influxdb_import']['logs_count']} 条日志记录")
        
    print("===========================\n")
    
    if result['status'] == 'success':
        print("时序数据生成完成!")
        
        # 提供查询InfluxDB的示例
        if 'influxdb_import' in result and result['influxdb_import']['success']:
            print("\n要查询生成的时序数据，可以使用以下Flux查询示例:")
            print("```flux")
            print("// 查询性能指标")
            print("from(bucket: \"metrics\")")
            print("  |> range(start: -30d)")
            print("  |> filter(fn: (r) => r._measurement == \"vm_metrics\")")
            print("  |> filter(fn: (r) => r.node_id == \"<节点ID>\")")
            print("  |> filter(fn: (r) => r.metric == \"cpu_usage\")")
            print("  |> filter(fn: (r) => r._field == \"value\")")
            print("  |> yield(name: \"mean\")")
            print("")
            print("// 查询日志状态")
            print("from(bucket: \"metrics\")")
            print("  |> range(start: -30d)")
            print("  |> filter(fn: (r) => r._measurement == \"node_logs\")")
            print("  |> filter(fn: (r) => r.node_id == \"<节点ID>\")")
            print("  |> filter(fn: (r) => r.level == \"ERROR\" or r.level == \"WARNING\")")
            print("```")
    else:
        print(f"时序数据生成失败: {result.get('error', '未知错误')}")
    
if __name__ == "__main__":
    main() 