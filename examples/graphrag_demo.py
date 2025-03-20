"""
GraphRAG适配器使用示例
"""
import os
from dynamic_graph_rag.rag.graph_rag_adapter import GraphRAGAdapter

def main():
    # 从环境变量获取配置
    neo4j_config = {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7688"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "graphrag_password")
    }
    
    influxdb_config = {
        "url": os.getenv("INFLUXDB_URL", "http://localhost:8087"),
        "token": os.getenv("INFLUXDB_TOKEN", "graphrag_token"),
        "org": os.getenv("INFLUXDB_ORG", "graphrag_org")
    }
    
    vllm_config = {
        "api_url": os.getenv("VLLM_API_URL", "http://localhost:8000/v1"),
        "model_name": os.getenv("VLLM_MODEL_NAME", "Qwen2.5-vl-7b"),
        "temperature": float(os.getenv("VLLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("VLLM_MAX_TOKENS", "1024"))
    }
    
    # 示例查询
    queries = [
        "查看虚拟机VM_001最近3天的CPU使用率趋势",
        "分析主机HOST_001上所有虚拟机的内存使用情况",
        "检查网络设备NE_001的性能是否异常",
        "查找存储池STORAGEPOOL_001的IOPS波动情况"
    ]
    
    # 初始化适配器
    with GraphRAGAdapter(neo4j_config, influxdb_config, vllm_config) as adapter:
        # 执行查询
        for query in queries:
            print(f"\n执行查询: {query}")
            print("-" * 50)
            
            try:
                result = adapter.query(query)
                print(result)
            except Exception as e:
                print(f"查询失败: {str(e)}")
            
            print("-" * 50)

if __name__ == "__main__":
    main() 