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
from typing import Dict, List, Optional, Union, Any, Tuple
from influxdb_client import Point

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from dynamic_graph_rag.config.settings import NODE_TYPES, INFLUXDB_CONFIG, GRAPH_DB_CONFIG
from dynamic_graph_rag.db.neo4j_connector import Neo4jConnector
from dynamic_graph_rag.db.influxdb_client import InfluxDBManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / 'time_series_generator.log')
    ]
)
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
        if not self.influxdb_client.connect():
            logger.error("无法连接到InfluxDB，跳过导入")
            return 0
        
        total_imported = 0
        
        try:
            for node_id, metrics in metrics_data.items():
                for metric_name, df in metrics.items():
                    if df.empty:
                        continue
                    
                    # 确保DataFrame有必要的列
                    if not all(col in df.columns for col in ['timestamp', 'value', 'node_type']):
                        logger.warning(f"节点 {node_id} 的 {metric_name} 指标数据缺少必要的列")
                        continue
                    
                    # 将数据转换为适合导入的格式
                    ts_df = df.copy()
                    ts_df['node_id'] = node_id
                    ts_df['metric'] = metric_name
                    
                    # 按批次导入
                    batch_size = 1000
                    for i in range(0, len(ts_df), batch_size):
                        batch_df = ts_df.iloc[i:i + batch_size]
                        
                        # 生成Point对象列表
                        points = []
                        for _, row in batch_df.iterrows():
                            measurement = f"{row['node_type'].lower()}_metrics"
                            
                            # 创建Point对象
                            point = Point(measurement)
                            
                            # 添加标签
                            point = point.tag("node_id", row['node_id'])
                            point = point.tag("node_type", row['node_type'])
                            point = point.tag("metric", row['metric'])
                            
                            # 添加值
                            point = point.field("value", float(row['value']))
                            if 'unit' in row:
                                point = point.field("unit", row['unit'])
                            
                            # 添加时间戳
                            point = point.time(row['timestamp'])
                            
                            points.append(point)
                        
                        # 写入批次数据
                        success = self.influxdb_client.write_metrics_batch(points)
                        
                        if success:
                            total_imported += len(points)
                            logger.info(f"成功导入 {len(points)} 个数据点（节点: {node_id}, 指标: {metric_name})")
                        else:
                            logger.warning(f"导入数据点失败（节点: {node_id}, 指标: {metric_name})")
            
            logger.info(f"总计成功导入 {total_imported} 个数据点到InfluxDB")
            return total_imported
            
        except Exception as e:
            logger.error(f"导入数据到InfluxDB时出错: {str(e)}")
            return total_imported
        finally:
            # 关闭连接
            try:
                self.influxdb_client.close()
            except:
                pass
    
    def run(self, 
           start_time: Optional[datetime] = None,
           end_time: Optional[datetime] = None,
           export_csv: bool = False,
           import_influxdb: bool = True,
           output_dir: str = './output',
           include_anomalies: bool = True) -> Dict:
        """
        运行数据生成过程
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            export_csv: 是否导出为CSV
            import_influxdb: 是否导入到InfluxDB
            output_dir: 导出CSV的输出目录
            include_anomalies: 是否包含异常数据
            
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
            
        # 生成时序数据
        metrics_data = self.generate_metrics_data(
            start_time=start_time,
            end_time=end_time,
            include_anomalies=include_anomalies
        )
        
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
        
        # 导出为CSV
        if export_csv:
            csv_files = self.export_to_csv(metrics_data, output_dir)
            result['csv_files'] = {
                'count': len(csv_files),
                'directory': output_dir
            }
            
        # 导入到InfluxDB
        if import_influxdb:
            # 检查InfluxDB是否可用
            if not self.influxdb_available:
                logger.warning("InfluxDB不可用，跳过导入")
                result['influxdb_import'] = {
                    'count': 0,
                    'success': False,
                    'error': 'InfluxDB连接不可用'
                }
            else:
                imported_count = self.import_to_influxdb(metrics_data)
                result['influxdb_import'] = {
                    'count': imported_count,
                    'success': imported_count > 0
                }
            
        return result

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成模拟时序数据')
    
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
    
    # 设置时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.days)
    
    # 创建生成器实例
    generator = TimeSeriesGenerator()
    
    # 加载节点信息
    generator.load_nodes_from_neo4j(node_types=args.node_types)
    
    # 运行生成过程
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
    print(f"时间范围: {result['time_range']['start']} 到 {result['time_range']['end']}")
    
    if 'csv_files' in result:
        print(f"CSV文件: {result['csv_files']['count']} 个文件已导出到 {result['csv_files']['directory']}")
        
    if 'influxdb_import' in result:
        print(f"InfluxDB导入: {result['influxdb_import']['count']} 个数据点")
        
    print("===========================\n")
    
if __name__ == "__main__":
    main() 