import requests
import json
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class LMStudioClient:
    """LM Studio API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:12343"):
        """
        初始化LM Studio客户端
        
        Args:
            base_url: LM Studio API的基础URL
        """
        self.base_url = base_url.rstrip('/')
        # self.model = "deepseek-r1-distill-qwen-32b"
        self.model = "mistral-small-3.1-24b-instruct-2503"
        
    def _make_request(self, endpoint: str, method: str = "POST", **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求到LM Studio API
        
        Args:
            endpoint: API端点
            method: HTTP方法
            **kwargs: 请求参数
            
        Returns:
            API响应
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            raise
            
    def _clean_response(self, response: str) -> str:
        """
        清理响应文本，移除重复内容和特殊标签
        
        Args:
            response: 原始响应文本
            
        Returns:
            清理后的响应文本
        """
        # 移除think标签
        response = response.replace("<think>", "").replace("</think>", "")
        
        # 移除思考过程
        lines = response.split("\n")
        cleaned_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
                
            line = line.strip()
            if not line:
                continue
                
            # 跳过思考过程相关的行
            if any(phrase in line.lower() for phrase in [
                "我现在需要仔细思考",
                "首先，我应该",
                "接下来，我需要",
                "然后，我要",
                "最后，组织",
                "让我思考一下",
                "我需要分析",
                "我应该考虑"
            ]):
                continue
                
            # 增强的重复检测
            is_duplicate = False
            for existing_line in cleaned_lines:
                # 计算相似度（使用更严格的匹配）
                if len(line) > 10:
                    # 检查是否是完整句子的重复
                    if line.endswith(('.', '。', '!', '！', '?', '？')):
                        if line in existing_line or existing_line in line:
                            is_duplicate = True
                            break
                    # 检查是否是部分重复
                    elif len(line) > 20 and (line in existing_line or existing_line in line):
                        is_duplicate = True
                        break
                    
            if not is_duplicate:
                cleaned_lines.append(line)
                
        # 合并行并清理
        cleaned_text = "\n".join(cleaned_lines)
        
        # 移除多余的空行
        cleaned_text = "\n".join(line for line in cleaned_text.split("\n") if line.strip())
        
        return cleaned_text.strip()
            
    def generate(self, 
                prompt: str,
                system_prompt: Optional[str] = None,
                max_tokens: int = 2048,
                temperature: float = 0.7,
                top_p: float = 0.9,
                stop: Optional[List[str]] = None,
                **kwargs) -> str:
        """
        生成文本响应
        
        Args:
            prompt: 输入提示
            system_prompt: 系统提示，可选
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top-p采样参数
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            生成的文本响应
        """
        messages = []
        
        # 添加系统提示
        if system_prompt:
            # 确保系统提示被正确格式化
            messages.append({
                "role": "system",
                "content": system_prompt.strip()
            })
            
        # 添加用户提示
        messages.append({
            "role": "user",
            "content": prompt.strip()
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False
        }
        
        if stop:
            payload["stop"] = stop
            
        for key, value in kwargs.items():
            payload[key] = value
            
        response = self._make_request("/v1/chat/completions", json=payload)
        
        try:
            raw_response = response["choices"][0]["message"]["content"]
            return self._clean_response(raw_response)
        except (KeyError, IndexError) as e:
            logger.error(f"解析响应失败: {str(e)}")
            raise
            
    def get_embeddings(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            文本的嵌入向量
        """
        payload = {
            "model": self.model,
            "input": text
        }
        
        response = self._make_request("/v1/embeddings", json=payload)
        
        try:
            return response["data"][0]["embedding"]
        except (KeyError, IndexError) as e:
            logger.error(f"解析嵌入向量失败: {str(e)}")
            raise 