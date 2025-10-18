"""
BM25 检索器：基于 Title 和 Overview 的关键词检索
"""

import json
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path
from rank_bm25 import BM25Okapi
import numpy as np


class BM25Retriever:
    """
    BM25 检索器（基于 knowledge_base_structured.json）
    """
    
    def __init__(self, kb_json_path: str = None):
        """
        初始化 BM25 检索器
        
        Args:
            kb_json_path: knowledge_base_structured.json 路径
        """
        if kb_json_path is None:
            # 默认路径：相对于 rag_module
            kb_json_path = Path(__file__).parent.parent.parent.parent / "knowledge_base_structured.json"
        
        self.kb_json_path = str(kb_json_path)
        
        if not os.path.exists(self.kb_json_path):
            raise FileNotFoundError(f"Knowledge base not found: {self.kb_json_path}")
        
        # 加载知识库
        with open(self.kb_json_path, 'r', encoding='utf-8') as f:
            self.sops = json.load(f)
        
        print(f"BM25: Loaded {len(self.sops)} SOPs from {self.kb_json_path}")
        
        # 为每个 SOP 构建 Title + Overview 文本
        self.sop_texts = []
        for sop in self.sops:
            title = sop.get("Title", "")
            overview = sop.get("Overview", "")
            text = f"{title} {overview}"
            self.sop_texts.append(text)
        
        # 分词（简单空格分词）
        self.tokenized_corpus = [self._tokenize(text) for text in self.sop_texts]
        
        # 初始化 BM25
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        print(f"BM25: Initialized with {len(self.tokenized_corpus)} documents")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        分词（可扩展为更复杂的分词器）
        
        Args:
            text: 输入文本
        
        Returns:
            Token 列表
        """
        # 转小写 + 空格分词
        tokens = text.lower().split()
        
        # 移除标点符号
        tokens = [token.strip('.,;:!?()[]{}"\'-') for token in tokens]
        
        # 过滤空字符串
        tokens = [t for t in tokens if t]
        
        return tokens
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        BM25 检索
        
        Args:
            query: 查询字符串
            k: 返回 Top-K 结果
        
        Returns:
            List of (SOP dict, BM25 score) tuples
        """
        # 分词查询
        tokenized_query = self._tokenize(query)
        
        # 计算 BM25 分数
        scores = self.bm25.get_scores(tokenized_query)
        
        # 获取 Top-K 索引
        top_k_indices = np.argsort(scores)[::-1][:k]
        
        # 构建结果
        results = []
        for idx in top_k_indices:
            sop = self.sops[idx]
            score = float(scores[idx])
            results.append((sop, score))
        
        return results
    
    def normalize_scores(self, results: List[Tuple[Dict, float]]) -> List[Tuple[Dict, float]]:
        """
        归一化 BM25 分数到 [0, 1]
        
        Args:
            results: [(SOP, raw_score), ...]
        
        Returns:
            [(SOP, normalized_score), ...]
        """
        if not results:
            return []
        
        scores = [score for _, score in results]
        
        min_score = min(scores)
        max_score = max(scores)
        
        # 避免除零
        if max_score == min_score:
            normalized_results = [(sop, 1.0) for sop, _ in results]
        else:
            normalized_results = [
                (sop, (score - min_score) / (max_score - min_score))
                for sop, score in results
            ]
        
        return normalized_results
    
    def search_normalized(self, query: str, k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        BM25 检索并归一化分数
        
        Args:
            query: 查询字符串
            k: Top-K
        
        Returns:
            [(SOP, normalized_score), ...]
        """
        results = self.search(query, k)
        return self.normalize_scores(results)