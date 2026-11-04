"""
上下文追问测试
模拟多轮对话，验证指代消解功能
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.loop import run_agent


INPUTS_DIR = Path(__file__).parent.parent / "examples" / "inputs"
TRACES_DIR = Path(__file__).parent.parent / "examples" / "traces"


def test_context_followup():
    """测试上下文追问场景"""
    
    # 加载输入
    input_file = INPUTS_DIR / "context_followup.json"
    with open(input_file, "r", encoding="utf-8") as f:
        case_input = json.load(f)
    
    print(f"=== 测试用例：{case_input['case']} ===")
    print(f"描述：{case_input['description']}\n")
    
    turns = case_input["turns"]
    conversation_history = []
    
    # 模拟多轮对话
    for i, turn in enumerate(turns):
        if turn["role"] == "user":
            query = turn["content"]
            print(f"轮次 {i+1}：用户问「{query}」")
            
            # 运行 Agent
            result = run_agent(
                query=query,
                conversation_history=conversation_history.copy(),
                case_name=f"context_followup_turn{i+1}"
            )
            
            print(f"  状态：{result['status']}")
            print(f"  步数：{len(result.get('steps', []))}")
            
            # 提取回答
            answer = result.get("answer", "")
            print(f"  回答：{answer[:100]}...")
            
            # 记录到对话历史
            conversation_history.append({
                "role": "user",
                "content": query
            })
            conversation_history.append({
                "role": "assistant",
                "content": answer
            })
            
            # 检查第二轮是否正确处理了指代
            if i == 2:  # 第三轮（索引2）：用户问"那申请流程呢"
                # 检查 trace 中的第一个 search_docs 调用
                if result.get("steps"):
                    first_step = result["steps"][0]
                    if first_step["action"] == "search_docs":
                        search_query = first_step["args"].get("query", "")
                        print(f"  指代消解结果：「{search_query}」")
                        
                        # 验证：search_query 应该包含"年假"
                        if "年假" in search_query:
                            print(f"  ✅ 指代消解成功：'那' 被还原为 '年假'")
                        else:
                            print(f"  ❌ 指代消解失败：未找到'年假'")
            
            print()
    
    print("=== 测试完成 ===")
    print(f"Trace 文件已保存到：{TRACES_DIR}")


if __name__ == "__main__":
    test_context_followup()
