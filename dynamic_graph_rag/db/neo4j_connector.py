#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Neo4j数据库连接器模块
"""

import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)

class Neo4jConnector:
    """Neo4j数据库连接器类"""
    
    def __init__(self, uri, user, password, database=None):
        """
        初始化Neo4j连接器
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
            database: 数据库名
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            logger.info(f"已初始化Neo4j连接: {self.uri}")
            
            # 测试连接
            self._test_connection()
            
        except Exception as e:
            logger.error(f"连接Neo4j时出错: {str(e)}")
            raise
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                assert record["test"] == 1
                logger.info("Neo4j连接测试成功")
                
                # 获取数据库版本
                version_result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
                for record in version_result:
                    if record["name"] == "Neo4j Kernel":
                        logger.info(f"Neo4j版本: {record['versions'][0]}")
                        break
                
        except ServiceUnavailable as e:
            logger.error(f"Neo4j服务不可用: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"测试Neo4j连接时出错: {str(e)}")
            raise
    
    def close(self):
        """关闭Neo4j连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j连接已关闭")
    
    def execute_query(self, query, parameters=None, database=None):
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            database: 数据库名（覆盖默认值）
            
        Returns:
            list: 查询结果记录列表
        """
        db = database or self.database
        
        try:
            with self.driver.session(database=db) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
                
        except Exception as e:
            logger.error(f"执行查询时出错: {str(e)}")
            logger.error(f"查询: {query}")
            logger.error(f"参数: {parameters}")
            raise
    
    def execute_write_transaction(self, tx_function, *args, database=None):
        """
        执行写入事务
        
        Args:
            tx_function: 事务函数
            args: 传递给事务函数的参数
            database: 数据库名（覆盖默认值）
            
        Returns:
            任何事务函数返回的结果
        """
        db = database or self.database
        
        with self.driver.session(database=db) as session:
            return session.write_transaction(tx_function, *args)
    
    def execute_read_transaction(self, tx_function, *args, database=None):
        """
        执行读取事务
        
        Args:
            tx_function: 事务函数
            args: 传递给事务函数的参数
            database: 数据库名（覆盖默认值）
            
        Returns:
            任何事务函数返回的结果
        """
        db = database or self.database
        
        with self.driver.session(database=db) as session:
            return session.read_transaction(tx_function, *args)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，关闭连接"""
        self.close() 