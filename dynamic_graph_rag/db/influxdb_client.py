"""
InfluxDB时序数据库连接模块
提供时序数据库连接和基本操作功能
"""

import logging
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from ..config.settings import get_influxdb_config, NODE_TYPES

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InfluxDBManager:
    """InfluxDB时序数据库管理器"""
    
    def __init__(self, url=None, token=None, org=None, bucket=None):
        """初始化InfluxDB连接
        
        Args:
            url: InfluxDB服务器URL，默认从配置文件读取
            token: 访问令牌，默认从配置文件读取
            org: 组织名称，默认从配置文件读取
            bucket: 存储桶，默认从配置文件读取
        """
        config = get_influxdb_config()
        self.url = url or config["url"]
        self.token = token or config["token"]
        self.org = org or config["org"]
        self.bucket = bucket or config["bucket"]
        self.client = None
        self.write_api = None
        self.query_api = None
        
    def connect(self):
        """建立与InfluxDB数据库的连接"""
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            self.delete_api = self.client.delete_api()
            logger.info(f"已成功连接到InfluxDB: {self.url}")
            
            # 检查存储桶是否存在，不存在则创建
            self._ensure_bucket_exists()
            
            return True
        except Exception as e:
            logger.error(f"InfluxDB连接失败: {str(e)}")
            return False
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在，如不存在则创建"""
        try:
            buckets_api = self.client.buckets_api()
            buckets = buckets_api.find_buckets().buckets
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.bucket not in bucket_names:
                logger.info(f"创建存储桶: {self.bucket}")
                buckets_api.create_bucket(bucket_name=self.bucket, org=self.org)
                
            return True
        except Exception as e:
            logger.error(f"检查/创建存储桶失败: {str(e)}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.close()
            logger.info("InfluxDB连接已关闭")
    
    def verify_connection(self):
        """验证数据库连接"""
        if not self.client:
            return self.connect()
        
        try:
            health = self.client.health()
            if health.status == "pass":
                logger.info("InfluxDB连接正常")
                return True
            else:
                logger.warning(f"InfluxDB健康检查未通过: {health.message}")
                return False
        except Exception as e:
            logger.error(f"InfluxDB连接验证失败: {str(e)}")
            self.client = None
            return False
    
    def write_metrics(self, measurement, tags, fields, timestamp=None):
        """写入指标数据
        
        Args:
            measurement: 度量名称
            tags: 标签字典，如 {"node_id": "VM_001", "node_type": "VM"}
            fields: 字段字典，如 {"cpu_usage": 45.2, "memory_usage": 60.5}
            timestamp: 时间戳，默认为当前时间
            
        Returns:
            是否成功
        """
        if not self.client:
            if not self.connect():
                return False
        
        try:
            point = Point(measurement)
            
            # 添加标签
            for tag_key, tag_value in tags.items():
                point = point.tag(tag_key, tag_value)
                
            # 添加字段
            for field_key, field_value in fields.items():
                point = point.field(field_key, field_value)
                
            # 设置时间戳
            if timestamp:
                point = point.time(timestamp)
                
            # 写入数据
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            logger.error(f"写入指标失败: {str(e)}")
            return False
    
    def write_metrics_batch(self, points_list):
        """批量写入指标数据
        
        Args:
            points_list: Point对象列表
            
        Returns:
            是否成功
        """
        if not self.client:
            if not self.connect():
                return False
        
        try:
            self.write_api.write(bucket=self.bucket, record=points_list)
            return True
        except Exception as e:
            logger.error(f"批量写入指标失败: {str(e)}")
            return False
    
    def query_metrics(self, measurement, node_id=None, fields=None, start_time=None, end_time=None):
        """查询指标数据
        
        Args:
            measurement: 度量名称
            node_id: 节点ID（可选）
            fields: 需要查询的字段列表（可选）
            start_time: 开始时间，如 "-1h"（可选）
            end_time: 结束时间（可选）
            
        Returns:
            包含查询结果的DataFrame
        """
        if not self.client:
            if not self.connect():
                return None
        
        try:
            # 构建Flux查询
            query = f'from(bucket: "{self.bucket}") |> range(start: {start_time or "-1h"})'
            
            if end_time:
                query += f', stop: {end_time}'
                
            query += f' |> filter(fn: (r) => r._measurement == "{measurement}")'
            
            if node_id:
                query += f' |> filter(fn: (r) => r.node_id == "{node_id}")'
                
            if fields:
                field_filters = ' or '.join([f'r._field == "{field}"' for field in fields])
                query += f' |> filter(fn: (r) => {field_filters})'
                
            # 执行查询
            tables = self.query_api.query_data_frame(query=query)
            
            # 如果结果是空的
            if tables is None or (isinstance(tables, pd.DataFrame) and tables.empty):
                return pd.DataFrame()
                
            # 如果结果是DataFrame列表，合并它们
            if isinstance(tables, list):
                if not tables:
                    return pd.DataFrame()
                tables = pd.concat(tables)
                
            return tables
        except Exception as e:
            logger.error(f"查询指标失败: {str(e)}")
            return None
    
    def delete_metrics(self, measurement=None, node_id=None, start_time=None, end_time=None):
        """删除指标数据
        
        Args:
            measurement: 度量名称（可选）
            node_id: 节点ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            
        Returns:
            是否成功
        """
        if not self.client:
            if not self.connect():
                return False
        
        try:
            # 构建删除条件
            predicate = []
            
            if measurement:
                predicate.append(f'_measurement="{measurement}"')
                
            if node_id:
                predicate.append(f'node_id="{node_id}"')
                
            # 如果没有指定条件，为安全起见不执行删除
            if not predicate:
                logger.warning("删除请求未指定条件，操作已取消")
                return False
                
            predicate_str = ' AND '.join(predicate)
            
            # 执行删除
            self.delete_api.delete(
                start=start_time or "1970-01-01T00:00:00Z",
                stop=end_time or "2099-12-31T23:59:59Z",
                predicate=predicate_str,
                bucket=self.bucket,
                org=self.org
            )
            
            logger.info(f"删除指标成功，条件: {predicate_str}")
            return True
        except Exception as e:
            logger.error(f"删除指标失败: {str(e)}")
            return False
    
    def import_csv_metrics(self, csv_file, measurement, time_column='timestamp', tag_columns=None, field_columns=None):
        """从CSV文件导入指标数据
        
        Args:
            csv_file: CSV文件路径
            measurement: 度量名称
            time_column: 时间列名称（默认'timestamp'）
            tag_columns: 标签列名称列表
            field_columns: 字段列名称列表
            
        Returns:
            导入的点数量
        """
        if not self.client:
            if not self.connect():
                return 0
        
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_file)
            
            # 确保时间列是datetime类型
            df[time_column] = pd.to_datetime(df[time_column])
            
            # 默认标签和字段列
            if tag_columns is None:
                tag_columns = ['node_id', 'node_type']
            
            if field_columns is None:
                # 除了时间列和标签列以外的所有列都作为字段
                field_columns = [col for col in df.columns if col != time_column and col not in tag_columns]
            
            # 创建Point对象列表
            points = []
            for _, row in df.iterrows():
                point = Point(measurement)
                
                # 添加标签
                for tag_col in tag_columns:
                    if tag_col in row and not pd.isna(row[tag_col]):
                        point = point.tag(tag_col, str(row[tag_col]))
                
                # 添加字段
                for field_col in field_columns:
                    if field_col in row and not pd.isna(row[field_col]):
                        # 尝试转换为适当的类型
                        value = row[field_col]
                        if isinstance(value, (int, float)):
                            point = point.field(field_col, value)
                        elif isinstance(value, str) and value.lower() in ('true', 'false'):
                            point = point.field(field_col, value.lower() == 'true')
                        else:
                            point = point.field(field_col, str(value))
                
                # 设置时间戳
                point = point.time(row[time_column])
                
                points.append(point)
            
            # 批量写入
            if points:
                self.write_api.write(bucket=self.bucket, record=points)
                
            logger.info(f"从CSV导入了 {len(points)} 个数据点到 {measurement}")
            return len(points)
        except Exception as e:
            logger.error(f"从CSV导入指标失败: {str(e)}")
            return 0
    
    def export_metrics_to_csv(self, measurement, output_file, node_id=None, start_time=None, end_time=None):
        """将指标数据导出到CSV文件
        
        Args:
            measurement: 度量名称
            output_file: 输出CSV文件路径
            node_id: 节点ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            
        Returns:
            导出的行数
        """
        # 查询数据
        df = self.query_metrics(measurement, node_id, None, start_time, end_time)
        
        if df is None or df.empty:
            logger.warning(f"没有找到数据，导出取消: {measurement}")
            return 0
        
        try:
            # 重新组织数据格式，转换宽表格式
            pivot_df = df.pivot_table(
                index=['_time', 'node_id', 'node_type'],
                columns='_field',
                values='_value'
            ).reset_index()
            
            # 重命名列
            pivot_df = pivot_df.rename(columns={'_time': 'timestamp'})
            
            # 保存到CSV
            pivot_df.to_csv(output_file, index=False)
            
            logger.info(f"成功导出 {len(pivot_df)} 行数据到 {output_file}")
            return len(pivot_df)
        except Exception as e:
            logger.error(f"导出指标到CSV失败: {str(e)}")
            return 0
    
    def get_node_type_metrics(self, node_type, node_id, start_time=None, end_time=None):
        """获取特定类型节点的指标
        
        Args:
            node_type: 节点类型，如'VM', 'HOST'
            node_id: 节点ID
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            
        Returns:
            包含指标的DataFrame
        """
        # 查找节点类型对应的度量名称
        if node_type.upper() not in NODE_TYPES:
            logger.error(f"未知的节点类型: {node_type}")
            return None
        
        measurement = NODE_TYPES[node_type.upper()]['measurement']
        metrics = NODE_TYPES[node_type.upper()]['metrics']
        
        return self.query_metrics(measurement, node_id, metrics, start_time, end_time)
    
    def __enter__(self):
        """上下文管理器入口，确保连接建立"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，确保资源释放"""
        self.close() 