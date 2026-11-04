"""
文档工具模块
提供文档检索、片段读取、元数据查询和用户交互工具
"""
import json
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent / "data"
FAQ_FILE = DATA_DIR / "faq_v1.json"


def _load_faq(data_file: Optional[Path] = None) -> list[dict]:
    """加载 FAQ 文档库"""
    file_path = data_file or FAQ_FILE
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_fault(fault_config: Optional[dict], tool_name: str) -> Optional[dict]:
    """
    检查是否触发故障注入
    
    Args:
        fault_config: 故障配置 {"tool": 名称, "mode": "error", "times": N}
        tool_name: 当前工具名称
    
    Returns:
        如果触发故障返回错误响应，否则返回 None
    """
    if not fault_config:
        return None
    
    if fault_config.get("tool") == tool_name and fault_config.get("mode") == "error":
        return {
            "status": "error",
            "error": f"工具 {tool_name} 调用失败：模拟故障（第 {fault_config.get('times', 1)} 次）"
        }
    
    return None


def search_docs(
    query: str, 
    top_k: int = 5,
    _fault: Optional[dict] = None,
    _data_file: Optional[Path] = None
) -> dict:
    """
    搜索文档，返回匹配的片段
    
    Args:
        query: 搜索关键词
        top_k: 返回最多 top_k 个结果
        _fault: 故障注入配置
        _data_file: 数据文件路径（测试用）
    
    Returns:
        {status: ok|empty|error, hits: [...], error: ...}
    """
    fault_resp = _check_fault(_fault, "search_docs")
    if fault_resp:
        return fault_resp
    
    try:
        documents = _load_faq(_data_file)
        
        if not documents:
            return {
                "status": "empty",
                "hits": [],
                "error": None
            }
        
        query_lower = query.lower()
        
        # 改进的分词策略：
        # 1. 先尝试按空格分词（英文）
        # 2. 如果没有空格，使用滑动窗口提取 2-4 字符的词组（中文）
        keywords = query_lower.split()
        if len(keywords) == 1 and len(keywords[0]) > 2:
            # 中文查询，提取 2-4 字符的词组
            query_text = keywords[0]
            keywords = []
            for window_size in [4, 3, 2]:
                for i in range(len(query_text) - window_size + 1):
                    keyword = query_text[i:i+window_size]
                    if keyword not in keywords:
                        keywords.append(keyword)
        
        scored_hits = []
        for doc in documents:
            for snippet in doc.get("snippets", []):
                score = 0
                text = snippet["text"].lower()
                title = doc["title"].lower()
                
                for keyword in keywords:
                    if keyword in text:
                        score += text.count(keyword)
                    if keyword in title:
                        score += title.count(keyword) * 2
                
                if score > 0:
                    scored_hits.append({
                        "doc_id": doc["doc_id"],
                        "title": doc["title"],
                        "version_date": doc["version_date"],
                        "snippet_id": snippet["snippet_id"],
                        "snippet": snippet["text"],
                        "score": score
                    })
        
        scored_hits.sort(key=lambda x: x["score"], reverse=True)
        hits = scored_hits[:top_k]
        
        if not hits:
            return {
                "status": "empty",
                "hits": [],
                "error": None
            }
        
        return {
            "status": "ok",
            "hits": hits,
            "error": None
        }
    
    except Exception as e:
        return {
            "status": "error",
            "hits": [],
            "error": f"搜索失败：{str(e)}"
        }


def read_snippet(
    doc_id: str, 
    snippet_id: str,
    _fault: Optional[dict] = None,
    _data_file: Optional[Path] = None
) -> dict:
    """
    读取指定文档的指定片段
    
    Args:
        doc_id: 文档 ID
        snippet_id: 片段 ID
        _fault: 故障注入配置
        _data_file: 数据文件路径（测试用）
    
    Returns:
        {status, doc_id, text, error}
    """
    fault_resp = _check_fault(_fault, "read_snippet")
    if fault_resp:
        return fault_resp
    
    try:
        documents = _load_faq(_data_file)
        
        for doc in documents:
            if doc["doc_id"] == doc_id:
                for snippet in doc.get("snippets", []):
                    if snippet["snippet_id"] == snippet_id:
                        return {
                            "status": "ok",
                            "doc_id": doc_id,
                            "text": snippet["text"],
                            "error": None
                        }
                
                return {
                    "status": "empty",
                    "doc_id": doc_id,
                    "text": None,
                    "error": f"片段 {snippet_id} 不存在"
                }
        
        return {
            "status": "empty",
            "doc_id": doc_id,
            "text": None,
            "error": f"文档 {doc_id} 不存在"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "doc_id": doc_id,
            "text": None,
            "error": f"读取片段失败：{str(e)}"
        }


def get_doc_meta(
    doc_id: str,
    _fault: Optional[dict] = None,
    _data_file: Optional[Path] = None
) -> dict:
    """
    获取文档元数据
    
    Args:
        doc_id: 文档 ID
        _fault: 故障注入配置
        _data_file: 数据文件路径（测试用）
    
    Returns:
        {status, scope, priority, effective_date, error}
    """
    fault_resp = _check_fault(_fault, "get_doc_meta")
    if fault_resp:
        return fault_resp
    
    try:
        documents = _load_faq(_data_file)
        
        for doc in documents:
            if doc["doc_id"] == doc_id:
                return {
                    "status": "ok",
                    "doc_id": doc_id,
                    "scope": doc.get("scope"),
                    "priority": doc.get("priority"),
                    "effective_date": doc.get("version_date"),
                    "error": None
                }
        
        return {
            "status": "empty",
            "doc_id": doc_id,
            "scope": None,
            "priority": None,
            "effective_date": None,
            "error": f"文档 {doc_id} 不存在"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "doc_id": doc_id,
            "scope": None,
            "priority": None,
            "effective_date": None,
            "error": f"获取元数据失败：{str(e)}"
        }


def ask_user(
    question: str,
    _fault: Optional[dict] = None,
    _data_file: Optional[Path] = None,
    **kwargs  # 接受额外参数（如 conflict_docs, citations）
) -> dict:
    """
    向用户提问（模拟）
    
    Args:
        question: 问题内容
        _fault: 故障注入配置
        _data_file: 数据文件路径（测试用，ask_user 不使用）
        **kwargs: 额外参数（如 conflict_docs, citations）
    
    Returns:
        {status: "ok", question, citations, gaps}
    """
    fault_resp = _check_fault(_fault, "ask_user")
    if fault_resp:
        return fault_resp
    
    result = {
        "status": "ok",
        "question": question,
        "error": None
    }
    
    # 传递额外参数到 observation
    if "citations" in kwargs:
        result["citations"] = kwargs["citations"]
    if "conflict_docs" in kwargs:
        result["gaps"] = ["需要用户确认适用制度：" + ", ".join(kwargs["conflict_docs"])]
    
    return result
