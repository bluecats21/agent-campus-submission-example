# 技术方案

## 1. 架构概览

```
用户问题
  ↓
Agent 主循环 (src/agent/loop.py)
  ↓
model_decide(state) → 下一步动作
  ↓
execute_action(action, args) → 工具调用
  ↓
工具层 (src/tools/document_tools.py)
  ├─ search_docs(query, top_k)
  ├─ read_snippet(doc_id, snippet_id)
  ├─ get_doc_meta(doc_id)
  └─ ask_user(question)
  ↓
数据层 (data/faq_v1.json)
  ↓
观察结果 → 更新 state → 循环
```

## 2. 核心模块

### 2.1 Agent 主循环 (src/agent/loop.py)

**职责**：实现 ReAct 决策循环

**关键函数**：
- `run_agent(query, max_steps=8)`：主入口
- `model_decide(state)`：调用模型决策（当前使用 MockModel）
- `execute_action(action, args)`：工具分发（dict 映射）

**设计要点**：
- 循环中无业务 if，下一步动作完全来自 model_decide 返回值
- state 每步记录 {step, action, args, observation, reason}
- 达到 max_steps 返回 {status: "incomplete", done: [...], undone: [...]}
- 结束时写 trace 到 examples/traces/<case>.json

**代码位置**：
- 主循环：src/agent/loop.py:191-242
- 动作分发：src/agent/loop.py:45-68

### 2.2 工具层 (src/tools/document_tools.py)

**职责**：提供 4 个纯函数工具

**工具清单**：

| 工具 | 参数 | 返回 | 说明 |
|------|------|------|------|
| search_docs | query, top_k | {status, hits, error} | 关键词匹配检索 |
| read_snippet | doc_id, snippet_id | {status, doc_id, text, error} | 读取片段全文 |
| get_doc_meta | doc_id | {status, scope, priority, effective_date, error} | 获取元数据 |
| ask_user | question | {status, question, error} | 向用户提问 |

**三态设计**：
- `ok`：找到有效数据
- `empty`：数据不存在（文档/片段未找到）
- `error`：工具调用失败（故障注入或异常）

**故障注入**：所有工具支持 `_fault={"tool": 名称, "mode": "error", "times": N}`

**纯函数**：不依赖全局状态，支持 `_data_file` 参数切换数据源

**代码位置**：src/tools/document_tools.py

### 2.3 模型层 (src/model/)

**职责**：决定下一步动作

**接口**：src/model/base.py
```python
class ModelBase(ABC):
    def decide(self, state: dict) -> dict:
        # 返回 {"action", "args", "reason", "terminate"}
```

**Mock 实现**：src/model/mock.py
- 基于规则的状态机
- 根据 last_observation.status 和 hits 结构决策
- 不使用业务硬编码（如 if "30" in text）

**决策逻辑**：
1. 首次调用 → search_docs
2. search_docs 返回 ok 且唯一 doc_id → read_snippet
3. search_docs 返回 ok 且多个 doc_id → get_doc_meta
4. get_doc_meta 返回 ok 且 scope/priority 均为 null → ask_user
5. get_doc_meta 返回 ok 且 scope 非空 → answer
6. read_snippet 返回 ok → answer
7. search_docs 返回 empty → 改写重试（最多 2 次）
8. search_docs 返回 error → 终止

**真实 API**：src/model/real.py（可选，需 OPENAI_API_KEY）

**代码位置**：src/model/mock.py:35-180

### 2.4 提示词 (src/prompts/system.txt)

**职责**：指导模型决策

**内容**：
- 工具清单（4 个工具及参数说明）
- JSON 决策格式（action / args / reason）
- 检索策略（指代补全、空结果改写）
- 冲突处理四段式（判定→查证→消解→列冲突）
- 无法回答条件
- 引用要求（逐字引用）
- 工具失败降级
- 步数上限（默认 5 次）

**红线**：
- 不含具体天数、doc_id、业务词
- 冲突处理写原则，不写模式匹配

