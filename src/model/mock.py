"""
Mock 模型实现 - 仅验证流程，不代表真实模型决策效果

根据 state["last_observation"]["status"] 与已执行动作决定下一步，
用来演示不同路径。决策基于结构信息（status、hits 数量等），
不使用业务硬编码（如 if "30" in text）。
"""
from .base import ModelBase


class MockModel(ModelBase):
    """
    Mock 模型：基于规则的状态机
    
    决策逻辑：
    - 首次调用（无 last_observation）→ search_docs
    - search_docs 返回 ok 且 hits 数量 == 1 → read_snippet
    - search_docs 返回 ok 且 hits 数量 >= 2 → get_doc_meta（检查冲突）
    - get_doc_meta 返回 ok 且 scope/priority 均为 null → ask_user（列冲突）
    - get_doc_meta 返回 ok 且 scope 不为 null → 基于 scope 回答
    - read_snippet 返回 ok → 生成回答
    - search_docs 返回 empty → 改写关键词重试（最多 2 次）
    - search_docs 返回 error → 终止
    """
    
    def __init__(self):
        self.rewrite_count = 0  # 改写重试计数
        self.max_rewrites = 2
    
    def resolve_reference(self, query: str, conversation_history: list) -> str:
        """
        指代消解：如果 query 包含指代词，从 conversation_history 中还原完整查询
        
        Args:
            query: 当前用户问题
            conversation_history: 对话历史 [{"role": "user", "content": "..."}, ...]
        
        Returns:
            还原后的完整查询
        """
        # 简单的指代词检测
        reference_words = ["它", "这个", "那个", "那", "这", "其", "该", "上述", "前面提到的"]
        
        has_reference = any(word in query for word in reference_words)
        
        if not has_reference or not conversation_history:
            return query
        
        # 从 history 中找最近的用户问题
        for turn in reversed(conversation_history):
            if turn.get("role") == "user":
                prev_query = turn.get("content", "")
                # 改进策略：提取前一轮的核心主题词
                topic = self._extract_topic(prev_query)
                
                # 清理当前查询：去除语气词
                cleaned_query = self._clean_query(query)
                
                # 将当前查询中的指代词替换为主题
                resolved = cleaned_query
                for word in reference_words:
                    if word in cleaned_query:
                        resolved = cleaned_query.replace(word, topic, 1)
                        break
                
                # 如果替换后没有变化，直接拼接主题（用空格分隔）
                if resolved == cleaned_query:
                    resolved = f"{topic} {cleaned_query}"
                
                return resolved
        
        return query
    
    def _clean_query(self, query: str) -> str:
        """
        清理查询：去除语气词
        
        Args:
            query: 原始查询
        
        Returns:
            清理后的查询
        """
        # 去除常见语气词
        particles = ["呢", "吗", "啊", "呀", "吧", "哦", "嘛", "么", "没", "没有"]
        cleaned = query
        for particle in particles:
            cleaned = cleaned.replace(particle, "")
        return cleaned.strip()
    
    def _extract_topic(self, query: str) -> str:
        """
        从查询中提取主题词
        
        简单实现：取查询的前 2-4 个字符
        实际应用中需要更复杂的 NLP 处理（如关键词提取、实体识别）
        
        Args:
            query: 用户查询
        
        Returns:
            主题词
        """
        # 简单的关键词映射
        keyword_map = {
            "年假": "年假",
            "报销": "报销",
            "差旅": "差旅",
            "加班": "加班",
            "退款": "退款",
            "退货": "退货",
        }
        
        # 检查查询中是否包含已知关键词
        for keyword, topic in keyword_map.items():
            if keyword in query:
                return topic
        
        # 默认取前 2-4 个字符
        if len(query) >= 4:
            return query[:4]
        elif len(query) >= 2:
            return query[:2]
        else:
            return query
    
    def decide(self, state: dict) -> dict:
        """
        根据状态决定下一步
        
        Args:
            state: 当前状态
        
        Returns:
            {"action", "args", "reason", "terminate"}
        """
        steps = state.get("steps", [])
        last_observation = state.get("last_observation")
        query = state.get("query", "")
        conversation_history = state.get("conversation_history", [])
        
        # 首次调用：无 last_observation
        if last_observation is None:
            # 指代消解：如果有对话历史，尝试还原完整查询
            resolved_query = self.resolve_reference(query, conversation_history)
            
            return {
                "action": "search_docs",
                "args": {"query": resolved_query, "top_k": 10},
                "reason": f"首次调用，执行初始检索（原始查询：{query}，还原后：{resolved_query}）",
                "terminate": False
            }
        
        # 获取上一步的动作
        last_action = steps[-1]["action"] if steps else None
        last_status = last_observation.get("status")
        
        # 根据上一步动作和状态决策
        if last_action == "search_docs":
            return self._decide_after_search(last_status, last_observation, query)
        
        elif last_action == "read_snippet":
            return self._decide_after_read(last_status, last_observation, steps)
        
        elif last_action == "get_doc_meta":
            return self._decide_after_meta(last_status, last_observation, steps)
        
        elif last_action == "ask_user":
            # ask_user 后终止，传递冲突信息
            last_args = steps[-1]["args"] if steps else {}
            return {
                "action": "answer",
                "args": {
                    "content": last_args.get("question", "已向用户提问，等待确认"),
                    "citations": last_args.get("citations", []),
                    "gaps": ["需要用户确认适用制度"]
                },
                "reason": "ask_user 已完成，终止循环",
                "terminate": True
            }
        
        # 默认终止
        return {
            "action": "answer",
            "args": {"content": "流程结束"},
            "reason": "未匹配的動作，终止",
            "terminate": True
        }
    
    def _decide_after_search(self, status: str, observation: dict, query: str) -> dict:
        """search_docs 后的决策"""
        
        if status == "error":
            return {
                "action": "answer",
                "args": {"content": "工具调用失败", "error": observation.get("error")},
                "reason": "search_docs 返回 error，终止",
                "terminate": True
            }
        
        if status == "empty":
            # 空结果：改写重试
            if self.rewrite_count < self.max_rewrites:
                self.rewrite_count += 1
                # 简单改写：取前两个字符
                rewritten_query = query[:2] if len(query) > 2 else query
                return {
                    "action": "search_docs",
                    "args": {"query": rewritten_query, "top_k": 10},
                    "reason": f"search_docs 返回 empty，第 {self.rewrite_count} 次改写重试",
                    "terminate": False
                }
            else:
                # 改写次数用尽
                return {
                    "action": "answer",
                    "args": {
                        "content": "未找到相关文档",
                        "status": "empty",
                        "gaps": [f"未找到与'{query}'相关的文档"]
                    },
                    "reason": f"改写 {self.max_rewrites} 次后仍为 empty，无法回答",
                    "terminate": True
                }
        
        if status == "ok":
            hits = observation.get("hits", [])
            hit_count = len(hits)
            
            if hit_count == 0:
                # 理论上不会发生（ok 应该有 hits）
                return {
                    "action": "answer",
                    "args": {"content": "检索结果为空"},
                    "reason": "status=ok 但 hits 为空",
                    "terminate": True
                }
            
            # 检查 hits 是否来自不同文档
            unique_doc_ids = set(hit["doc_id"] for hit in hits)
            
            if len(unique_doc_ids) == 1:
                # 唯一文档（可能有多个片段）：读取第一个片段
                hit = hits[0]
                return {
                    "action": "read_snippet",
                    "args": {
                        "doc_id": hit["doc_id"],
                        "snippet_id": hit["snippet_id"]
                    },
                    "reason": f"search_docs 返回 {hit_count} 条结果，均来自 {hit['doc_id']}，读取完整片段",
                    "terminate": False
                }
            
            else:
                # 多个不同文档：检查元数据（可能冲突）
                # 选择分数最高的文档进行检查
                top_hit = max(hits, key=lambda h: h.get("score", 0))
                return {
                    "action": "get_doc_meta",
                    "args": {"doc_id": top_hit["doc_id"]},
                    "reason": f"search_docs 返回 {hit_count} 条结果，来自 {len(unique_doc_ids)} 个不同文档，检查元数据判断冲突（选择分数最高的 {top_hit['doc_id']}）",
                    "terminate": False
                }
        
        # 默认
        return {
            "action": "answer",
            "args": {"content": "未知状态"},
            "reason": f"未处理的 status: {status}",
            "terminate": True
        }
    
    def _decide_after_read(self, status: str, observation: dict, steps: list) -> dict:
        """read_snippet 后的决策"""
        
        if status == "error":
            return {
                "action": "answer",
                "args": {"content": "读取片段失败", "error": observation.get("error")},
                "reason": "read_snippet 返回 error，终止",
                "terminate": True
            }
        
        if status == "empty":
            return {
                "action": "answer",
                "args": {"content": "片段不存在"},
                "reason": "read_snippet 返回 empty，终止",
                "terminate": True
            }
        
        if status == "ok":
            # 读取成功，生成回答
            doc_id = observation.get("doc_id")
            text = observation.get("text", "")
            
            # 从 steps 中获取原始查询
            query = steps[0]["args"].get("query", "") if steps else ""
            
            return {
                "action": "answer",
                "args": {
                    "content": f"根据文档 {doc_id}：\n> {text}",
                    "citations": [{"doc_id": doc_id, "text": text}]
                },
                "reason": "read_snippet 返回 ok，生成回答",
                "terminate": True
            }
        
        return {
            "action": "answer",
            "args": {"content": "未知状态"},
            "reason": f"未处理的 status: {status}",
            "terminate": True
        }
    
    def _decide_after_meta(self, status: str, observation: dict, steps: list) -> dict:
        """get_doc_meta 后的决策"""
        
        if status == "error":
            return {
                "action": "answer",
                "args": {"content": "获取元数据失败", "error": observation.get("error")},
                "reason": "get_doc_meta 返回 error，终止",
                "terminate": True
            }
        
        if status == "empty":
            return {
                "action": "answer",
                "args": {"content": "文档不存在"},
                "reason": "get_doc_meta 返回 empty，终止",
                "terminate": True
            }
        
        if status == "ok":
            scope = observation.get("scope")
            priority = observation.get("priority")
            doc_id = observation.get("doc_id")
            
            # 检查元数据是否为空（无法消解冲突）
            if scope is None and priority is None:
                # 从 steps 中获取 search_docs 的结果
                search_steps = [s for s in steps if s["action"] == "search_docs"]
                conflict_docs = []
                citations = []
                
                if search_steps:
                    last_search = search_steps[-1]
                    hits = last_search["observation"].get("hits", [])
                    unique_docs = {}
                    for hit in hits:
                        if hit["doc_id"] not in unique_docs:
                            unique_docs[hit["doc_id"]] = hit
                    
                    # 构建冲突文档列表和引用
                    for doc_id_key, hit in unique_docs.items():
                        conflict_docs.append(f"{doc_id_key}（{hit['title']}，版本 {hit['version_date']}）")
                        citations.append({
                            "doc_id": doc_id_key,
                            "snippet_id": hit["snippet_id"],
                            "text": hit["snippet"]
                        })
                
                conflict_list = "\n".join([f"- {doc}" for doc in conflict_docs])
                question = f"发现文档冲突，以下文档均相关但元数据不足以判断适用范围：\n{conflict_list}\n\n请确认您需要查询哪项制度？"
                
                # 元数据为空，无法判断适用范围，列冲突并请求确认
                return {
                    "action": "ask_user",
                    "args": {
                        "question": question,
                        "conflict_docs": conflict_docs,
                        "citations": citations
                    },
                    "reason": "get_doc_meta 返回 ok 但 scope/priority 均为 null，无法消解冲突，请求用户确认",
                    "terminate": False
                }
            else:
                # 元数据有值，可以基于 scope 回答
                # 从 steps 中获取相关片段
                search_steps = [s for s in steps if s["action"] == "search_docs"]
                citations = []
                if search_steps:
                    last_search = search_steps[-1]
                    hits = last_search["observation"].get("hits", [])
                    # 选择与当前 doc_id 相关的 hits
                    for hit in hits:
                        if hit["doc_id"] == doc_id:
                            citations.append({
                                "doc_id": doc_id,
                                "snippet_id": hit["snippet_id"],
                                "text": hit["snippet"]
                            })
                            break
                
                return {
                    "action": "answer",
                    "args": {
                        "content": f"根据文档 {doc_id}（scope={scope}, priority={priority}）",
                        "citations": citations
                    },
                    "reason": "get_doc_meta 返回 ok 且 scope/priority 非空，基于元数据回答",
                    "terminate": True
                }
        
        return {
            "action": "answer",
            "args": {"content": "未知状态"},
            "reason": f"未处理的 status: {status}",
            "terminate": True
        }


def get_mock_model() -> MockModel:
    """获取 Mock 模型实例"""
    return MockModel()
