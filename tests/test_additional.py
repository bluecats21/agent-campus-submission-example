"""
额外测试：步数上限、引用验证、硬编码检查
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from agent.loop import run_agent
from data import faq_v1


class TestStepLimit:
    """步数上限测试"""
    
    def test_incomplete_on_max_steps(self):
        """达到最大步数时返回 incomplete"""
        # 使用一个会触发多次检索的查询
        result = run_agent(
            "测试问题",
            max_steps=2,  # 设置很小的上限
            case_name="step_limit_test"
        )
        
        # 如果达到上限，应该返回 incomplete
        if len(result.get("steps", [])) >= 2:
            assert result["status"] == "incomplete"
            assert "done" in result
            assert "undone" in result


class TestCitationValidation:
    """引用验证测试"""
    
    def test_citations_are_substrings(self):
        """回答中的每条引用必须是 read_snippet 返回文本的子串"""
        result = run_agent("年假", case_name="citation_test")
        
        # 找到所有 read_snippet 步骤
        read_steps = [s for s in result.get("steps", []) if s["action"] == "read_snippet"]
        
        if not read_steps:
            pytest.skip("没有 read_snippet 步骤")
        
        # 收集所有读取的文本
        read_texts = [s["observation"].get("text", "") for s in read_steps if s["observation"].get("status") == "ok"]
        
        # 检查回答中的引用
        answer = result.get("answer", "")
        citations = result.get("citations", [])
        
        # 如果有引用，验证它们是 read_texts 的子串
        for citation in citations:
            if isinstance(citation, dict) and "text" in citation:
                cited_text = citation["text"]
                # 检查是否是某个 read_text 的子串
                is_substring = any(cited_text in read_text for read_text in read_texts)
                assert is_substring, f"引用文本不在 read_snippet 返回中：{cited_text[:50]}..."


class TestNoHardcoding:
    """硬编码检查测试"""
    
    def test_no_data_numbers_in_prompts(self):
        """data 里的数值不出现在 src/prompts/"""
        # 加载 data
        documents = faq_v1.load_documents()
        
        # 提取所有数值
        numbers = set()
        for doc in documents:
            for snippet in doc.get("snippets", []):
                text = snippet["text"]
                # 提取数值（如 30, 15, 500, 100 等）
                found = re.findall(r'\b\d+\b', text)
                numbers.update(found)
        
        # 读取 prompts
        prompts_dir = Path(__file__).parent.parent / "src" / "prompts"
        if not prompts_dir.exists():
            pytest.skip("src/prompts/ 不存在")
        
        # 检查每个 prompt 文件
        for prompt_file in prompts_dir.glob("*.txt"):
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 检查是否包含 data 中的数值
            for num in numbers:
                # 跳过太短的数值（如 1, 2, 3），容易误判
                if len(num) < 2:
                    continue
                
                if num in content:
                    # 检查是否在占位符中（如 <DAY_A>）
                    # 如果是纯数字出现，则失败
                    pattern = rf'(?<!<){num}(?!>)'
                    if re.search(pattern, content):
                        pytest.fail(f"src/prompts/{prompt_file.name} 中包含 data 数值：{num}")
    
    def test_no_doc_ids_in_prompts(self):
        """data 里的 doc_id 不出现在 src/prompts/"""
        # 加载 data
        documents = faq_v1.load_documents()
        doc_ids = [doc["doc_id"] for doc in documents]
        
        # 读取 prompts
        prompts_dir = Path(__file__).parent.parent / "src" / "prompts"
        if not prompts_dir.exists():
            pytest.skip("src/prompts/ 不存在")
        
        # 检查每个 prompt 文件
        for prompt_file in prompts_dir.glob("*.txt"):
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            for doc_id in doc_ids:
                assert doc_id not in content, f"src/prompts/{prompt_file.name} 中包含 doc_id：{doc_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
