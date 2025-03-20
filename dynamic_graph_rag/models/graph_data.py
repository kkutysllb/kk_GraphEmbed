"""
图数据模型模块
提供对Neo4j图数据的查询和分析功能
"""

import logging
from typing import Dict, List, Optional, Union, Any
from ..db.neo4j_connector import Neo4jConnector
from ..config.settings import GRAPH_DB_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphData:
    """图数据模型，提供对Neo4j图数据的查询和分析功能"""
    
    def __init__(self, neo4j_client=None):
        """初始化图数据模型
        
        Args:
            neo4j_client: 可选的Neo4j客户端实例，如果不提供则创建新实例
        """
        self.client = neo4j_client or Neo4jConnector(
            uri=GRAPH_DB_CONFIG["uri"],
            user=GRAPH_DB_CONFIG["user"],
            password=GRAPH_DB_CONFIG["password"],
            database=GRAPH_DB_CONFIG["database"]
        )
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict]:
        """通过ID获取节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点数据字典或None
        """
        query = """
        MATCH (n {id: $id}) 
        RETURN n
        """
        results = self.client.execute_query(query, {"id": node_id})
        return results[0]["n"] if results else None
    
    def get_nodes_by_type(self, node_type: str) -> List[Dict]:
        """获取特定类型的所有节点
        
        Args:
            node_type: 节点类型
            
        Returns:
            节点列表
        """
        query = """
        MATCH (n) 
        WHERE n.type = $type 
        RETURN n
        """
        results = self.client.execute_query(query, {"type": node_type})
        return [record["n"] for record in results]
    
    def get_nodes_by_level(self, level: int) -> List[Dict]:
        """获取特定层级的所有节点
        
        Args:
            level: 节点层级
            
        Returns:
            节点列表
        """
        query = """
        MATCH (n) 
        WHERE n.level = $level 
        RETURN n
        """
        results = self.client.execute_query(query, {"level": level})
        return [record["n"] for record in results]
    
    def get_node_relationships(self, node_id: str, direction: str = "both") -> List[Dict]:
        """获取节点的关系
        
        Args:
            node_id: 节点ID
            direction: 关系方向，'in', 'out' 或 'both'
            
        Returns:
            关系列表
        """
        if direction == "out":
            query = """
            MATCH (n {id: $id})-[r]->() 
            RETURN r
            """
        elif direction == "in":
            query = """
            MATCH (n {id: $id})<-[r]-() 
            RETURN r
            """
        else:
            query = """
            MATCH (n {id: $id})-[r]-() 
            RETURN r
            """
        results = self.client.execute_query(query, {"id": node_id})
        return [record["r"] for record in results]
    
    def get_connected_nodes(self, node_id: str, relationship_type: Optional[str] = None, 
                          direction: str = "out") -> List[Dict]:
        """获取与指定节点相连的节点
        
        Args:
            node_id: 源节点ID
            relationship_type: 可选的关系类型
            direction: 关系方向，'in', 'out' 或 'both'
            
        Returns:
            节点列表
        """
        direction_clause = ""
        if direction == "out":
            direction_clause = "-[r]->"
        elif direction == "in":
            direction_clause = "<-[r]-"
        else:
            direction_clause = "-[r]-"
            
        relationship_clause = ""
        if relationship_type:
            relationship_clause = f":{relationship_type}"
            
        query = f"""
        MATCH (a {{id: $nodeId}}){direction_clause}(b)
        WHERE type(r){relationship_clause}
        RETURN b
        """
        results = self.client.execute_query(query, {"nodeId": node_id})
        return [record["b"] for record in results]
    
    def find_subgraph(self, node_id: str, depth: int = 1) -> Dict:
        """查找以节点为中心的子图
        
        Args:
            node_id: 中心节点ID
            depth: 遍历深度
            
        Returns:
            子图数据（包含节点和边）
        """
        query = f"""
        MATCH path = (n {{id: $nodeId}})-[*0..{depth}]-(related)
        RETURN path
        """
        results = self.client.execute_query(query, {"nodeId": node_id})
        
        nodes = set()
        relationships = set()
        
        for record in results:
            path = record["path"]
            for node in path.nodes:
                nodes.add(node)
            for rel in path.relationships:
                relationships.add(rel)
        
        return {
            "nodes": list(nodes),
            "relationships": list(relationships)
        }
    
    def get_graph_statistics(self) -> Dict:
        """获取图的统计信息
        
        Returns:
            包含统计信息的字典
        """
        stats = {}
        
        # 获取节点统计
        node_stats_query = """
        MATCH (n)
        RETURN n.type as type, count(*) as count
        """
        results = self.client.execute_query(node_stats_query)
        stats["nodes"] = {record["type"]: record["count"] for record in results}
        
        # 获取关系统计
        rel_stats_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        """
        results = self.client.execute_query(rel_stats_query)
        stats["relationships"] = {record["type"]: record["count"] for record in results}
        
        return stats 