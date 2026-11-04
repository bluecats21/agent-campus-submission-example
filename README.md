# 企业知识问答 Agent

校招考核项目：帮助员工从内部文档中查找可靠答案的 AI Agent。

## 核心特性

- **ReAct 决策循环**：模型选择动作 → 执行工具 → 观察结果 → 调整下一步
- **三态工具返回**：ok / empty / error，语义清晰
- **冲突处理**：多文档冲突时列冲突并请求确认，不擅自选择
- **无硬编码**：所有业务内容来自 data/*.json，提示词不含具体数值/doc_id
- **可替换数据**：支持 v1/v2 数据切换，验证 Agent 行为随数据变化

## 环境要求

- Python 3.10+
- 无需 API Key（使用 Mock 模型验证流程）

## 安装

```bash
pip install -r requirements.txt
```

依赖：
- langgraph>=0.2.0
- langchain-core>=0.3.0
- langchain-openai>=0.2.0
- python-dotenv>=1.0.0
- pytest>=7.4.0

## 运行

### 1. 运行单个用例

```bash
python -X utf8 -c "
import sys
sys.path.insert(0, 'src')
from agent.loop import run_agent
result = run_agent('你的问题', case_name='my_test')
import json
print(json.dumps(result, ensure_ascii=False, indent=2))
"
```

### 2. 运行 4 组测试用例

```bash
python -X utf8 tests/run_cases.py
```

输出：
- examples/traces/normal_unique.json
- examples/traces/conflict.json
- examples/traces/out_of_scope.json
- examples/traces/tool_error.json

### 3. 运行完整测试

```bash
python -X utf8 -m pytest tests/ -v
```

当前测试数：22 个（全部通过）

### 4. 替换回归测试

```bash
python -X utf8 -m pytest tests/test_swap.py -v
```

验证：同一问题在 faq_v1.json 和 faq_v2.json 下走不同路径。

## 项目结构

```
.
├── README.md
├── AGENTS.md                    # 项目硬约束
├── requirements.txt
├── .env.example
├── data/
│   ├── faq_v1.json              # 原始数据（D01/D02/D03/D04）
│   └── faq_v2.json              # 修改数据（删 D02，改天数）
├── src/
│   ├── tools/
│   │   ├── __init__.py
│   │   └── document_tools.py    # 4 个工具（search_docs, read_snippet, get_doc_meta, ask_user）
│   ├── model/
│   │   ├── __init__.py
│   │   ├── base.py              # 模型接口
│   │   ├── mock.py              # Mock 实现（仅验证流程）
│   │   └── real.py              # 真实 API（可选，需 API Key）
│   ├── agent/
│   │   ├── __init__.py
│   │   └── loop.py              # ReAct 主循环
│   ├── data/
│   │   ├── __init__.py
│   │   └── faq_v1.py            # 数据加载
│   └── prompts/
│       └── system.txt           # 系统提示词
├── tests/
│   ├── test_tools.py            # 工具三态测试（15 个）
│   ├── test_swap.py             # 替换回归测试（3 个）
│   ├── test_additional.py       # 额外测试（4 个）
│   └── run_cases.py             # 4 组用例运行器
├── examples/
│   ├── inputs/                  # 输入文件
│   └── traces/                  # 运行 trace
└── docs/
    ├── 01-requirements.md       # 需求文档
    ├── 02-solution.md           # 技术方案
    ├── 03-evaluation.md         # 测试评估
    ├── 04-ai-usage.md           # AI 使用记录
    └── 05-retrospective.md      # 复盘总结
```

## 评审入口

1. **运行测试**：`python -X utf8 -m pytest tests/ -v`
2. **查看 trace**：examples/traces/*.json
3. **替换数据**：修改 data/faq_v1.json，重跑测试，观察行为变化
4. **检查硬编码**：grep src/prompts/system.txt，应无具体数值/doc_id

## 已知限制

- Mock 模型基于规则，不代表真实 LLM 决策效果
- 检索算法为简单关键词匹配，未使用向量库/embedding
- 未实现真实 LLM 调用（real.py 仅接口占位）
- 单 Agent 架构，未实现多 Agent 协作

## 许可证

校招考核项目，仅供评审使用。
