#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图数据导入脚本 - 从JSON文件导入拓扑图数据到Neo4j
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import click
import pandas as pd
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from dynamic_graph_rag.config.settings import GRAPH_DB_CONFIG
from dynamic_graph_rag.db.neo4j_connector import Neo4jConnector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / 'graph_import.log')
    ]
)
logger = logging.getLogger('graph_importer')

class GraphDataImporter:
    """处理图数据导入的类"""

    def __init__(self, uri=None, user=None, password=None, database=None):
        """
        初始化导入器
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
            database: 数据库名
        """
        # 使用传入参数或默认配置
        self.uri = uri or GRAPH_DB_CONFIG["uri"]
        self.user = user or GRAPH_DB_CONFIG["user"]
        self.password = password or GRAPH_DB_CONFIG["password"]
        self.database = database or GRAPH_DB_CONFIG["database"]
        
        # 连接Neo4j
        self.connector = Neo4jConnector(
            uri=self.uri,
            user=self.user,
            password=self.password,
            database=self.database
        )
        self.driver = self.connector.driver
        
        # 统计信息
        self.stats = {
            "nodes_total": 0,
            "nodes_imported": 0,
            "edges_total": 0,
            "edges_imported": 0,
            "node_types": {},
            "edge_types": {},
            "errors": 0
        }
    
    def load_json_data(self, json_file_path):
        """
        加载JSON文件数据
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            dict: 加载的JSON数据
        """
        logger.info(f"从 {json_file_path} 加载JSON数据")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载JSON数据，大小: {len(str(data))} 字节")
            return data
        except Exception as e:
            logger.error(f"加载JSON文件时出错: {str(e)}")
            raise
    
    def preprocess_nodes(self, nodes):
        """
        预处理节点数据，适应不同的格式
        
        Args:
            nodes: 原始节点列表
            
        Returns:
            list: 处理后的节点列表
        """
        processed_nodes = []
        for node in nodes:
            # 创建新节点对象，包含基本字段
            processed_node = {
                "id": node["id"],
                "type": node["type"],  # 保留type属性，用于统计
                "level": node["level"]
            }
            
            # 处理属性字段
            if "properties" in node and isinstance(node["properties"], dict):
                # 如果有properties子对象，将其展平到节点对象中
                for key, value in node["properties"].items():
                    processed_node[key] = value
            
            # 复制其他直接属性（除了已处理的基本字段和properties外）
            for key, value in node.items():
                if key not in ["id", "type", "level", "properties"]:
                    processed_node[key] = value
            
            processed_nodes.append(processed_node)
        
        return processed_nodes
    
    def preprocess_edges(self, edges):
        """
        预处理边数据，适应不同的格式
        
        Args:
            edges: 原始边列表
            
        Returns:
            list: 处理后的边列表
        """
        processed_edges = []
        for edge in edges:
            # 创建新边对象，包含基本字段
            processed_edge = {
                "source": edge["source"],
                "target": edge["target"],
                "type": edge["type"]  # 保留type属性，用于统计
            }
            
            # 处理属性字段
            if "properties" in edge and isinstance(edge["properties"], dict):
                # 如果有properties子对象，将其展平到边对象中
                for key, value in edge["properties"].items():
                    processed_edge[key] = value
            
            # 复制其他直接属性（除了已处理的基本字段和properties外）
            for key, value in edge.items():
                if key not in ["source", "target", "type", "properties"]:
                    processed_edge[key] = value
            
            processed_edges.append(processed_edge)
        
        return processed_edges
    
    def clear_database(self):
        """清空数据库中的所有节点和关系，同时删除所有索引和约束"""
        logger.warning("正在清空数据库中的所有节点和关系...")
        with self.driver.session(database=self.database) as session:
            # 删除所有节点和关系
            session.run("MATCH (n) DETACH DELETE n")
            
            # 删除所有索引和约束
            try:
                # Neo4j 5.x 语法
                indexes = session.run("SHOW INDEXES").data()
                for index in indexes:
                    index_name = index.get("name")
                    if index_name:
                        session.run(f"DROP INDEX {index_name} IF EXISTS")
                
                constraints = session.run("SHOW CONSTRAINTS").data()
                for constraint in constraints:
                    constraint_name = constraint.get("name")
                    if constraint_name:
                        session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
            except Exception as e:
                logger.warning(f"清除索引和约束时出错: {str(e)}")
                
        logger.info("数据库已清空，所有索引和约束已删除")

    def create_constraints_and_indexes(self):
        """创建必要的约束和索引以提高性能"""
        logger.info("创建约束和索引...")
        
        # 获取所有可能的节点类型，用于创建约束
        node_types = ["DC", "TENANT", "NE", "VM", "HOST", "HOSTGROUP", "TRU"]
        
        constraints_and_indexes = []
        
        # 为每种节点类型创建ID唯一性约束
        for node_type in node_types:
            constraints_and_indexes.append(
                f"CREATE CONSTRAINT {node_type.lower()}_id_unique IF NOT EXISTS FOR (n:{node_type}) REQUIRE n.id IS UNIQUE"
            )
        
        # 创建等级索引
        constraints_and_indexes.append(
            "CREATE INDEX level_index IF NOT EXISTS FOR (n) ON (n.level)"
        )
        
        with self.driver.session(database=self.database) as session:
            for query in constraints_and_indexes:
                try:
                    session.run(query)
                except Exception as e:
                    logger.warning(f"创建约束或索引时出错 ({query}): {str(e)}")
        
        logger.info("约束和索引创建完成")

    def import_nodes(self, nodes):
        """
        导入节点数据，使用正确的Neo4j标签
        
        Args:
            nodes: 节点列表
            
        Returns:
            int: 成功导入的节点数量
        """
        logger.info(f"开始导入 {len(nodes)} 个节点...")
        self.stats["nodes_total"] = len(nodes)
        
        # 预处理节点
        processed_nodes = self.preprocess_nodes(nodes)
        
        # 按节点类型分组，以便为每种类型使用不同的导入查询
        nodes_by_type = {}
        for node in processed_nodes:
            node_type = node.get("type", "UNKNOWN")
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append(node)
            
            # 更新节点类型统计
            if node_type not in self.stats["node_types"]:
                self.stats["node_types"][node_type] = 0
            self.stats["node_types"][node_type] += 1
        
        # 为每种节点类型执行导入
        for node_type, type_nodes in tqdm(nodes_by_type.items(), desc="导入节点类型"):
            # 按批次导入节点
            batch_size = 500
            batches = [type_nodes[i:i + batch_size] for i in range(0, len(type_nodes), batch_size)]
            
            for batch_idx, batch in enumerate(tqdm(batches, desc=f"导入{node_type}类型节点", leave=False)):
                with self.driver.session(database=self.database) as session:
                    try:
                        # 准备批量导入的参数
                        batch_params = {"batch": batch}
                        
                        # 创建批量导入的Cypher查询，使用节点类型作为标签
                        query = f"""
                        UNWIND $batch AS node
                        CREATE (n:{node_type})
                        SET n = node
                        RETURN count(n) AS imported
                        """
                        
                        result = session.run(query, batch_params)
                        imported = result.single()["imported"]
                        self.stats["nodes_imported"] += imported
                        
                    except Exception as e:
                        logger.error(f"导入{node_type}节点批次 {batch_idx+1} 时出错: {str(e)}")
                        self.stats["errors"] += 1
        
        logger.info(f"节点导入完成. 成功导入: {self.stats['nodes_imported']}/{self.stats['nodes_total']}")
        return self.stats["nodes_imported"]

    def import_edges(self, edges):
        """
        导入边数据，使用正确的Neo4j关系类型
        
        Args:
            edges: 边列表
            
        Returns:
            int: 成功导入的边数量
        """
        logger.info(f"开始导入 {len(edges)} 条边...")
        self.stats["edges_total"] = len(edges)
        
        # 预处理边
        processed_edges = self.preprocess_edges(edges)
        
        # 按边类型分组，以便为每种类型使用不同的导入查询
        edges_by_type = {}
        for edge in processed_edges:
            edge_type = edge.get("type", "UNKNOWN")
            if edge_type not in edges_by_type:
                edges_by_type[edge_type] = []
            edges_by_type[edge_type].append(edge)
            
            # 更新边类型统计
            if edge_type not in self.stats["edge_types"]:
                self.stats["edge_types"][edge_type] = 0
            self.stats["edge_types"][edge_type] += 1
        
        # 为每种边类型执行导入
        for edge_type, type_edges in tqdm(edges_by_type.items(), desc="导入边类型"):
            # 按批次导入边
            batch_size = 500
            batches = [type_edges[i:i + batch_size] for i in range(0, len(type_edges), batch_size)]
            
            for batch_idx, batch in enumerate(tqdm(batches, desc=f"导入{edge_type}类型边", leave=False)):
                with self.driver.session(database=self.database) as session:
                    try:
                        # 准备批量导入的参数
                        batch_params = {"batch": batch}
                        
                        # 创建批量导入的Cypher查询，使用边类型作为关系类型
                        query = f"""
                        UNWIND $batch AS edge
                        MATCH (source {{id: edge.source}})
                        MATCH (target {{id: edge.target}})
                        CREATE (source)-[r:{edge_type}]->(target)
                        SET r = edge
                        RETURN count(r) AS imported
                        """
                        
                        result = session.run(query, batch_params)
                        imported = result.single()["imported"]
                        self.stats["edges_imported"] += imported
                        
                    except Exception as e:
                        logger.error(f"导入{edge_type}边批次 {batch_idx+1} 时出错: {str(e)}")
                        self.stats["errors"] += 1
        
        logger.info(f"边导入完成. 成功导入: {self.stats['edges_imported']}/{self.stats['edges_total']}")
        return self.stats["edges_imported"]

    def verify_data_integrity(self):
        """
        验证导入数据的完整性
        
        Returns:
            dict: 验证结果
        """
        logger.info("验证数据完整性...")
        verification_results = {
            "nodes_count_match": False,
            "edges_count_match": False,
            "node_types_consistent": False,
            "edge_types_consistent": False,
            "orphan_edges": 0,
            "node_count_in_db": 0,
            "edge_count_in_db": 0,
            "errors": []
        }
        
        try:
            with self.driver.session(database=self.database) as session:
                # 验证节点总数量
                node_count_result = session.run("MATCH (n) RETURN count(n) AS count").single()
                node_count = node_count_result["count"]
                verification_results["node_count_in_db"] = node_count
                verification_results["nodes_count_match"] = (node_count == self.stats["nodes_imported"])
                
                # 验证边总数量
                edge_count_result = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()
                edge_count = edge_count_result["count"]
                verification_results["edge_count_in_db"] = edge_count
                verification_results["edges_count_match"] = (edge_count == self.stats["edges_imported"])
                
                # 检查每种节点类型的数量
                node_types_in_db = {}
                for node_type in self.stats["node_types"].keys():
                    count_result = session.run(f"MATCH (n:{node_type}) RETURN count(n) AS count").single()
                    node_count = count_result["count"]
                    node_types_in_db[node_type] = node_count
                
                verification_results["node_types_in_db"] = node_types_in_db
                
                # 节点类型一致性检查
                types_consistent = True
                for node_type, count in self.stats["node_types"].items():
                    if node_type not in node_types_in_db or node_types_in_db[node_type] != count:
                        types_consistent = False
                        verification_results["errors"].append(
                            f"节点类型一致性错误: 类型 {node_type}, 预期 {count}, 实际 {node_types_in_db.get(node_type, 0)}"
                        )
                verification_results["node_types_consistent"] = types_consistent
                
                # 检查每种边类型的数量
                edge_types_in_db = {}
                for edge_type in self.stats["edge_types"].keys():
                    count_result = session.run(f"MATCH ()-[r:{edge_type}]->() RETURN count(r) AS count").single()
                    edge_count = count_result["count"]
                    edge_types_in_db[edge_type] = edge_count
                
                verification_results["edge_types_in_db"] = edge_types_in_db
                
                # 边类型一致性检查
                types_consistent = True
                for edge_type, count in self.stats["edge_types"].items():
                    if edge_type not in edge_types_in_db or edge_types_in_db[edge_type] != count:
                        types_consistent = False
                        verification_results["errors"].append(
                            f"边类型一致性错误: 类型 {edge_type}, 预期 {count}, 实际 {edge_types_in_db.get(edge_type, 0)}"
                        )
                verification_results["edge_types_consistent"] = types_consistent
                
                # 检查孤立的边（源节点或目标节点不存在）
                orphan_edges_result = session.run("""
                    MATCH ()-[r]->()
                    WHERE NOT EXISTS(()-[r]->())
                    RETURN count(r) AS count
                """).single()
                verification_results["orphan_edges"] = orphan_edges_result["count"]
                
        except Exception as e:
            logger.error(f"验证数据完整性时出错: {str(e)}")
            verification_results["errors"].append(f"验证过程错误: {str(e)}")
        
        logger.info(f"数据完整性验证完成, 结果: {verification_results}")
        return verification_results

    def generate_import_report(self, verification_results, output_file=None):
        """
        生成导入报告
        
        Args:
            verification_results: 验证结果
            output_file: 输出文件路径
            
        Returns:
            str: 报告内容
        """
        logger.info("生成导入报告...")
        
        report = []
        report.append("# 图数据导入报告")
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("## 导入统计")
        report.append(f"- 节点总数: {self.stats['nodes_total']}")
        report.append(f"- 成功导入节点: {self.stats['nodes_imported']}")
        report.append(f"- 边总数: {self.stats['edges_total']}")
        report.append(f"- 成功导入边: {self.stats['edges_imported']}")
        report.append(f"- 错误数: {self.stats['errors']}")
        report.append("")
        
        report.append("## 节点类型分布")
        for node_type, count in sorted(self.stats["node_types"].items(), key=lambda x: x[1], reverse=True):
            report.append(f"- {node_type}: {count}")
        report.append("")
        
        report.append("## 边类型分布")
        for edge_type, count in sorted(self.stats["edge_types"].items(), key=lambda x: x[1], reverse=True):
            report.append(f"- {edge_type}: {count}")
        report.append("")
        
        report.append("## 数据完整性验证")
        report.append(f"- 节点数量匹配: {'✓' if verification_results['nodes_count_match'] else '✗'}")
        report.append(f"- 边数量匹配: {'✓' if verification_results['edges_count_match'] else '✗'}")
        report.append(f"- 节点类型一致性: {'✓' if verification_results['node_types_consistent'] else '✗'}")
        report.append(f"- 边类型一致性: {'✓' if verification_results['edge_types_consistent'] else '✗'}")
        report.append(f"- 孤立边数量: {verification_results['orphan_edges']}")
        report.append("")
        
        if verification_results["errors"]:
            report.append("## 错误信息")
            for error in verification_results["errors"]:
                report.append(f"- {error}")
            report.append("")
        
        report.append("## 导入结果摘要")
        if (verification_results["nodes_count_match"] and 
            verification_results["edges_count_match"] and 
            verification_results["node_types_consistent"] and 
            verification_results["edge_types_consistent"] and 
            verification_results["orphan_edges"] == 0):
            report.append("✅ 导入成功，所有验证通过")
        else:
            report.append("❌ 导入完成，但存在一些问题，请查看上面的错误信息")
        
        report_content = "\n".join(report)
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                logger.info(f"导入报告已保存到 {output_file}")
            except Exception as e:
                logger.error(f"保存导入报告时出错: {str(e)}")
        
        return report_content

    def import_data(self, json_file_path, clear_existing=False, report_file=None):
        """
        执行完整的导入过程
        
        Args:
            json_file_path: JSON文件路径
            clear_existing: 是否清除现有数据
            report_file: 报告文件路径
            
        Returns:
            dict: 导入结果统计
        """
        start_time = time.time()
        
        try:
            # 1. 加载JSON数据
            graph_data = self.load_json_data(json_file_path)
            
            if not isinstance(graph_data, dict) or "nodes" not in graph_data or "edges" not in graph_data:
                raise ValueError("JSON数据格式不正确，应包含 'nodes' 和 'edges' 键")
            
            # 2. 可选：清空现有数据库
            if clear_existing:
                self.clear_database()
            
            # 3. 创建约束和索引
            self.create_constraints_and_indexes()
            
            # 4. 导入节点数据
            nodes = graph_data["nodes"]
            self.import_nodes(nodes)
            
            # 5. 导入边数据
            edges = graph_data["edges"]
            self.import_edges(edges)
            
            # 6. 验证导入数据的完整性
            verification_results = self.verify_data_integrity()
            
            # 7. 生成导入报告
            report_path = report_file or Path(json_file_path).with_suffix('.report.md')
            self.generate_import_report(verification_results, report_path)
            
            # 8. 完成并返回统计信息
            end_time = time.time()
            self.stats["duration"] = end_time - start_time
            self.stats["verification"] = verification_results
            
            logger.info(f"图数据导入完成，用时 {self.stats['duration']:.2f} 秒")
            return self.stats
            
        except Exception as e:
            logger.error(f"导入过程中发生错误: {str(e)}")
            end_time = time.time()
            self.stats["duration"] = end_time - start_time
            self.stats["error"] = str(e)
            return self.stats

