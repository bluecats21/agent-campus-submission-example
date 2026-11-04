"""
测试用例运行器
运行 4 组测试用例并保存 trace
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.loop import run_agent, execute_action, _model
from tools import search_docs, read_snippet, get_doc_meta, ask_user


INPUTS_DIR = Path(__file__).parent.parent / "examples" / "inputs"
TRACES_DIR = Path(__file__).parent.parent / "examples" / "traces"


def execute_action_with_fault(action: str, args: dict, fault: dict = None) -> dict:
    """执行动作，支持故障注入"""
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
    
    # 如果有故障配置，传入 _fault 参数
    if fault and fault.get("tool") == action:
        return tool_map[action](**args, _fault=fault)
    
    try:
        return tool_map[action](**args)
    except Exception as e:
        return {
            "status": "error",
            "error": f"工具调用异常：{str(e)}"
        }


def run_case(case_file: Path):
    """运行单个测试用例"""
    with open(case_file, "r", encoding="utf-8") as f:
        case_input = json.load(f)
    
    case_name = case_input["case"]
    query = case_input["query"]
    fault = case_input.get("fault")
    
    print(f"\n{'='*60}")
    print(f"运行用例：{case_name}")
    print(f"查询：{query}")
    if fault:
        print(f"故障注入：{fault}")
    print(f"{'='*60}")
    
    # 临时替换 execute_action 以支持故障注入
    import agent.loop as loop_module
    original_execute = loop_module.execute_action
    
    if fault:
        def patched_execute(action, args):
            return execute_action_with_fault(action, args, fault)
        loop_module.execute_action = patched_execute
    
    try:
        result = run_agent(query, case_name=case_name)
    finally:
        loop_module.execute_action = original_execute
    
    # 保存 trace（run_agent 已自动保存）
    trace_file = TRACES_DIR / f"{case_name}.json"
    print(f"\nTrace 已保存：{trace_file}")
    print(f"状态：{result['status']}")
    print(f"步数：{len(result.get('steps', []))}")
    
    return result


def compare_action_sequences(case1_name: str, case2_name: str):
    """比较两个用例的动作序列"""
    trace1_file = TRACES_DIR / f"{case1_name}.json"
    trace2_file = TRACES_DIR / f"{case2_name}.json"
    
    with open(trace1_file, "r", encoding="utf-8") as f:
        trace1 = json.load(f)
    with open(trace2_file, "r", encoding="utf-8") as f:
        trace2 = json.load(f)
    
    actions1 = [step["action"] for step in trace1["steps"]]
    actions2 = [step["action"] for step in trace2["steps"]]
    
    print(f"\n{'='*60}")
    print("动作序列对比")
    print(f"{'='*60}")
    print(f"{case1_name:20s} | {case2_name:20s}")
    print(f"{'-'*20}-+-{'-'*20}")
    
    max_len = max(len(actions1), len(actions2))
    for i in range(max_len):
        a1 = actions1[i] if i < len(actions1) else "-"
        a2 = actions2[i] if i < len(actions2) else "-"
        marker = "✓" if a1 == a2 else "✗"
        print(f"{a1:20s} | {a2:20s} {marker}")
    
    print(f"\n序列是否不同：{actions1 != actions2}")


if __name__ == "__main__":
    # 运行所有用例
    cases = ["normal_unique", "conflict", "out_of_scope", "tool_error"]
    
    for case_name in cases:
        case_file = INPUTS_DIR / f"{case_name}.json"
        if case_file.exists():
            run_case(case_file)
        else:
            print(f"用例文件不存在：{case_file}")
    
    # 比较 case 1 和 case 2 的动作序列
    compare_action_sequences("normal_unique", "conflict")
