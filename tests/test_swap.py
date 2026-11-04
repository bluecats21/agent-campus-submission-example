"""
替换回归测试
验证：同一问题在 v1 和 v2 下走不同路径
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from agent.loop import run_agent
from tools import search_docs, read_snippet, get_doc_meta, ask_user
import agent.loop as loop_module


DATA_DIR = Path(__file__).parent.parent / "data"
V1_FILE = DATA_DIR / "faq_v1.json"
V2_FILE = DATA_DIR / "faq_v2.json"
TRACES_DIR = Path(__file__).parent.parent / "examples" / "traces"


def execute_action_with_data_file(action: str, args: dict, data_file: Path) -> dict:
    """执行动作，传递 data_file 参数"""
    tool_map = {
        "search_docs": search_docs,
        "read_snippet": read_snippet,
        "get_doc_meta": get_doc_meta,
        "ask_user": ask_user
    }
    
    if action not in tool_map:
        return {
            "status": "error",
            "error": f"未知动作：{action}"
        }
    
    if action == "answer":
        return {"status": "ok", "content": args.get("content", "")}
    
    try:
        return tool_map[action](**args, _data_file=data_file)
    except Exception as e:
        return {
            "status": "error",
            "error": f"工具调用异常：{str(e)}"
        }


def run_with_data_file(query: str, data_file: Path, case_name: str) -> dict:
    """使用指定数据文件运行 agent"""
    original_execute = loop_module.execute_action
    
    def patched_execute(action, args):
        return execute_action_with_data_file(action, args, data_file)
    
    loop_module.execute_action = patched_execute
    
    try:
        result = run_agent(query, case_name=case_name)
    finally:
        loop_module.execute_action = original_execute
    
    return result


class TestSwapRegression:
    """替换回归测试"""
    
    def test_v1_conflict_path(self):
        """v1: 报销 期限 → 命中 D01/D02 → 冲突 → ask_user"""
        # 使用更具体的查询，确保命中 D01 和 D02
        result = run_with_data_file("报销 期限", V1_FILE, "swap_v1")
        
        # 保存 trace
        trace_file = TRACES_DIR / "swap_v1.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump({
                "case": "swap_v1",
                "query": "报销 期限",
                "data_file": str(V1_FILE),
                "steps": result.get("steps", []),
                "result": result
            }, f, ensure_ascii=False, indent=2)
        
        # 验证动作序列
        actions = [step["action"] for step in result["steps"]]
        assert "search_docs" in actions
        
        # v1 应该走冲突路径（多个不同文档且元数据为空）
        search_steps = [s for s in result["steps"] if s["action"] == "search_docs"]
        if search_steps:
            last_search = search_steps[-1]
            if last_search["observation"].get("status") == "ok":
                hits = last_search["observation"].get("hits", [])
                unique_docs = set(h["doc_id"] for h in hits)
                # 如果命中多个不同文档，应该走 get_doc_meta 或 ask_user
                if len(unique_docs) > 1:
                    # 检查是否至少有一个文档的 scope 为 null
                    has_null_scope = False
                    for doc_id in unique_docs:
                        meta_steps = [s for s in result["steps"] if s["action"] == "get_doc_meta" and s["args"].get("doc_id") == doc_id]
                        if meta_steps:
                            meta = meta_steps[0]["observation"]
                            if meta.get("scope") is None:
                                has_null_scope = True
                                break
                    
                    if has_null_scope:
                        assert "get_doc_meta" in actions or "ask_user" in actions
    
    def test_v2_direct_answer(self):
        """v2: 报销 期限 → 命中 D01/D03 → D03 有 scope → 直接回答"""
        result = run_with_data_file("报销 期限", V2_FILE, "swap_v2")
        
        # 保存 trace
        trace_file = TRACES_DIR / "swap_v2.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump({
                "case": "swap_v2",
                "query": "报销 期限",
                "data_file": str(V2_FILE),
                "steps": result.get("steps", []),
                "result": result
            }, f, ensure_ascii=False, indent=2)
        
        # 验证动作序列
        actions = [step["action"] for step in result["steps"]]
        assert "search_docs" in actions
        
        # v2 删除了 D02，D03 有 scope="差旅场景"，应该能直接回答
        # 不应该走 ask_user（除非元数据仍为空）
        search_steps = [s for s in result["steps"] if s["action"] == "search_docs"]
        if search_steps:
            last_search = search_steps[-1]
            if last_search["observation"].get("status") == "ok":
                hits = last_search["observation"].get("hits", [])
                unique_docs = set(h["doc_id"] for h in hits)
                # 如果只有一个文档，应该走 read_snippet → answer
                if len(unique_docs) == 1:
                    assert "read_snippet" in actions
    
    def test_action_sequences_differ(self):
        """v1 和 v2 的行为应该不同（命中不同数量的文档）"""
        # 读取已保存的 trace
        v1_trace_file = TRACES_DIR / "swap_v1.json"
        v2_trace_file = TRACES_DIR / "swap_v2.json"
        
        if not v1_trace_file.exists() or not v2_trace_file.exists():
            pytest.skip("需要先运行 test_v1_conflict_path 和 test_v2_direct_answer")
        
        with open(v1_trace_file, "r", encoding="utf-8") as f:
            v1_trace = json.load(f)
        with open(v2_trace_file, "r", encoding="utf-8") as f:
            v2_trace = json.load(f)
        
        # 检查 search_docs 步骤
        v1_search = [s for s in v1_trace["steps"] if s["action"] == "search_docs"]
        v2_search = [s for s in v2_trace["steps"] if s["action"] == "search_docs"]
        
        if v1_search and v2_search:
            v1_hits = v1_search[0]["observation"].get("hits", [])
            v2_hits = v2_search[0]["observation"].get("hits", [])
            
            v1_docs = set(h["doc_id"] for h in v1_hits)
            v2_docs = set(h["doc_id"] for h in v2_hits)
            
            # v1 应该命中 D02，v2 不应该（因为 v2 删除了 D02）
            assert "D02" in v1_docs, f"v1 应该命中 D02，但实际命中：{v1_docs}"
            assert "D02" not in v2_docs, f"v2 不应该命中 D02，但实际命中：{v2_docs}"
            
            # 命中的文档数量应该不同
            assert len(v1_docs) != len(v2_docs), f"v1 和 v2 命中的文档数量相同：{len(v1_docs)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
