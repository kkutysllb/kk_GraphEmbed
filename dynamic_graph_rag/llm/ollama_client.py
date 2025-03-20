import requests
import json
from loguru import logger

class OllamaClient:
    def __init__(self, model_name="deepseek-r1:32b", api_base="http://localhost:11434"):
        """
        初始化Ollama客户端
        
        Args:
            model_name: Ollama模型名称，默认使用deepseek-r1:32b
            api_base: Ollama API地址，默认使用本地地址
        """
        self.model_name = model_name
        self.api_base = api_base.rstrip('/')
        logger.info(f"初始化Ollama客户端: model={model_name}, api_base={api_base}")
        
        # 测试API连接
        try:
            self.get_model_info()
            logger.info("成功连接到Ollama API并验证模型可用")
        except Exception as e:
            logger.warning(f"API连接测试失败: {str(e)}")
        
    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2048):
        """
        生成文本响应
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（角色设定）
            temperature: 采样温度
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本响应
        """
        url = f"{self.api_base}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(url, json=payload, stream=True)
            
            if response.status_code != 200:
                error_msg = f"API请求失败: status_code={response.status_code}, response={response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            full_response = ""
            in_think_block = False
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            response_text = chunk['response']
                            # 处理特殊标签
                            if response_text.startswith('<think>'):
                                in_think_block = True
                                continue
                            elif response_text.startswith('</think>'):
                                in_think_block = False
                                continue
                            # 只添加不在think块中的内容
                            if not in_think_block:
                                full_response += response_text
                    except json.JSONDecodeError as e:
                        error_msg = f"JSON解析失败: {str(e)}, line={line}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                        
            if not full_response:
                error_msg = "API返回空响应"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            logger.info("成功生成响应")
            return full_response.strip()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama API调用失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    def get_model_info(self):
        """
        获取模型信息
        
        Returns:
            模型的详细信息
        """
        url = f"{self.api_base}/api/show"
        
        try:
            response = requests.post(url, json={"name": self.model_name})
            response.raise_for_status()
            model_info = response.json()
            logger.info("成功获取模型信息")
            return model_info
        except requests.exceptions.RequestException as e:
            error_msg = f"获取模型信息失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) 