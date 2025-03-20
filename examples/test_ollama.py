from dynamic_graph_rag.rag.graph_rag_adapter import GraphRAGAdapter
from loguru import logger
import sys

# 配置日志
logger.remove()  # 移除默认的处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

def main():
    try:
        # 初始化适配器，使用Ollama的deepseek-r1:32b模型
        adapter = GraphRAGAdapter(
            model_type="ollama",
            model_name="deepseek-r1:32b"
        )
        
        # 测试简单查询
        query = "你是谁？你能做什么？"
        
        # 设置系统提示
        system_prompt = """你是一个专业的系统分析师，擅长分析系统故障和性能问题。
你可以：
1. 回答关于系统架构的问题
2. 分析系统性能问题
3. 提供故障诊断建议
4. 解答技术相关问题"""
        
        logger.info("开始处理查询...")
        
        # 处理查询
        response = adapter.process_query(
            query=query,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        print("\n系统提示:")
        print(system_prompt)
        print("\n查询:")
        print(query)
        print("\n响应:")
        print(response)
        
    except Exception as e:
        logger.error(f"执行出错: {str(e)}")
        raise

if __name__ == "__main__":
    main() 