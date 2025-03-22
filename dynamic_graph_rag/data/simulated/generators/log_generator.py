#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志状态数据生成器模块
根据性能指标动态生成对应的日志状态数据
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import random
from influxdb_client import Point

logger = logging.getLogger('log_generator')

class LogGenerator:
    """根据性能指标生成对应日志状态的生成器"""
    
    def __init__(self):
        """初始化日志生成器"""
        self._init_log_config()
    
    def _init_log_config(self):
        """初始化日志配置，包括阈值和模板"""
        # 定义状态阈值配置
        self.thresholds = {
            'VM': {
                'cpu_usage': {
                    'warning': 80,  # CPU > 80% 触发警告
                    'error': 95,    # CPU > 95% 触发错误
                    'recovery': 70  # CPU < 70% 触发恢复
                },
                'memory_usage': {
                    'warning': 85, 
                    'error': 95,
                    'recovery': 75
                },
                'disk_io': {
                    'warning': 7000,
                    'error': 9000,
                    'recovery': 5000
                },
                'network_throughput': {
                    'warning': 7000,
                    'error': 9000,
                    'recovery': 5000
                }
            },
            'HOST': {
                'cpu_usage': {'warning': 70, 'error': 90, 'recovery': 60},
                'memory_usage': {'warning': 80, 'error': 90, 'recovery': 70},
                'disk_usage': {'warning': 80, 'error': 90, 'recovery': 70},
                'temperature': {'warning': 65, 'error': 80, 'recovery': 60}
            },
            'NE': {
                'load': {'warning': 75, 'error': 90, 'recovery': 65},
                'response_time': {'warning': 500, 'error': 800, 'recovery': 300},
                'success_rate': {'warning': 50, 'error': 30, 'recovery': 70, 'inverse': True}  # 注意:低于阈值触发警告
            },
            'TRU': {
                'usage': {'warning': 80, 'error': 95, 'recovery': 70},
                'latency': {'warning': 50, 'error': 80, 'recovery': 30}
            },
            'HOSTGROUP': {
                'aggregate_cpu': {'warning': 75, 'error': 90, 'recovery': 65},
                'aggregate_memory': {'warning': 80, 'error': 90, 'recovery': 70}
            }
        }
        
        # 日志模板配置
        self.log_templates = {
            'VM': {
                'cpu_usage': {
                    'warning': "VM {node_id} CPU使用率较高，当前值{value}%，超过警告阈值{threshold}%",
                    'error': "VM {node_id} CPU使用率严重过高，当前值{value}%，系统性能严重下降",
                    'recovery': "VM {node_id} CPU使用率已恢复到正常水平，当前值{value}%"
                },
                'memory_usage': {
                    'warning': "VM {node_id} 内存使用率较高，当前值{value}%，可能影响系统性能",
                    'error': "VM {node_id} 内存使用率严重过高，当前值{value}%，系统面临内存不足风险",
                    'recovery': "VM {node_id} 内存使用率已恢复到正常水平，当前值{value}%"
                },
                'disk_io': {
                    'warning': "VM {node_id} 磁盘IO较高，当前值{value} IOPS，可能影响系统响应",
                    'error': "VM {node_id} 磁盘IO严重过高，当前值{value} IOPS，系统响应缓慢",
                    'recovery': "VM {node_id} 磁盘IO已恢复到正常水平，当前值{value} IOPS"
                },
                'network_throughput': {
                    'warning': "VM {node_id} 网络吞吐量较高，当前值{value} Mbps，可能影响网络服务",
                    'error': "VM {node_id} 网络吞吐量严重过高，当前值{value} Mbps，网络服务质量下降",
                    'recovery': "VM {node_id} 网络吞吐量已恢复到正常水平，当前值{value} Mbps"
                }
            },
            'HOST': {
                'cpu_usage': {
                    'warning': "主机 {node_id} CPU使用率较高，当前值{value}%，超过警告阈值{threshold}%",
                    'error': "主机 {node_id} CPU使用率严重过高，当前值{value}%，可能影响所有虚拟机性能",
                    'recovery': "主机 {node_id} CPU使用率已恢复到正常水平，当前值{value}%"
                },
                'memory_usage': {
                    'warning': "主机 {node_id} 内存使用率较高，当前值{value}%，接近预警水平",
                    'error': "主机 {node_id} 内存使用率严重过高，当前值{value}%，可能导致内存交换",
                    'recovery': "主机 {node_id} 内存使用率已恢复到正常水平，当前值{value}%"
                },
                'disk_usage': {
                    'warning': "主机 {node_id} 磁盘空间使用率较高，当前值{value}%，接近预警水平",
                    'error': "主机 {node_id} 磁盘空间严重不足，当前值{value}%，可能影响系统运行",
                    'recovery': "主机 {node_id} 磁盘空间使用率已恢复到正常水平，当前值{value}%"
                },
                'temperature': {
                    'warning': "主机 {node_id} 温度较高，当前值{value}°C，超过正常工作温度",
                    'error': "主机 {node_id} 温度过高，当前值{value}°C，可能触发保护性降频",
                    'recovery': "主机 {node_id} 温度已恢复到正常水平，当前值{value}°C"
                }
            },
            'NE': {
                'load': {
                    'warning': "网络设备 {node_id} 负载较高，当前值{value}%，可能影响转发性能",
                    'error': "网络设备 {node_id} 负载严重过高，当前值{value}%，存在转发丢包风险",
                    'recovery': "网络设备 {node_id} 负载已恢复到正常水平，当前值{value}%"
                },
                'response_time': {
                    'warning': "网络设备 {node_id} 响应时间增加，当前值{value}ms，网络延迟增大",
                    'error': "网络设备 {node_id} 响应时间严重增加，当前值{value}ms，网络性能下降",
                    'recovery': "网络设备 {node_id} 响应时间已恢复正常，当前值{value}ms"
                },
                'success_rate': {
                    'warning': "网络设备 {node_id} 请求成功率下降，当前值{value}%，低于正常水平",
                    'error': "网络设备 {node_id} 请求成功率严重下降，当前值{value}%，服务可用性受到影响",
                    'recovery': "网络设备 {node_id} 请求成功率已恢复正常，当前值{value}%"
                }
            },
            'TRU': {
                'usage': {
                    'warning': "存储单元 {node_id} 使用率较高，当前值{value}%，接近预警水平",
                    'error': "存储单元 {node_id} 使用率严重过高，当前值{value}%，存在容量不足风险",
                    'recovery': "存储单元 {node_id} 使用率已恢复到正常水平，当前值{value}%"
                },
                'latency': {
                    'warning': "存储单元 {node_id} 延迟增加，当前值{value}ms，存储响应变慢",
                    'error': "存储单元 {node_id} 延迟严重增加，当前值{value}ms，存储访问性能下降",
                    'recovery': "存储单元 {node_id} 延迟已恢复正常，当前值{value}ms"
                }
            },
            'HOSTGROUP': {
                'aggregate_cpu': {
                    'warning': "主机组 {node_id} 整体CPU使用率较高，当前值{value}%，集群负载增加",
                    'error': "主机组 {node_id} 整体CPU使用率严重过高，当前值{value}%，集群面临过载风险",
                    'recovery': "主机组 {node_id} 整体CPU使用率已恢复到正常水平，当前值{value}%"
                },
                'aggregate_memory': {
                    'warning': "主机组 {node_id} 整体内存使用率较高，当前值{value}%，集群资源紧张",
                    'error': "主机组 {node_id} 整体内存使用率严重过高，当前值{value}%，集群内存资源不足",
                    'recovery': "主机组 {node_id} 整体内存使用率已恢复到正常水平，当前值{value}%"
                }
            }
        }
        
        # 为每种节点类型添加定期信息日志
        self.info_log_templates = {
            'VM': [
                "VM {node_id} 运行正常，各项指标在正常范围内",
                "VM {node_id} 状态检查完成，系统稳定运行",
                "VM {node_id} 定期健康检查通过"
            ],
            'HOST': [
                "主机 {node_id} 运行正常，各项指标在正常范围内",
                "主机 {node_id} 状态检查完成，硬件运行正常",
                "主机 {node_id} 定期健康检查通过"
            ],
            'NE': [
                "网络设备 {node_id} 运行正常，网络状态良好",
                "网络设备 {node_id} 状态检查完成，连接稳定",
                "网络设备 {node_id} 定期健康检查通过"
            ],
            'TRU': [
                "存储单元 {node_id} 运行正常，存储状态良好",
                "存储单元 {node_id} 状态检查完成，数据访问正常",
                "存储单元 {node_id} 定期健康检查通过"
            ],
            'HOSTGROUP': [
                "主机组 {node_id} 运行正常，集群状态良好",
                "主机组 {node_id} 状态检查完成，资源分配均衡",
                "主机组 {node_id} 定期健康检查通过"
            ]
        }
        
        # 为突发异常点定义模板
        self.anomaly_templates = {
            'VM': {
                'cpu_usage': {
                    'spike': "VM {node_id} CPU使用率出现突发峰值，当前值{value}%，明显高于平均水平{mean}%",
                    'drop': "VM {node_id} CPU使用率出现异常下降，当前值{value}%，明显低于平均水平{mean}%"
                },
                'memory_usage': {
                    'spike': "VM {node_id} 内存使用率出现突发增长，当前值{value}%，明显高于平均水平{mean}%",
                    'drop': "VM {node_id} 内存使用率出现异常下降，当前值{value}%，明显低于平均水平{mean}%"
                },
                'disk_io': {
                    'spike': "VM {node_id} 磁盘IO出现突发峰值，当前值{value} IOPS，明显高于平均水平{mean} IOPS",
                    'drop': "VM {node_id} 磁盘IO出现异常下降，当前值{value} IOPS，明显低于平均水平{mean} IOPS"
                },
                'network_throughput': {
                    'spike': "VM {node_id} 网络吞吐量出现突发峰值，当前值{value} Mbps，明显高于平均水平{mean} Mbps",
                    'drop': "VM {node_id} 网络吞吐量出现异常下降，当前值{value} Mbps，明显低于平均水平{mean} Mbps"
                }
            },
            # 其他节点类型的异常模板可以类似定义
        }
        
        # 为系统状态变化添加事件日志
        self.event_templates = {
            'VM': {
                'start': "VM {node_id} 已启动，开始正常运行",
                'stop': "VM {node_id} 已停止运行",
                'restart': "VM {node_id} 已重启，正在恢复服务",
                'migrate': "VM {node_id} 正在进行迁移，可能出现短暂服务中断"
            },
            'HOST': {
                'start': "主机 {node_id} 已开机，开始正常运行",
                'stop': "主机 {node_id} 已关机",
                'maintenance': "主机 {node_id} 进入维护模式，暂停提供服务",
                'upgrade': "主机 {node_id} 正在进行固件升级"
            }
        }
    
    def generate_logs_for_metrics(self, metrics_data: Dict, nodes_info: List[Dict], 
                                 random_events: bool = True, info_log_frequency: int = 20) -> Dict:
        """根据性能指标数据生成对应的日志状态数据
        
        Args:
            metrics_data: 生成的性能指标数据，格式为 {node_id: {metric_name: DataFrame}}
            nodes_info: 节点信息列表
            random_events: 是否生成随机系统事件日志
            info_log_frequency: 产生INFO级别日志的频率（每多少个样本点产生一条）
            
        Returns:
            日志数据，格式为 {node_id: DataFrame}
        """
        all_logs = {}
        
        # 为每个节点生成日志
        for node_id, metrics in metrics_data.items():
            # 获取节点信息
            node_info = next((n for n in nodes_info if n['id'] == node_id), None)
            if not node_info:
                continue
                
            node_type = node_info['type']
            
            # 跳过不需要生成日志的节点类型
            if node_type not in self.thresholds:
                continue
                
            # 初始化日志列表
            logs = []
            
            # 记录该节点的样本时间点，用于生成随机INFO日志
            timepoints = []
            
            # 处理每个指标
            for metric_name, df in metrics.items():
                # 检查是否有此指标的阈值配置
                if metric_name not in self.thresholds.get(node_type, {}):
                    continue
                    
                threshold_config = self.thresholds[node_type][metric_name]
                template_config = self.log_templates.get(node_type, {}).get(metric_name, {})
                
                # 跟踪指标状态
                current_state = 'normal'  # 初始状态
                
                # 收集所有时间点
                for ts in df['timestamp']:
                    if ts not in timepoints:
                        timepoints.append(ts)
                
                # 计算统计特性，用于异常检测
                mean_value = df['value'].mean()
                std_value = df['value'].std()
                
                # 遍历时间序列数据
                for idx, row in df.iterrows():
                    value = row['value']
                    timestamp = row['timestamp']
                    
                    # 确定当前状态
                    new_state = current_state
                    
                    # 正向指标（越高越危险）
                    if not threshold_config.get('inverse', False):
                        # 检查错误阈值
                        if value >= threshold_config['error']:
                            new_state = 'error'
                        # 检查警告阈值
                        elif value >= threshold_config['warning']:
                            new_state = 'warning'
                        # 检查恢复阈值
                        elif value <= threshold_config['recovery'] and (current_state == 'warning' or current_state == 'error'):
                            new_state = 'recovery'
                    # 反向指标（越低越危险，如成功率）
                    else:
                        # 检查错误阈值
                        if value <= threshold_config['error']:
                            new_state = 'error'
                        # 检查警告阈值
                        elif value <= threshold_config['warning']:
                            new_state = 'warning'
                        # 检查恢复阈值
                        elif value >= threshold_config['recovery'] and (current_state == 'warning' or current_state == 'error'):
                            new_state = 'recovery'
                    
                    # 状态变化时生成日志
                    if new_state != current_state and new_state in template_config:
                        log_message = template_config[new_state].format(
                            node_id=node_id,
                            value=round(value, 2),
                            threshold=threshold_config.get(new_state, round(value, 2))
                        )
                        
                        # 确定日志级别
                        level = {
                            'error': 'ERROR',
                            'warning': 'WARNING',
                            'recovery': 'INFO',
                            'normal': 'INFO'
                        }.get(new_state, 'INFO')
                        
                        # 添加随机波动，使日志时间不完全等于性能数据采样点
                        # 在采样点前后5分钟内随机生成
                        jitter = timedelta(minutes=random.uniform(-5, 5))
                        log_timestamp = timestamp + jitter
                        
                        # 创建日志条目
                        log_entry = {
                            'timestamp': log_timestamp,
                            'node_id': node_id,
                            'node_type': node_type,
                            'level': level,
                            'message': log_message,
                            'source': 'threshold',
                            'metric': metric_name,
                            'metric_value': value
                        }
                        logs.append(log_entry)
                        
                    # 更新状态
                    current_state = new_state
                    
                    # 检测异常值 (超过2.5个标准差)
                    if abs(value - mean_value) > 2.5 * std_value and std_value > 0:
                        # 避免与阈值日志重复
                        if any(abs((l['timestamp'] - timestamp).total_seconds()) < 300 and 
                               l['metric'] == metric_name for l in logs):
                            continue
                            
                        # 判断是高异常还是低异常
                        if value > mean_value and not threshold_config.get('inverse', False):
                            anomaly_type = 'spike'
                            level = "WARNING"
                        elif value < mean_value and not threshold_config.get('inverse', False):
                            anomaly_type = 'drop'
                            level = "WARNING"
                        elif value < mean_value and threshold_config.get('inverse', False):
                            anomaly_type = 'spike'  # 对于反向指标，低值是危险的
                            level = "WARNING"
                        elif value > mean_value and threshold_config.get('inverse', False):
                            anomaly_type = 'drop'  # 对于反向指标，高值是安全的
                            level = "WARNING"
                        
                        # 查找对应的异常模板
                        anomaly_template = self.anomaly_templates.get(node_type, {}).get(metric_name, {}).get(anomaly_type)
                        
                        # 如果没有特定模板，使用通用模板
                        if not anomaly_template:
                            if anomaly_type == 'spike':
                                anomaly_template = "{node_type} {node_id} {metric} 出现突发峰值，当前值{value}，明显偏离平均水平{mean}"
                            else:
                                anomaly_template = "{node_type} {node_id} {metric} 出现异常下降，当前值{value}，明显偏离平均水平{mean}"
                        
                        log_message = anomaly_template.format(
                            node_id=node_id,
                            node_type=node_type,
                            metric=metric_name,
                            value=round(value, 2),
                            mean=round(mean_value, 2)
                        )
                        
                        # 添加随机波动
                        jitter = timedelta(minutes=random.uniform(-2, 2))
                        log_timestamp = timestamp + jitter
                        
                        # 创建日志条目
                        log_entry = {
                            'timestamp': log_timestamp,
                            'node_id': node_id,
                            'node_type': node_type,
                            'level': level,
                            'message': log_message,
                            'source': 'anomaly',
                            'metric': metric_name,
                            'metric_value': value
                        }
                        logs.append(log_entry)
            
            # 添加定期信息日志
            if timepoints and node_type in self.info_log_templates:
                sorted_timepoints = sorted(timepoints)
                
                # 每隔一定样本点生成一条INFO日志
                for i in range(0, len(sorted_timepoints), info_log_frequency):
                    timestamp = sorted_timepoints[i]
                    
                    # 随机选择一个INFO日志模板
                    info_template = random.choice(self.info_log_templates[node_type])
                    
                    # 生成日志消息
                    log_message = info_template.format(node_id=node_id)
                    
                    # 添加随机波动
                    jitter = timedelta(minutes=random.uniform(-10, 10))
                    log_timestamp = timestamp + jitter
                    
                    # 创建日志条目
                    log_entry = {
                        'timestamp': log_timestamp,
                        'node_id': node_id,
                        'node_type': node_type,
                        'level': 'INFO',
                        'message': log_message,
                        'source': 'info',
                        'metric': 'system',
                        'metric_value': 0.0
                    }
                    logs.append(log_entry)
            
            # 添加随机系统事件日志
            if random_events and timepoints and node_type in self.event_templates:
                sorted_timepoints = sorted(timepoints)
                
                # 决定是否为此节点生成事件
                if random.random() < 0.3:  # 30%的节点会有事件
                    # 随机选择1-2个时间点生成事件
                    event_count = random.randint(1, 2)
                    for _ in range(event_count):
                        # 随机选择一个时间点
                        timestamp_idx = random.randint(0, len(sorted_timepoints) - 1)
                        timestamp = sorted_timepoints[timestamp_idx]
                        
                        # 随机选择一个事件类型
                        event_type = random.choice(list(self.event_templates[node_type].keys()))
                        
                        # 生成日志消息
                        log_message = self.event_templates[node_type][event_type].format(node_id=node_id)
                        
                        # 确定日志级别
                        if event_type in ['stop', 'maintenance']:
                            level = 'WARNING'
                        elif event_type in ['restart', 'migrate']:
                            level = 'WARNING'
                        else:
                            level = 'INFO'
                        
                        # 创建日志条目
                        log_entry = {
                            'timestamp': timestamp,
                            'node_id': node_id,
                            'node_type': node_type,
                            'level': level,
                            'message': log_message,
                            'source': 'event',
                            'metric': 'system',
                            'metric_value': 0.0
                        }
                        logs.append(log_entry)
            
            # 如果有日志，转换为DataFrame并排序
            if logs:
                logs_df = pd.DataFrame(logs)
                logs_df = logs_df.sort_values('timestamp')
                all_logs[node_id] = logs_df
        
        return all_logs
    
    def prepare_logs_for_influxdb(self, logs_data: Dict) -> List[Point]:
        """将日志数据转换为适合InfluxDB的Point对象
        
        Args:
            logs_data: 日志数据，格式为 {node_id: DataFrame}
            
        Returns:
            InfluxDB Point对象列表
        """
        points = []
        
        for node_id, logs_df in logs_data.items():
            for _, row in logs_df.iterrows():
                # 创建日志数据点
                point = Point("node_logs")
                
                # 添加标签
                point = point.tag("node_id", row['node_id'])
                point = point.tag("node_type", row['node_type'])
                point = point.tag("level", row['level'])
                point = point.tag("source", row['source'])
                
                # 添加字段
                point = point.field("message", row['message'])
                if 'metric' in row:
                    point = point.tag("metric", row['metric'])
                if 'metric_value' in row:
                    point = point.field("value", float(row['metric_value']))
                
                # 设置时间戳
                point = point.time(row['timestamp'])
                
                points.append(point)
        
        return points
