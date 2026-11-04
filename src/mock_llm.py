"""
离线 Mock LLM，用于无 API Key 时验证流程
"""
import json
import re
from typing import Any


class MockLLM:
    """模拟 LLM 响应，基于规则生成决策"""
    
    def __init__(self):
        self.call_count = 0
        self.max_calls = 10
        
    def invoke(self, messages: list[dict], tools: list = None) -> dict:
        """
        模拟 LLM 调用
        
        Args:
            messages: 消息列表
            tools: 可用工具列表
        
        Returns:
            LLM 响应（包含 tool_calls 或 content）
        """
        self.call_count += 1
        
        if self.call_count > self.max_calls:
            return {
                "content": "达到最大调用次数限制，停止处理。",
                "tool_calls": []
            }
        
        last_message = messages[-1]["content"] if messages else ""
        
        # 分析上下文，决定下一步动作
        return self._generate_response(last_message, messages, tools)
    
    def _generate_response(self, query: str, messages: list[dict], tools: list) -> dict:
        """根据上下文生成响应"""
        
        # 检查是否有工具结果
        tool_results = [m for m in messages if m.get("role") == "tool"]
        
        if not tool_results:
            # 第一轮：需要检索文档
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "search_documents",
                            "arguments": json.dumps({"query": query}, ensure_ascii=False)
                        }
                    }
                ]
            }
        
        # 解析最近一次工具结果
        last_result = tool_results[-1]["content"]
        try:
            result_data = json.loads(last_result)
        except:
            result_data = {"error": "解析失败"}
        
        # 根据工具结果决定下一步
        if "error" in result_data:
            # 工具失败，返回错误状态
            return {
                "content": f"抱歉，处理您的问题时遇到了技术故障：{result_data['error']}。请稍后重试或联系管理员。",
                "tool_calls": []
            }
        
        if result_data.get("results"):
            results = result_data["results"]
            
            # 检查是否需要读取完整文档
            if len(results) >= 2:
                # 多个结果，可能需要读取完整文档来确认
                doc_ids = [r["id"] for r in results[:2]]
                return {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_read_{doc_id}",
                            "type": "function",
                            "function": {
                                "name": "read_document",
                                "arguments": json.dumps({"doc_id": doc_id}, ensure_ascii=False)
                            }
                        }
                        for doc_id in doc_ids
                    ]
                }
            elif len(results) == 1:
                # 单个结果，读取完整文档
                return {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_read_1",
                            "type": "function",
                            "function": {
                                "name": "read_document",
                                "arguments": json.dumps({"doc_id": results[0]["id"]}, ensure_ascii=False)
                            }
                        }
                    ]
                }
        
        # 检查是否已经读取了文档
        full_docs = [m for m in messages if "content" in m and "title" in m.get("content", "")]
        
        if full_docs:
            # 已有完整文档，生成最终回答
            return self._generate_answer(query, full_docs, messages)
        
        # 没有相关文档
        return {
            "content": "抱歉，我在现有文档库中没有找到与您问题相关的信息。建议您：\n1. 尝试使用不同的关键词重新提问\n2. 联系相关部门获取更准确的信息\n\n资料缺口：未找到相关文档",
            "tool_calls": []
        }
    
    def _generate_answer(self, query: str, docs: list[dict], messages: list[dict]) -> dict:
        """基于文档生成回答"""
        
        # 提取文档内容
        doc_contents = []
        for m in messages:
            if m.get("role") == "tool":
                try:
                    content = json.loads(m["content"])
                    if "content" in content and "title" in content:
                        doc_contents.append(content)
                except:
                    pass
        
        if not doc_contents:
            return {
                "content": "抱歉，无法获取相关文档内容。",
                "tool_calls": []
            }
        
        # 检查是否有冲突
        query_lower = query.lower()
        
        # 报销期限冲突检测
        if "报销" in query_lower and ("期限" in query_lower or "多久" in query_lower or "时间" in query_lower):
            deadlines = {}
            for doc in doc_contents:
                content = doc.get("content", "")
                # 提取期限
                if "30 天" in content or "30天" in content:
                    deadlines[doc["id"]] = "30 天"
                if "15 天" in content or "15个工作日" in content:
                    deadlines[doc["id"]] = "15 天/15 个工作日"
            
            if len(deadlines) > 1:
                # 发现冲突
                conflict_msg = "发现文档冲突：\n\n"
                for doc_id, deadline in deadlines.items():
                    conflict_msg += f"- 文档 {doc_id}：{deadline}\n"
                conflict_msg += "\n请确认您需要查询的是哪项制度的报销期限？\n1. 一般费用报销（D01 员工报销管理制度）\n2. 差旅费用报销（D02 差旅费用管理办法）"
                
                return {
                    "content": conflict_msg,
                    "tool_calls": []
                }
        
        # 无冲突，正常回答
        answer = "根据文档内容：\n\n"
        citations = []
        
        for doc in doc_contents:
            answer += f"**{doc['title']}**（{doc['id']}，版本 {doc['version']}）：\n"
            
            # 提取关键信息
            content = doc.get("content", "")
            lines = content.split("\n")
            key_info = [line for line in lines if any(kw in query_lower for kw in ["报销", "期限", "年假", "加班", "退款", "退货"])][:3]
            
            if key_info:
                answer += "\n".join(key_info) + "\n\n"
            else:
                answer += content[:300] + "...\n\n"
            
            citations.append(f"[{doc['id']}] {doc['title']}")
        
        answer += "\n引用文档：\n" + "\n".join(citations)
        
        return {
            "content": answer,
            "tool_calls": []
        }


def get_mock_llm() -> MockLLM:
    """获取 Mock LLM 实例"""
    return MockLLM()
