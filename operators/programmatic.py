"""
预编程算子（不使用 LLM）

包括数据读取、基于规则的过滤、统计等操作。
"""

import json
from typing import List, Dict, Any
import re


class ReadJsonOperator:
    """读取 JSON 文件算子"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def execute(self, input_data: Any = None) -> List[Dict]:
        """
        读取 JSON 文件。
        
        Returns:
            文档列表
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data


class KeywordFilterOperator:
    """基于关键词的过滤算子（规则based）"""
    
    def __init__(self, keywords: List[str], mode: str = "any"):
        """
        初始化关键词过滤器。
        
        Args:
            keywords: 关键词列表
            mode: "any" (包含任意关键词) 或 "all" (包含所有关键词)
        """
        self.keywords = keywords
        self.mode = mode
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        过滤包含指定关键词的文档。
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            过滤后的文档列表
        """
        filtered = []
        
        for doc in input_data:
            text = doc.get("text", "").lower()
            
            if self.mode == "any":
                # 包含任意关键词
                if any(keyword.lower() in text for keyword in self.keywords):
                    filtered.append(doc)
            else:
                # 包含所有关键词
                if all(keyword.lower() in text for keyword in self.keywords):
                    filtered.append(doc)
        
        return filtered


class CountTokensOperator:
    """统计 token 数量算子"""
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        为每个文档添加 token 计数。
        
        简化实现：按字符数估算（中文约1字=1token，英文约4字符=1token）
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            添加了 token_count 字段的文档列表
        """
        result = []
        
        for doc in input_data:
            text = doc.get("text", "")
            
            # 简单估算：中文字符数 + 英文字符数/4
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            
            estimated_tokens = chinese_chars + (english_chars // 4)
            
            doc_copy = doc.copy()
            doc_copy["token_count"] = estimated_tokens
            result.append(doc_copy)
        
        return result


class RegexExtractOperator:
    """基于正则表达式的提取算子"""
    
    def __init__(self, pattern: str, field_name: str):
        """
        初始化正则提取器。
        
        Args:
            pattern: 正则表达式模式
            field_name: 提取结果存储的字段名
        """
        self.pattern = re.compile(pattern)
        self.field_name = field_name
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        使用正则表达式提取信息。
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            添加了提取字段的文档列表
        """
        result = []
        
        for doc in input_data:
            text = doc.get("text", "")
            matches = self.pattern.findall(text)
            
            doc_copy = doc.copy()
            doc_copy[self.field_name] = matches
            result.append(doc_copy)
        
        return result


class DeduplicateOperator:
    """去重算子"""
    
    def __init__(self, key_field: str = "id"):
        """
        初始化去重器。
        
        Args:
            key_field: 用于判断重复的字段
        """
        self.key_field = key_field
    
    def execute(self, input_data: List[Dict]) -> List[Dict]:
        """
        根据指定字段去重。
        
        Args:
            input_data: 输入文档列表
        
        Returns:
            去重后的文档列表
        """
        seen = set()
        result = []
        
        for doc in input_data:
            key = doc.get(self.key_field)
            if key and key not in seen:
                seen.add(key)
                result.append(doc)
        
        return result
