"""
工具模块测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.tools import search_docs, read_snippet, get_doc_meta, ask_user


class TestSearchDocs:
    """search_docs 工具测试"""
    
    def test_ok_with_matches(self):
        """测试有匹配结果的搜索"""
        result = search_docs("报销期限")
        assert result["status"] == "ok"
        assert len(result["hits"]) > 0
        assert result["error"] is None
        
        hit = result["hits"][0]
        assert "doc_id" in hit
        assert "title" in hit
        assert "snippet_id" in hit
        assert "snippet" in hit
        assert "score" in hit
        assert hit["score"] > 0
    
    def test_empty_no_matches(self):
        """测试无匹配结果的搜索"""
        result = search_docs("不存在的关键词xyz123")
        assert result["status"] == "empty"
        assert len(result["hits"]) == 0
        assert result["error"] is None
    
    def test_error_with_fault(self):
        """测试故障注入"""
        fault = {"tool": "search_docs", "mode": "error", "times": 1}
        result = search_docs("报销", _fault=fault)
        assert result["status"] == "error"
        assert result["error"] is not None
        assert "模拟故障" in result["error"]
    
    def test_top_k_limit(self):
        """测试返回数量限制"""
        result = search_docs("报销", top_k=2)
        assert result["status"] == "ok"
        assert len(result["hits"]) <= 2


class TestReadSnippet:
    """read_snippet 工具测试"""
    
    def test_ok_existing_snippet(self):
        """测试读取存在的片段"""
        result = read_snippet("D01", "D01_S1")
        assert result["status"] == "ok"
        assert result["doc_id"] == "D01"
        assert result["text"] is not None
        assert result["error"] is None
    
    def test_empty_nonexistent_doc(self):
        """测试读取不存在的文档"""
        result = read_snippet("D999", "D999_S1")
        assert result["status"] == "empty"
        assert result["text"] is None
        assert "不存在" in result["error"]
    
    def test_empty_nonexistent_snippet(self):
        """测试读取不存在的片段"""
        result = read_snippet("D01", "D01_S999")
        assert result["status"] == "empty"
        assert result["text"] is None
        assert "不存在" in result["error"]
    
    def test_error_with_fault(self):
        """测试故障注入"""
        fault = {"tool": "read_snippet", "mode": "error", "times": 1}
        result = read_snippet("D01", "D01_S1", _fault=fault)
        assert result["status"] == "error"
        assert result["error"] is not None


class TestGetDocMeta:
    """get_doc_meta 工具测试"""
    
    def test_ok_existing_doc(self):
        """测试获取存在的文档元数据"""
        result = get_doc_meta("D01")
        assert result["status"] == "ok"
        assert result["doc_id"] == "D01"
        assert "scope" in result
        assert "priority" in result
        assert "effective_date" in result
        assert result["error"] is None
    
    def test_ok_with_null_fields(self):
        """测试元数据字段可为 null"""
        result = get_doc_meta("D01")
        assert result["status"] == "ok"
        assert result["scope"] is None
        assert result["priority"] is None
    
    def test_ok_with_scope(self):
        """测试有 scope 的文档"""
        result = get_doc_meta("D03")
        assert result["status"] == "ok"
        assert result["scope"] == "差旅场景"
    
    def test_empty_nonexistent_doc(self):
        """测试获取不存在的文档元数据"""
        result = get_doc_meta("D999")
        assert result["status"] == "empty"
        assert "不存在" in result["error"]
    
    def test_error_with_fault(self):
        """测试故障注入"""
        fault = {"tool": "get_doc_meta", "mode": "error", "times": 1}
        result = get_doc_meta("D01", _fault=fault)
        assert result["status"] == "error"
        assert result["error"] is not None


class TestAskUser:
    """ask_user 工具测试"""
    
    def test_ok(self):
        """测试正常提问"""
        result = ask_user("请确认您需要查询哪项制度？")
        assert result["status"] == "ok"
        assert result["question"] == "请确认您需要查询哪项制度？"
        assert result["error"] is None
    
    def test_error_with_fault(self):
        """测试故障注入"""
        fault = {"tool": "ask_user", "mode": "error", "times": 1}
        result = ask_user("问题", _fault=fault)
        assert result["status"] == "error"
        assert result["error"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
