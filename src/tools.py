"""
文档检索和读取工具
"""
import json
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
DOCUMENTS_FILE = DATA_DIR / "documents.json"


def load_documents() -> list[dict]:
    """加载文档库"""
    if not DOCUMENTS_FILE.exists():
        return []
    with open(DOCUMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def search_documents(query: str, top_k: int = 3) -> dict:
    """
    搜索文档，返回匹配的文档摘要
    
    Args:
        query: 搜索关键词
        top_k: 返回最多 top_k 个结果
    
    Returns:
        包含匹配文档列表的字典
    """
    documents = load_documents()
    
    query_lower = query.lower()
    keywords = query_lower.split()
    
    scored_docs = []
    for doc in documents:
        score = 0
        content_lower = (doc["title"] + " " + doc["content"] + " " + doc.get("category", "")).lower()
        
        for keyword in keywords:
            if keyword in content_lower:
                score += content_lower.count(keyword)
        
        if score > 0:
            snippet = doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"]
            scored_docs.append({
                "id": doc["id"],
                "title": doc["title"],
                "version": doc["version"],
                "category": doc.get("category", ""),
                "snippet": snippet,
                "score": score
            })
    
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    results = scored_docs[:top_k]
    
    return {
        "query": query,
        "total_matches": len(scored_docs),
        "results": results
    }


def read_document(doc_id: str) -> Optional[dict]:
    """
    读取指定文档的完整内容
    
    Args:
        doc_id: 文档 ID
    
    Returns:
        完整文档内容，如果不存在返回 None
    """
    documents = load_documents()
    
    for doc in documents:
        if doc["id"] == doc_id:
            return {
                "id": doc["id"],
                "title": doc["title"],
                "version": doc["version"],
                "category": doc.get("category", ""),
                "content": doc["content"]
            }
    
    return {"error": f"文档 {doc_id} 不存在"}


def simulate_tool_failure(tool_name: str) -> dict:
    """模拟工具调用失败，用于测试"""
    return {
        "error": f"工具 {tool_name} 调用失败：服务暂时不可用",
        "status": "failed"
    }
