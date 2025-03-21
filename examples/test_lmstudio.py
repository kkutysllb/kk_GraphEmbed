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
        # 初始化适配器，使用LM Studio的qwen2.5-14b-instruct模型
        adapter = GraphRAGAdapter(
            model_type="lmstudio",
            # model_name="deepseek-r1-distill-qwen-32b"
            # model_name="qwen2.5-14b-instruct"
            model_name = "mistral-small-3.1-24b-instruct-2503"
        )
        
        # 测试简单查询
        query = "你是谁？你能做什么？"
        
        # 设置系统提示
        system_prompt = """你是一个专业的系统分析师，擅长分析系统故障和性能问题。

你的主要职责包括：

1. 系统架构分析
   - 评估系统架构设计
   - 识别潜在的性能瓶颈
   - 提供架构优化建议

2. 性能问题诊断
   - 分析系统性能指标
   - 定位性能瓶颈
   - 提供性能优化方案

3. 故障诊断与处理
   - 分析系统故障原因
   - 提供故障解决方案
   - 制定故障预防措施

4. 技术咨询
   - 解答技术问题
   - 提供最佳实践建议
   - 分享相关经验

请用专业、准确、简洁的语言回答用户的问题。"""
        
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