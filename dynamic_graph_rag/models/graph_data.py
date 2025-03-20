"""
图数据模型模块
提供对Neo4j图数据的抽象封装和操作
"""

import json
import logging
from typing import Dict, List, Optional, Union, Any
from ..db.neo4j_client import Neo4jClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphData:
    """图数据模型，提供对Neo4j图数据的抽象和操作"""
    
    def __init__(self, neo4j_client=None):
        """初始化图数据模型
        
        Args:
            neo4j_client: 可选的Neo4j客户端实例，如果不提供则创建新实例
        """
        self.client = neo4j_client or Neo4jClient()
        if not self.client.verify_connection():
            self.client.connect()
    
    def import_graph_from_json(self, json_file: str) -> bool:
        """从JSON文件导入图数据
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            是否成功
        """
        return self.client.import_graph_from_json(json_file)
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict]:
        """通过ID获取节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点数据字典或None
        """
        return self.client.get_node_by_id(node_id)
    
    def get_nodes_by_type(self, node_type: str) -> List[Dict]:
        """获取特定类型的所有节点
        
        Args:
            node_type: 节点类型
            
        Returns:
            节点列表
        """
        query = f"""
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
        query = f"""
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
        return self.client.get_node_relationships(node_id, direction)
    
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
    
    def get_path_between_nodes(self, source_id: str, target_id: str, 
                              max_depth: int = 5) -> List[Dict]:
        """获取两个节点之间的路径
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            max_depth: 最大路径深度
            
        Returns:
            路径列表
        """
        query = f"""
        MATCH path = shortestPath((a {{id: $sourceId}})-[*1..{max_depth}]-(b {{id: $targetId}}))
        RETURN path
        """
        results = self.client.execute_query(query, {"sourceId": source_id, "targetId": target_id})
        return [record["path"] for record in results]
    
    def find_nodes_with_property(self, property_name: str, 
                                property_value: Any) -> List[Dict]:
        """查找具有特定属性值的节点
        
        Args:
            property_name: 属性名称
            property_value: 属性值
            
        Returns:
            节点列表
        """
        query = f"""
        MATCH (n)
        WHERE n.{property_name} = $value
        RETURN n
        """
        results = self.client.execute_query(query, {"value": property_value})
        return [record["n"] for record in results]
    
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
            # 处理路径中的节点和关系
            for node in path.nodes:
                nodes.add(node)
            for rel in path.relationships:
                relationships.add(rel)
        
        # 将节点和关系转换为字典
        nodes_list = [self._node_to_dict(node) for node in nodes]
        rels_list = [self._relationship_to_dict(rel) for rel in relationships]
        
        return {
            "nodes": nodes_list,
            "relationships": rels_list
        }

    def get_node_ancestors(self, node_id: str, relationship_types: Optional[List[str]] = None, 
                          max_depth: int = 10) -> List[Dict]:
        """获取节点的所有祖先节点
        
        Args:
            node_id: 节点ID
            relationship_types: 关系类型列表
            max_depth: 最大深度
            
        Returns:
            祖先节点列表
        """
        rel_clause = ""
        if relationship_types:
            rel_types = "|".join(f":{t}" for t in relationship_types)
            rel_clause = f"[r {rel_types}]"
        else:
            rel_clause = "[r]"
            
        query = f"""
        MATCH path = (ancestor)-{rel_clause}*1..{max_depth}->(n {{id: $nodeId}})
        RETURN ancestor
        """
        results = self.client.execute_query(query, {"nodeId": node_id})
        return [record["ancestor"] for record in results]
    
    def get_node_descendants(self, node_id: str, relationship_types: Optional[List[str]] = None, 
                            max_depth: int = 10) -> List[Dict]:
        """获取节点的所有后代节点
        
        Args:
            node_id: 节点ID
            relationship_types: 关系类型列表
            max_depth: 最大深度
            
        Returns:
            后代节点列表
        """
        rel_clause = ""
        if relationship_types:
            rel_types = "|".join(f":{t}" for t in relationship_types)
            rel_clause = f"[r {rel_types}]"
        else:
            rel_clause = "[r]"
            
        query = f"""
        MATCH path = (n {{id: $nodeId}})-{rel_clause}*1..{max_depth}->(descendant)
        RETURN descendant
        """
        results = self.client.execute_query(query, {"nodeId": node_id})
        return [record["descendant"] for record in results]
    
    def get_nodes_by_property_range(self, property_name: str, min_value: Union[int, float], 
                                  max_value: Union[int, float]) -> List[Dict]:
        """通过属性值范围查找节点
        
        Args:
            property_name: 属性名称
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            节点列表
        """
        query = f"""
        MATCH (n)
        WHERE n.{property_name} >= $minValue AND n.{property_name} <= $maxValue
        RETURN n
        """
        results = self.client.execute_query(query, {"minValue": min_value, "maxValue": max_value})
        return [record["n"] for record in results]

    def get_full_graph(self) -> Dict:
        """获取完整的图数据
        
        Returns:
            完整图数据（包含所有节点和边）
        """
        nodes_query = "MATCH (n) RETURN n"
        relationships_query = "MATCH ()-[r]->() RETURN r"
        
        nodes_result = self.client.execute_query(nodes_query)
        relationships_result = self.client.execute_query(relationships_query)
        
        nodes = [self._node_to_dict(record["n"]) for record in nodes_result]
        relationships = [self._relationship_to_dict(record["r"]) for record in relationships_result]
        
        return {
            "nodes": nodes,
            "relationships": relationships
        }
    
    def export_graph_to_json(self, output_file: str) -> bool:
        """将图数据导出到JSON文件
        
        Args:
            output_file: 输出JSON文件路径
            
        Returns:
            是否成功
        """
        graph_data = self.get_full_graph()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            logger.info(f"图数据已成功导出到 {output_file}")
            return True
        except Exception as e:
            logger.error(f"导出图数据失败: {str(e)}")
            return False
    
    def get_node_statistics(self) -> Dict:
        """获取图数据节点统计信息
        
        Returns:
            节点统计信息
        """
        query = """
        MATCH (n)
        RETURN n.type as type, count(*) as count
        """
        results = self.client.execute_query(query)
        stats = {record["type"]: record["count"] for record in results}
        
        # 添加总节点数
        total_query = "MATCH (n) RETURN count(n) as total"
        total_result = self.client.execute_query(total_query)
        stats["total"] = total_result[0]["total"] if total_result else 0
        
        return stats
    
    def get_relationship_statistics(self) -> Dict:
        """获取图数据关系统计信息
        
        Returns:
            关系统计信息
        """
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        """
        results = self.client.execute_query(query)
        stats = {record["type"]: record["count"] for record in results}
        
        # 添加总关系数
        total_query = "MATCH ()-[r]->() RETURN count(r) as total"
        total_result = self.client.execute_query(total_query)
        stats["total"] = total_result[0]["total"] if total_result else 0
        
        return stats
    
    def _node_to_dict(self, node) -> Dict:
        """将Neo4j节点对象转换为字典
        
        Args:
            node: Neo4j节点对象
            
        Returns:
            节点字典
        """
        # 提取节点属性
        props = dict(node)
        # 添加节点ID
        props["id"] = node.id
        return props
    
    def _relationship_to_dict(self, relationship) -> Dict:
        """将Neo4j关系对象转换为字典
        
        Args:
            relationship: Neo4j关系对象
            
        Returns:
            关系字典
        """
        # 提取关系属性
        props = dict(relationship)
        # 添加关系类型和节点IDs
        props["type"] = relationship.type
        props["source"] = relationship.start_node.id
        props["target"] = relationship.end_node.id
        return props
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，确保资源释放"""
        pass 