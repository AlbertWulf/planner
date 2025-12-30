"""
基于 LLM 的算子

使用 vLLM 服务进行推理的算子。
"""

import json
import requests
from typing import List, Dict, Any, Optional
import time


class VLLMClient:
    """vLLM 客户端，用于调用 vLLM 服务"""
    
    def __init__(self, base_url: str = "http://localhost:8000", model: str = "default"):
        """
        初始化 vLLM 客户端。
        
        Args:
            base_url: vLLM 服务地址
            model: 模型名称
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.completion_url = f"{self.base_url}/v1/completions"
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        调用 vLLM 生成文本。
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            top_p: top_p 采样参数
        
        Returns:
            生成结果字典
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": None
        }
        
        try:
            response = requests.post(
                self.completion_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "text": result["choices"][0]["text"].strip(),
                "usage": result.get("usage", {}),
                "finish_reason": result["choices"][0].get("finish_reason", "stop")
            }
        
        except requests.exceptions.RequestException as e:
            print(f"❌ vLLM 调用失败: {e}")
            return {
                "text": "",
                "usage": {"total_tokens": 0},
                "finish_reason": "error"
            }


class LLMSummarizeOperator:
    """LLM 摘要算子"""
    
    def __init__(
        self,
        vllm_client: VLLMClient,
        max_tokens: int = 200,
        temperature: float = 0.3
    ):
        """
        初始化 LLM 摘要算子。
        
        Args:
            vllm_client: vLLM 客户端
            max_tokens: 最大生成 token 数
            temperature: 温度参数
        """
        self.client = vllm_client
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.total_tokens = 0
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        对每个文档进行摘要。
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            添加了 summary 字段的文档列表
        """
        result = []
        
        for doc in input_data:
            text = doc.get("text", "")
            
            # 构造提示词
            prompt = f"""请对以下医疗文档进行摘要，提取关键医疗信息（患者情况、诊断、处方等）。

文档：
{text}

摘要："""
            
            # 调用 LLM
            response = self.client.generate(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # 统计 tokens
            self.total_tokens += response["usage"].get("total_tokens", 0)
            
            # 添加摘要字段
            doc_copy = doc.copy()
            doc_copy["summary"] = response["text"]
            doc_copy["summary_tokens"] = response["usage"].get("total_tokens", 0)
            result.append(doc_copy)
        
        return result


class LLMFilterOperator:
    """LLM 过滤算子"""
    
    def __init__(
        self,
        vllm_client: VLLMClient,
        filter_criteria: str,
        max_tokens: int = 50,
        temperature: float = 0.1
    ):
        """
        初始化 LLM 过滤算子。
        
        Args:
            vllm_client: vLLM 客户端
            filter_criteria: 过滤标准描述
            max_tokens: 最大生成 token 数
            temperature: 温度参数（过滤任务使用较低温度）
        """
        self.client = vllm_client
        self.filter_criteria = filter_criteria
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.total_tokens = 0
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        使用 LLM 过滤文档。
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            过滤后的文档列表
        """
        result = []
        
        for doc in input_data:
            text = doc.get("text", "")
            
            # 构造提示词
            prompt = f"""判断以下文档是否符合标准：{self.filter_criteria}

文档：
{text}

请只回答"是"或"否"。
答案："""
            
            # 调用 LLM
            response = self.client.generate(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # 统计 tokens
            self.total_tokens += response["usage"].get("total_tokens", 0)
            
            # 判断是否保留
            answer = response["text"].lower()
            if "是" in answer or "yes" in answer or "符合" in answer:
                doc_copy = doc.copy()
                doc_copy["filter_tokens"] = response["usage"].get("total_tokens", 0)
                result.append(doc_copy)
        
        return result


class LLMExtractOperator:
    """LLM 提取算子"""
    
    def __init__(
        self,
        vllm_client: VLLMClient,
        extract_target: str,
        output_field: str = "extracted",
        max_tokens: int = 300,
        temperature: float = 0.2
    ):
        """
        初始化 LLM 提取算子。
        
        Args:
            vllm_client: vLLM 客户端
            extract_target: 提取目标描述（如"药物名称"）
            output_field: 输出字段名
            max_tokens: 最大生成 token 数
            temperature: 温度参数
        """
        self.client = vllm_client
        self.extract_target = extract_target
        self.output_field = output_field
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.total_tokens = 0
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        从文档中提取信息。
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            添加了提取字段的文档列表
        """
        result = []
        
        for doc in input_data:
            text = doc.get("text", "")
            
            # 构造提示词
            prompt = f"""从以下医疗文档中提取{self.extract_target}。请以列表形式输出，每项一行。

文档：
{text}

提取的{self.extract_target}：
"""
            
            # 调用 LLM
            response = self.client.generate(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # 统计 tokens
            self.total_tokens += response["usage"].get("total_tokens", 0)
            
            # 解析提取结果
            extracted_text = response["text"]
            extracted_items = [
                line.strip().lstrip('-').lstrip('*').strip()
                for line in extracted_text.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            
            # 添加提取字段
            doc_copy = doc.copy()
            doc_copy[self.output_field] = extracted_items
            doc_copy["extract_tokens"] = response["usage"].get("total_tokens", 0)
            result.append(doc_copy)
        
        return result


# 全局客户端实例（可配置）
_default_vllm_client: Optional[VLLMClient] = None

def set_default_vllm_client(base_url: str = "http://localhost:8000", model: str = "default"):
    """设置全局默认的 vLLM 客户端"""
    global _default_vllm_client
    _default_vllm_client = VLLMClient(base_url=base_url, model=model)

def get_default_vllm_client() -> VLLMClient:
    """获取全局默认的 vLLM 客户端"""
    global _default_vllm_client
    if _default_vllm_client is None:
        _default_vllm_client = VLLMClient()
    return _default_vllm_client
