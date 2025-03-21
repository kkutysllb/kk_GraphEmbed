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
        # 初始化适配器，使用vLLM的Qwen2.5-vl-7b模型
        adapter = GraphRAGAdapter(
            model_type="vllm",
            model_name="/home/libing/kk_LLMs/Qwen2.5-7b-1m",
            api_base="http://localhost:8000/v1"
        )
        
        # 测试简单查询
        query = "作为一个系统分析师，请分析一下当前系统的架构和性能特点。"
        
        # 设置系统提示
        system_prompt = """你是一个专业的系统分析师，你的主要职责是分析和解决系统相关的问题。
你必须：
1. 始终以系统分析师的身份回答
2. 专注于系统架构、性能、故障诊断等领域
3. 使用专业的技术术语
4. 提供具体的技术分析和建议
5. 如果问题超出系统分析范围，请明确指出

你的专业领域包括：
- 系统架构设计和优化
- 性能问题分析和调优
- 故障诊断和根因分析
- 系统监控和运维
- 技术架构咨询

注意：你必须始终以系统分析师的身份回答，不要偏离这个角色定位。"""
        
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