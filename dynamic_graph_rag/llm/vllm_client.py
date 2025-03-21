"""
vLLM客户端模块，用于与本地部署的vLLM服务通信
"""
import json
import requests
from typing import Dict, List, Optional, Union

class VLLMClient:
    """vLLM客户端类"""
    
    def __init__(self, 
                 api_url: str = "http://localhost:8000/v1",
                 model_name: str = "Qwen2.5-vl-7b",
                 temperature: float = 0.3,
                 max_tokens: int = 1024):
        """初始化vLLM客户端
        
        Args:
            api_url: vLLM服务的API地址
            model_name: 模型名称
            temperature: 采样温度
            max_tokens: 最大生成token数
        """
        self.api_url = api_url.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """生成文本
        
        Args:
            prompt: 输入提示
            system_prompt: 系统提示，可选
            
        Returns:
            生成的文本
            
        Raises:
            Exception: 请求失败时抛出异常
        """
        # 构建消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 构建请求数据
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        # 发送请求
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception("无效的响应格式")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求vLLM服务失败: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("解析vLLM响应失败")
        except Exception as e:
            raise Exception(f"调用vLLM服务出错: {str(e)}")
    
    def generate_batch(self, prompts: List[str]) -> List[str]:
        """批量生成文本
        
        Args:
            prompts: 输入提示列表
            
        Returns:
            生成的文本列表
        """
        results = []
        for prompt in prompts:
            try:
                result = self.generate(prompt)
                results.append(result)
            except Exception as e:
                results.append(str(e))
        return results 