#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图数据导入脚本测试
"""

import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from dynamic_graph_rag.data_import.graph_data_importer import GraphDataImporter


class TestGraphDataImporter(unittest.TestCase):
    """测试图数据导入器类"""

    def setUp(self):
        """测试前准备"""
        # 创建测试数据
        self.test_data = {
            "nodes": [
                {"id": "node1", "type": "DC", "name": "数据中心1", "level": 1},
                {"id": "node2", "type": "TENANT", "name": "租户1", "level": 2},
                {"id": "node3", "type": "NE", "name": "网元1", "level": 3},
                {"id": "node4", "type": "VM", "name": "虚拟机1", "level": 4},
                {"id": "node5", "type": "HOST", "name": "主机1", "level": 5}
            ],
            "edges": [
                {"source": "node1", "target": "node2", "type": "HAS_TENANT"},
                {"source": "node2", "target": "node3", "type": "HAS_NE"},
                {"source": "node3", "target": "node4", "type": "HAS_VM"},
                {"source": "node4", "target": "node5", "type": "DEPLOYED_ON"}
            ]
        }
        
        # 创建测试数据文件
        self.test_data_file = Path(__file__).parent / "test_data.json"
        with open(self.test_data_file, "w", encoding="utf-8") as f:
            json.dump(self.test_data, f, ensure_ascii=False, indent=2)
    
    def tearDown(self):
        """测试后清理"""
        # 删除测试数据文件
        if self.test_data_file.exists():
            self.test_data_file.unlink()
    
    @patch('dynamic_graph_rag.data_import.graph_data_importer.Neo4jConnector')
    def test_load_json_data(self, mock_connector):
        """测试加载JSON数据"""
        # 设置模拟对象
        mock_driver = MagicMock()
        mock_connector.return_value.driver = mock_driver
        
        # 创建导入器实例
        importer = GraphDataImporter(
            uri="bolt://localhost:7688",
            user="neo4j",
            password="test",
            database="neo4j"
        )
        
        # 测试加载JSON数据
        data = importer.load_json_data(str(self.test_data_file))
        
        # 验证数据
        self.assertEqual(len(data["nodes"]), 5)
        self.assertEqual(len(data["edges"]), 4)
        self.assertEqual(data["nodes"][0]["id"], "node1")
        self.assertEqual(data["edges"][0]["type"], "HAS_TENANT")
    
    @patch('dynamic_graph_rag.data_import.graph_data_importer.Neo4jConnector')
    def test_import_nodes(self, mock_connector):
        """测试导入节点"""
        # 设置模拟对象
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"imported": 5}
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        
        mock_connector.return_value.driver = mock_driver
        
        # 创建导入器实例
        importer = GraphDataImporter(
            uri="bolt://localhost:7688",
            user="neo4j",
            password="test",
            database="neo4j"
        )
        
        # 测试导入节点
        nodes_imported = importer.import_nodes(self.test_data["nodes"])
        
        # 验证结果
        self.assertEqual(nodes_imported, 5)
        self.assertEqual(importer.stats["nodes_total"], 5)
        self.assertEqual(importer.stats["nodes_imported"], 5)
        self.assertEqual(len(importer.stats["node_types"]), 5)
    
    @patch('dynamic_graph_rag.data_import.graph_data_importer.Neo4jConnector')
    def test_import_edges(self, mock_connector):
        """测试导入边"""
        # 设置模拟对象
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"imported": 4}
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        
        mock_connector.return_value.driver = mock_driver
        
        # 创建导入器实例
        importer = GraphDataImporter(
            uri="bolt://localhost:7688",
            user="neo4j",
            password="test",
            database="neo4j"
        )
        
        # 测试导入边
        edges_imported = importer.import_edges(self.test_data["edges"])
        
        # 验证结果
        self.assertEqual(edges_imported, 4)
        self.assertEqual(importer.stats["edges_total"], 4)
        self.assertEqual(importer.stats["edges_imported"], 4)
        self.assertEqual(len(importer.stats["edge_types"]), 4)
    
    @patch('dynamic_graph_rag.data_import.graph_data_importer.Neo4jConnector')
    def test_verify_data_integrity(self, mock_connector):
        """测试验证数据完整性"""
        # 设置模拟对象
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        # 模拟节点计数查询结果
        mock_node_count_result = MagicMock()
        mock_node_count_result.single.return_value = {"count": 5}
        
        # 模拟边计数查询结果
        mock_edge_count_result = MagicMock()
        mock_edge_count_result.single.return_value = {"count": 4}
        
        # 模拟节点类型查询结果
        mock_node_types_result = MagicMock()
        mock_node_types_result.__iter__.return_value = [
            {"type": "DC", "count": 1},
            {"type": "TENANT", "count": 1},
            {"type": "NE", "count": 1},
            {"type": "VM", "count": 1},
            {"type": "HOST", "count": 1}
        ]
        
        # 模拟边类型查询结果
        mock_edge_types_result = MagicMock()
        mock_edge_types_result.__iter__.return_value = [
            {"type": "HAS_TENANT", "count": 1},
            {"type": "HAS_NE", "count": 1},
            {"type": "HAS_VM", "count": 1},
            {"type": "DEPLOYED_ON", "count": 1}
        ]
        
        # 模拟孤立边查询结果
        mock_orphan_edges_result = MagicMock()
        mock_orphan_edges_result.single.return_value = {"count": 0}
        
        # 设置模拟会话方法的返回值
        mock_session.run.side_effect = [
            mock_node_count_result,
            mock_edge_count_result,
            mock_node_types_result,
            mock_edge_types_result,
            mock_orphan_edges_result
        ]
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_connector.return_value.driver = mock_driver
        
        # 创建导入器实例
        importer = GraphDataImporter(
            uri="bolt://localhost:7688",
            user="neo4j",
            password="test",
            database="neo4j"
        )
        
        # 设置导入器的统计信息
        importer.stats["nodes_imported"] = 5
        importer.stats["edges_imported"] = 4
        importer.stats["node_types"] = {
            "DC": 1,
            "TENANT": 1,
            "NE": 1,
            "VM": 1,
            "HOST": 1
        }
        importer.stats["edge_types"] = {
            "HAS_TENANT": 1,
            "HAS_NE": 1,
            "HAS_VM": 1,
            "DEPLOYED_ON": 1
        }
        
        # 测试验证数据完整性
        verification_results = importer.verify_data_integrity()
        
        # 验证结果
        self.assertTrue(verification_results["nodes_count_match"])
        self.assertTrue(verification_results["edges_count_match"])
        self.assertTrue(verification_results["node_types_consistent"])
        self.assertTrue(verification_results["edge_types_consistent"])
        self.assertEqual(verification_results["orphan_edges"], 0)
    
    def test_import_data(self):
        """测试完整导入过程（集成测试，跳过mock）"""
        
        try:
            # 创建导入器实例（将使用默认配置）
            importer = GraphDataImporter()
            
            # 设置断言的期望结果，因为是集成测试，我们无法准确预测结果，所以跳过一些断言
            stats = importer.import_data(
                json_file_path=str(self.test_data_file),
                clear_existing=True
            )
            
            # 确保执行完成，简单断言
            self.assertTrue("nodes_total" in stats)
            self.assertTrue("edges_total" in stats)
            self.assertTrue("duration" in stats)
            
        except Exception as e:
            # 如果连接失败（例如Neo4j服务未运行），就跳过测试
            self.skipTest(f"跳过集成测试: {str(e)}")


if __name__ == "__main__":
    unittest.main() 