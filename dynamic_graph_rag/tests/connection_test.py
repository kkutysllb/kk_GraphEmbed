"""
基础设施连接测试脚本
测试Neo4j和InfluxDB连接
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from dynamic_graph_rag.config.settings import get_neo4j_config, get_influxdb_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_neo4j_connection():
    """测试Neo4j数据库连接"""
    logger.info("=== 测试Neo4j连接 ===")
    
    config = get_neo4j_config()
    logger.info(f"连接到Neo4j: {config['uri']}")
    
    try:
        # 建立连接
        driver = GraphDatabase.driver(
            config['uri'], 
            auth=(config['user'], config['password'])
        )
        
        # 验证连接
        with driver.session(database=config['database']) as session:
            result = session.run("RETURN 'Neo4j连接成功' AS message")
            message = result.single()["message"]
            logger.info(f"Neo4j响应: {message}")
            
            # 检查数据库版本
            result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
            record = result.single()
            logger.info(f"数据库: {record['name']}, 版本: {record['versions']}")
            
        driver.close()
        return True
    except Exception as e:
        logger.error(f"Neo4j连接失败: {str(e)}")
        return False

def test_influxdb_connection():
    """测试InfluxDB连接"""
    logger.info("=== 测试InfluxDB连接 ===")
    
    config = get_influxdb_config()
    logger.info(f"连接到InfluxDB: {config['url']}")
    
    try:
        # 初始化客户端
        client = InfluxDBClient(
            url=config['url'],
            token=config['token'],
            org=config['org']
        )
        
        # 检查健康状态
        health = client.health()
        logger.info(f"InfluxDB健康状态: {health.status}")
        
        # 获取可用的桶列表
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        bucket_names = [bucket.name for bucket in buckets]
        logger.info(f"可用桶列表: {bucket_names}")
        
        # 检查指定的桶是否存在
        bucket_exists = config['bucket'] in bucket_names
        if not bucket_exists:
            logger.warning(f"指定的桶 '{config['bucket']}' 不存在，将创建它")
            # 创建桶
            buckets_api.create_bucket(bucket_name=config['bucket'], org=config['org'])
            logger.info(f"已创建桶: {config['bucket']}")
            
        # 写入测试数据点
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = Point("test_measurement") \
            .tag("test_tag", "connection_test") \
            .field("test_value", 100) \
            .time(datetime.utcnow())
            
        write_api.write(bucket=config['bucket'], record=point)
        logger.info("测试数据点写入成功")
        
        # 查询测试数据
        query = f'''
        from(bucket: "{config['bucket']}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "test_measurement")
          |> filter(fn: (r) => r["test_tag"] == "connection_test")
          |> last()
        '''
        
        query_api = client.query_api()
        result = query_api.query(query=query, org=config['org'])
        
        if result and len(result) > 0:
            logger.info("查询测试数据成功")
            for table in result:
                for record in table.records:
                    logger.info(f"查询结果: {record.values}")
                    
        # 清理测试数据
        delete_api = client.delete_api()
        delete_api.delete(
            start="1970-01-01T00:00:00Z",
            stop=datetime.utcnow().isoformat() + "Z",
            predicate='_measurement="test_measurement" AND test_tag="connection_test"',
            bucket=config['bucket'],
            org=config['org']
        )
        logger.info("测试数据已清理")
        
        client.close()
        return True
    except Exception as e:
        logger.error(f"InfluxDB连接失败: {str(e)}")
        return False

def main():
    """主函数，运行所有连接测试"""
    logger.info("开始基础设施连接测试")
    
    neo4j_success = test_neo4j_connection()
    logger.info(f"Neo4j连接测试: {'成功' if neo4j_success else '失败'}")
    
    influxdb_success = test_influxdb_connection()
    logger.info(f"InfluxDB连接测试: {'成功' if influxdb_success else '失败'}")
    
    if neo4j_success and influxdb_success:
        logger.info("所有连接测试通过!")
        return 0
    else:
        logger.error("部分连接测试失败!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 