**代码位置**：src/prompts/system.txt

## 3. 数据层

### 3.1 数据结构 (data/faq_v1.json)

```json
[
  {
    "doc_id": "D01",
    "title": "员工报销管理制度",
    "version_date": "2024-01-15",
    "scope": null,
    "priority": null,
    "snippets": [
      {"snippet_id": "D01_S1", "text": "..."}
    ]
  }
]
```

**字段说明**：
- doc_id：文档唯一标识
- title：文档标题
- version_date：版本日期
- scope：适用范围（可为 null）
- priority：优先级（可为 null）
- snippets：片段列表

### 3.2 替换测试 (data/faq_v2.json)

**修改内容**：
- 删除 D02
- D01 天数从 <DAY_A> 改为 <DAY_C>
- D03 保留 scope="差旅场景"

**用途**：验证同一问题在 v1 和 v2 下走不同路径

## 4. 调用流程

### 4.1 正常路径（唯一文档）

```
查询："年假"
  ↓
search_docs → ok (5 hits, 均来自 D04)
  ↓
检测唯一 doc_id → read_snippet(D04, D04_S1)
  ↓
read_snippet → ok
  ↓
answer → 生成回答
  ↓
完成（3 步）
```

**Trace**：examples/traces/normal_unique.json

### 4.2 冲突路径（多文档）

```
查询："报销期限"
  ↓
search_docs → ok (3 hits, 来自 D01/D02/D03)
  ↓
检测多个 doc_id → get_doc_meta(D01)
  ↓
get_doc_meta → ok (scope=null, priority=null)
  ↓
元数据为空 → ask_user("请确认适用制度")
  ↓
answer → 终止
  ↓
完成（4 步）
```

**Trace**：examples/traces/conflict.json

### 4.3 资料外路径

```
查询："股票期权激励计划"
  ↓
search_docs → empty
  ↓
改写重试 → empty
  ↓
改写次数用尽 → answer("未找到相关文档")
  ↓
完成（3 步）
```

**Trace**：examples/traces/out_of_scope.json

### 4.4 工具失败路径

```
查询："报销流程"（注入 _fault）
  ↓
search_docs → error
  ↓
终止 → answer("工具调用失败")
  ↓
完成（1 步）
```

**Trace**：examples/traces/tool_error.json

## 5. 技术取舍

### 5.1 为什么用 Mock 模型而非真实 LLM？

**原因**：
- 考核重点在工程实现和流程验证，非模型效果
- Mock 可离线运行，无需 API Key
- 决策逻辑可解释，便于评审理解

**代价**：
- 不代表真实 LLM 决策效果
- 无法验证提示词质量

### 5.2 为什么用关键词匹配而非向量检索？

**原因**：
- 简单可靠，无需额外依赖
- 考核重点在 Agent 决策，非检索算法
- 数据量小（5 个文档），关键词匹配足够

**代价**：
- 语义理解能力弱
- 同义词/改写需要手动处理

### 5.3 为什么工具返回三态而非二态？

**原因**：
- `empty` 和 `error` 语义不同
- `empty`：数据不存在，可改写重试
- `error`：工具失败，需降级处理
- 区分两者让模型决策更精准

### 5.4 为什么循环中无业务 if？

**原因**：
- 遵循 AGENTS.md 硬约束
- 下一步动作只能来自 model_decide 返回值
- 便于替换数据和模型，不影响循环逻辑

**代价**：
- 模型需要更强的决策能力
- Mock 模型需要更复杂的规则

## 6. 可扩展点

1. **真实 LLM 接入**：实现 src/model/real.py 的 decide 方法
2. **向量检索**：替换 search_docs 为 embedding + 相似度匹配
3. **多轮对话**：扩展 conversation_history 处理
4. **工具扩展**：添加更多工具（如 SQL 查询、API 调用）
5. **多 Agent 协作**：拆分为检索 Agent、推理 Agent、回答 Agent