@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--clear', is_flag=True, help='清空Neo4j数据库中的现有数据')
@click.option('--uri', help='Neo4j数据库URI')
@click.option('--user', help='Neo4j用户名')
@click.option('--password', help='Neo4j密码')
@click.option('--database', help='Neo4j数据库名')
@click.option('--report', type=click.Path(), help='导入报告输出路径')
def main(json_file, clear, uri, user, password, database, report):
    """从JSON文件导入图数据到Neo4j数据库"""
    try:
        click.echo(f"开始从 {json_file} 导入数据...")
        
        importer = GraphDataImporter(
            uri=uri,
            user=user,
            password=password,
            database=database
        )
        
        stats = importer.import_data(
            json_file_path=json_file,
            clear_existing=clear,
            report_file=report
        )
        
        # 输出简短摘要
        click.echo("\n导入摘要:")
        click.echo(f"节点: {stats['nodes_imported']}/{stats['nodes_total']} 导入成功")
        click.echo(f"边: {stats['edges_imported']}/{stats['edges_total']} 导入成功")
        click.echo(f"错误数: {stats['errors']}")
        click.echo(f"用时: {stats['duration']:.2f} 秒")
        
        verification = stats.get("verification", {})
        if verification:
            all_good = (verification.get("nodes_count_match", False) and 
                         verification.get("edges_count_match", False) and 
                         verification.get("node_types_consistent", False) and 
                         verification.get("edge_types_consistent", False) and 
                         verification.get("orphan_edges", 1) == 0)
            
            if all_good:
                click.secho("✅ 导入成功，所有验证通过", fg="green")
            else:
                click.secho("❌ 导入完成，但存在一些验证问题", fg="yellow")
        
        # 输出报告位置
        report_path = report or Path(json_file).with_suffix('.report.md')
        click.echo(f"\n完整报告已保存到: {report_path}")
        
    except Exception as e:
        click.secho(f"错误: {str(e)}", fg="red", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 