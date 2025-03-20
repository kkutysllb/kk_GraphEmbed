#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
时序数据生成器测试
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from dynamic_graph_rag.data.simulated.time_series_generator import TimeSeriesGenerator

class TestTimeSeriesGenerator(unittest.TestCase):
    """时序数据生成器测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建测试节点列表
        self.test_nodes = [
            {'id': 'VM_TEST_001', 'type': 'VM', 'name': 'Test VM 1'},
            {'id': 'HOST_TEST_001', 'type': 'HOST', 'name': 'Test Host 1'},
            {'id': 'NE_TEST_001', 'type': 'NE', 'name': 'Test NE 1'}
        ]
        
        # 初始化生成器
        self.generator = TimeSeriesGenerator(nodes_info=self.test_nodes)
        
        # 设置测试时间范围 - 只生成1天的数据以加快测试速度
        self.end_time = datetime.now()
        self.start_time = self.end_time - timedelta(days=1)
    
    def test_metrics_definition(self):
        """测试指标定义"""
        self.assertIn('VM', self.generator.metrics_definition)
        self.assertIn('HOST', self.generator.metrics_definition)
        self.assertIn('NE', self.generator.metrics_definition)
        
        # 检查VM指标
        vm_metrics = self.generator.metrics_definition['VM']
        self.assertIn('cpu_usage', vm_metrics)
        self.assertIn('memory_usage', vm_metrics)
        self.assertIn('disk_io', vm_metrics)
        self.assertIn('network_throughput', vm_metrics)
    
    def test_generate_periodic_pattern(self):
        """测试周期性模式生成"""
        # 创建一天的时间范围，每小时一个点
        time_range = pd.date_range(
            start=self.start_time,
            end=self.end_time,
            freq='1h'
        )
        
        # 生成基本模式
        base_value = 50.0
        values = self.generator.generate_periodic_pattern(
            base_value=base_value,
            volatility='medium',
            time_range=time_range,
            daily_pattern=True,
            weekly_pattern=False
        )
        
        # 验证结果
        self.assertEqual(len(values), len(time_range))
        self.assertTrue(np.all(values >= 0))  # 所有值都应大于等于0
        
        # 检查日模式影响 - 工作时间值应该更高
        business_hours = [9, 10, 11, 12, 13, 14, 15, 16, 17]
        business_values = []
        non_business_values = []
        
        for i, t in enumerate(time_range):
            if t.hour in business_hours:
                business_values.append(values[i])
            else:
                non_business_values.append(values[i])
        
        # 如果有足够的数据点，工作时间的平均值应高于非工作时间
        if business_values and non_business_values:
            self.assertGreater(
                np.mean(business_values),
                np.mean(non_business_values)
            )
    
    def test_add_anomalies(self):
        """测试异常值添加"""
        # 创建一个正常的数组
        normal_values = np.ones(100) * 50.0
        
        # 添加异常值，高概率确保有异常被添加
        anomaly_values = self.generator.add_anomalies(
            values=normal_values,
            anomaly_probability=0.2,
            anomaly_severity='high',
            anomaly_duration=5
        )
        
        # 验证结果
        self.assertEqual(len(anomaly_values), len(normal_values))
        self.assertFalse(np.array_equal(anomaly_values, normal_values))  # 应该有差异
        
        # 计算与原始值差异较大的点的数量
        diff = np.abs(anomaly_values - normal_values)
        anomaly_count = np.sum(diff > 50.0)  # 差异大于基础值的点视为异常
        
        # 应该存在一些异常点
        self.assertGreater(anomaly_count, 0)
    
    def test_generate_metrics_for_node(self):
        """测试为单个节点生成指标数据"""
        # 为VM节点生成指标
        node_info = self.test_nodes[0]  # VM节点
        
        metrics_data = self.generator.generate_metrics_for_node(
            node_info=node_info,
            start_time=self.start_time,
            end_time=self.end_time,
            include_anomalies=True
        )
        
        # 验证结果
        self.assertIsInstance(metrics_data, dict)
        self.assertGreater(len(metrics_data), 0)
        
        # 检查各指标
        for metric_name, df in metrics_data.items():
            self.assertIsInstance(df, pd.DataFrame)
            self.assertGreater(len(df), 0)
            
            # 检查必要的列
            required_columns = ['timestamp', 'value', 'node_id', 'node_type', 'metric', 'unit']
            for col in required_columns:
                self.assertIn(col, df.columns)
            
            # 验证数据
            self.assertEqual(df['node_id'].iloc[0], node_info['id'])
            self.assertEqual(df['node_type'].iloc[0], node_info['type'])
            self.assertEqual(df['metric'].iloc[0], metric_name)
    
    def test_generate_metrics_data(self):
        """测试为所有节点生成指标数据"""
        metrics_data = self.generator.generate_metrics_data(
            start_time=self.start_time,
            end_time=self.end_time,
            include_anomalies=True
        )
        
        # 验证结果
        self.assertIsInstance(metrics_data, dict)
        self.assertEqual(len(metrics_data), len(self.test_nodes))
        
        # 检查每个节点的数据
        for node_info in self.test_nodes:
            node_id = node_info['id']
            self.assertIn(node_id, metrics_data)
            
            node_metrics = metrics_data[node_id]
            self.assertIsInstance(node_metrics, dict)
            self.assertGreater(len(node_metrics), 0)
    
    def test_export_to_csv(self):
        """测试导出到CSV文件"""
        # 生成指标数据
        metrics_data = self.generator.generate_metrics_data(
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # 创建临时输出目录
        test_output_dir = Path(__file__).parent / 'test_output'
        
        # 导出为CSV
        csv_files = self.generator.export_to_csv(
            metrics_data=metrics_data,
            output_dir=str(test_output_dir)
        )
        
        # 验证结果
        self.assertIsInstance(csv_files, list)
        self.assertGreater(len(csv_files), 0)
        
        # 检查文件是否创建
        for file_path in csv_files:
            self.assertTrue(os.path.exists(file_path))
        
        # 清理测试文件
        try:
            import shutil
            shutil.rmtree(test_output_dir)
        except:
            pass
    
    # InfluxDB导入测试在这里省略，因为需要实际的数据库连接
    # 在实际环境中，应该使用模拟对象来测试
    
if __name__ == '__main__':
    unittest.main() 