"""
测试GraphRAG适配器的功能
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from dynamic_graph_rag.rag.graph_rag_adapter import GraphRAGAdapter

@pytest.fixture
def mock_neo4j_data():
    """模拟Neo4j数据"""
    return [
        {
            "n": Mock(
                id="1",
                labels=["VM"],
                properties={
                    "name": "vm-001",
                    "status": "running"
                }
            )
        },
        {
            "r": Mock(
                id="100",
                type="DEPLOYED_ON",
                start_node=Mock(id="1"),
                end_node=Mock(id="2"),
                properties={
                    "deploy_time": "2024-03-01"
                }
            )
        }
    ]

@pytest.fixture
def mock_influx_data():
    """模拟InfluxDB数据"""
    return [
        {
            "node_id": "1",
            "metric": "cpu_usage",
            "value": 75.5,
            "time": "2024-03-20T10:00:00Z"
        }
    ]

@pytest.fixture
def adapter():
    """初始化适配器"""
    neo4j_config = {
        "uri": "bolt://localhost:7688",
        "user": "neo4j",
        "password": "test"
    }
    
    influxdb_config = {
        "url": "http://localhost:8087",
        "token": "test",
        "org": "test"
    }
    
    with patch('neo4j.GraphDatabase'), \
         patch('influxdb_client.InfluxDBClient'):
        adapter = GraphRAGAdapter(
            neo4j_config=neo4j_config,
            influxdb_config=influxdb_config,
            openai_api_key="test"
        )
        yield adapter

def test_convert_to_graph_model(adapter, mock_neo4j_data):
    """测试Neo4j数据转换为GraphRAG模型"""
    graph = adapter._convert_to_graph_model(mock_neo4j_data)
    
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 1
    
    node = graph.nodes[0]
    assert node.id == "1"
    assert node.type == "VM"
    assert node.properties["name"] == "vm-001"
    
    edge = graph.edges[0]
    assert edge.id == "100"
    assert edge.type == "DEPLOYED_ON"
    assert edge.source == "1"
    assert edge.target == "2"

def test_get_time_series_data(adapter, mock_influx_data):
    """测试时序数据获取和处理"""
    with patch.object(adapter.query_api, 'query', return_value=mock_influx_data):
        data = adapter._get_time_series_data(
            node_ids=["1"],
            metrics=["cpu_usage"],
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        assert "1" in data
        assert len(data["1"]) == 1
        assert data["1"][0]["metric"] == "cpu_usage"
        assert data["1"][0]["value"] == 75.5

def test_query_processing(adapter):
    """测试查询处理流程"""
    test_query = "查看虚拟机vm-001最近1小时的CPU使用率"
    
    with patch.object(adapter.graphrag, 'generate', return_value=Mock(text="测试结果")):
        result = adapter.query(test_query)
        assert isinstance(result, str)
        assert len(result) > 0

def test_error_handling(adapter):
    """测试错误处理"""
    test_query = "查看不存在的节点"
    
    with patch.object(adapter.graphrag, 'generate', side_effect=Exception("测试错误")):
        result = adapter.query(test_query)
        assert "错误" in result
        assert "建议" in result

def test_resource_management(adapter):
    """测试资源管理"""
    with patch.object(adapter.neo4j_driver, 'close') as mock_neo4j_close, \
         patch.object(adapter.influx_client, 'close') as mock_influx_close:
        
        with adapter:
            pass  # 使用适配器
        
        mock_neo4j_close.assert_called_once()
        mock_influx_close.assert_called_once() 