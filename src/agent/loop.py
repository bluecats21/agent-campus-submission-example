"""
Agent 主循环
"""
import json
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import search_docs, read_snippet, get_doc_meta, ask_user
from model import MockModel


TRACES_DIR = Path(__file__).parent.parent.parent / "examples" / "traces"
TRACES_DIR.mkdir(parents=True, exist_ok=True)


# 全局模型实例（可在 run_agent 中替换）
_model = MockModel()


def set_model(model):
    """设置模型实例"""
    global _model
    _model = model


def model_decide(state: dict) -> dict:
    """
    模型决策接口
    
    这是循环中唯一决定"下一步动作"的地方。
    调用 _model.decide(state) 获取下一步动作。
    
    Args:
        state: 当前状态 {query, conversation_history, steps, current_step, last_observation}
    
    Returns:
        {
            "action": "工具名称",
            "args": {"参数": "值"},
            "reason": "决策理由",
            "terminate": False  # 是否终止循环
        }
    """
    return _model.decide(state)


def execute_action(action: str, args: dict) -> dict:
    """
    执行动作，使用 dict 映射分发到工具
    
    Args:
        action: 工具名称
        args: 工具参数
    
    Returns:
        工具返回结果
    """
    # action 分发用 dict 映射工具名
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
    
    try:
        return tool_map[action](**args)
    except Exception as e:
        return {
            "status": "error",
            "error": f"工具调用异常：{str(e)}"
        }


def summarize_observation(observation: dict) -> str:
    """
    生成观察摘要，用于记录到 trace
    
    Args:
        observation: 工具返回结果
    
    Returns:
        摘要字符串
    """
    status = observation.get("status", "unknown")
    
    if status == "ok":
        if "hits" in observation:
            count = len(observation["hits"])
            return f"检索到 {count} 条结果"
        elif "text" in observation:
            length = len(observation["text"])
            return f"读取片段成功，长度 {length}"
        elif "scope" in observation:
            return f"获取元数据成功"
        else:
            return "执行成功"
    elif status == "empty":
        return "无结果"
    elif status == "error":
        return f"错误：{observation.get('error', '未知')}"
    else:
        return f"状态：{status}"


def is_terminated(observation: dict, decision: dict) -> bool:
    """
    判断是否终止循环
    
    注意：这里只检查通用终止条件，不包含业务判断。
    业务终止由 model_decide 通过 terminate 字段控制。
    
    Args:
        observation: 工具返回结果
        decision: 模型决策
    
    Returns:
        是否终止
    """
    # 模型明确决定终止
    if decision.get("terminate", False):
        return True
    
    # 工具调用失败且无法降级（这里简化为直接终止）
    if observation.get("status") == "error":
        return True
    
    return False


def save_trace(state: dict, result: dict, case_name: str):
    """
    保存执行 trace 到文件
    
    Args:
        state: 最终状态
        result: 返回结果
        case_name: 用例名称
    """
    trace = {
        "case": case_name,
        "query": state["query"],
        "conversation_history": state["conversation_history"],
        "steps": state["steps"],
        "result": result
    }
    
    trace_file = TRACES_DIR / f"{case_name}.json"
    with open(trace_file, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)
    
    print(f"Trace 已保存：{trace_file}")


def run_agent(
    query: str,
    conversation_history: Optional[list] = None,
    max_steps: int = 8,
    case_name: str = "test"
) -> dict:
    """
    Agent 主循环
    
    流程：读输入 → 调 model_decide(state) → 执行 action → 记录 → 判断终止
    
    Args:
        query: 用户问题
        conversation_history: 对话历史
        max_steps: 最大步数，默认 8
        case_name: 用例名称，用于保存 trace
    
    Returns:
        {
            "status": "completed" | "incomplete",
            "answer": "回答内容",
            "citations": [],
            "steps": [],
            "done": [],
            "undone": []
        }
    """
    state = {
        "query": query,
        "conversation_history": conversation_history or [],
        "steps": [],
        "current_step": 0,
        "last_observation": None  # 上一步工具返回
    }
    
    # 主循环
    while state["current_step"] < max_steps:
        # 1. 调 model_decide(state)
        #    下一步动作来自这一行的返回值
        decision = model_decide(state)
        
        action = decision["action"]
        args = decision["args"]
        reason = decision["reason"]
        
        # 2. 执行 action（answer 是虚拟动作，不执行工具）
        if action == "answer":
            observation = {
                "status": "ok",
                "content": args.get("content", ""),
                "citations": args.get("citations", []),
                "gaps": args.get("gaps", [])
            }
        else:
            observation = execute_action(action, args)
        
        # 3. 记录
        step_record = {
            "step": state["current_step"],
            "action": action,
            "args": args,
            "observation": observation,
            "observation_summary": summarize_observation(observation),
            "reason": reason
        }
        state["steps"].append(step_record)
        
        # 4. 更新 last_observation
        state["last_observation"] = observation
        
        # 5. 判断终止
        if is_terminated(observation, decision):
            result = {
                "status": "completed",
                "answer": observation.get("content", "循环终止"),
                "citations": observation.get("citations", []),
                "gaps": observation.get("gaps", []),
                "steps": state["steps"]
            }
            save_trace(state, result, case_name)
            return result
        
        state["current_step"] += 1
    
    # 触顶返回 incomplete
    result = {
        "status": "incomplete",
        "done": state["steps"],
        "undone": ["达到最大步数限制，未完成任务"]
    }
    save_trace(state, result, case_name)
    return result


if __name__ == "__main__":
    # 简单测试
    result = run_agent("测试问题", case_name="loop_test")
    print(json.dumps(result, ensure_ascii=False, indent=2))
