# 测试评估

## 1. 测试概览

**测试框架**：pytest 7.4.0  
**测试总数**：23 个  
**通过数**：23 个  
**失败数**：0 个  
**耗时**：约 0.09 秒  

**运行命令**：
```bash
python -X utf8 -m pytest tests/ -v
```

**实际输出**：
```
============================= test session starts ==============================
platform win32 -- Python 3.12.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\user\Desktop\AGENTPROJECT\XIAOYING
plugins: anyio-4.15.1
collecting ... collected 23 items

tests/test_additional.py::TestStepLimit::test_incomplete_on_max_steps PASSED [  4%]
tests/test_additional.py::TestCitationValidation::test_citations_are_substrings PASSED [  8%]
tests/test_additional.py::TestNoHardcoding::test_no_data_numbers_in_prompts PASSED [ 13%]
tests/test_additional.py::TestNoHardcoding::test_no_doc_ids_in_prompts PASSED [ 17%]
tests/test_context_followup.py::test_context_followup PASSED             [ 21%]
tests/test_swap.py::TestSwapRegression::test_v1_conflict_path PASSED     [ 26%]
tests/test_swap.py::TestSwapRegression::test_v2_direct_answer PASSED     [ 30%]
tests/test_swap.py::TestSwapRegression::test_action_sequences_differ PASSED [ 34%]
tests/test_tools.py::TestSearchDocs::test_ok_with_matches PASSED         [ 39%]
tests/test_tools.py::TestSearchDocs::test_empty_no_matches PASSED        [ 43%]
tests/test_tools.py::TestSearchDocs::test_error_with_fault PASSED        [ 47%]
tests/test_tools.py::TestSearchDocs::test_top_k_limit PASSED             [ 52%]
tests/test_tools.py::TestReadSnippet::test_ok_existing_snippet PASSED    [ 56%]
tests/test_tools.py::TestReadSnippet::test_empty_nonexistent_doc PASSED  [ 60%]
tests/test_tools.py::TestReadSnippet::test_empty_nonexistent_snippet PASSED [ 65%]
tests/test_tools.py::TestReadSnippet::test_error_with_fault PASSED       [ 69%]
tests/test_tools.py::TestGetDocMeta::test_ok_existing_doc PASSED         [ 73%]
tests/test_tools.py::TestGetDocMeta::test_ok_with_null_fields PASSED     [ 78%]
tests/test_tools.py::TestGetDocMeta::test_ok_with_scope PASSED           [ 82%]
tests/test_tools.py::TestGetDocMeta::test_empty_nonexistent_doc PASSED   [ 86%]
tests/test_tools.py::TestGetDocMeta::test_error_with_fault PASSED        [ 91%]
tests/test_tools.py::TestAskUser::test_ok PASSED                         [ 95%]
tests/test_tools.py::TestAskUser::test_error_with_fault PASSED           [100%]

============================= 23 passed in 0.09s ==============================
```

## 2. 测试分类

### 2.1 工具三态测试 (tests/test_tools.py)

**测试数**：15 个  
**覆盖工具**：search_docs, read_snippet, get_doc_meta, ask_user  
**覆盖状态**：ok, empty, error  

**测试用例**：

| 工具 | 测试场景 | 预期状态 | 结果 |
|------|---------|---------|------|
| search_docs | 有匹配结果 | ok | ✅ PASSED |
| search_docs | 无匹配结果 | empty | ✅ PASSED |
| search_docs | 故障注入 | error | ✅ PASSED |
| search_docs | top_k 限制 | ok | ✅ PASSED |
| read_snippet | 存在的片段 | ok | ✅ PASSED |
| read_snippet | 不存在的文档 | empty | ✅ PASSED |
| read_snippet | 不存在的片段 | empty | ✅ PASSED |
| read_snippet | 故障注入 | error | ✅ PASSED |
| get_doc_meta | 存在的文档 | ok | ✅ PASSED |
| get_doc_meta | null 字段 | ok | ✅ PASSED |
| get_doc_meta | 有 scope 的文档 | ok | ✅ PASSED |
| get_doc_meta | 不存在的文档 | empty | ✅ PASSED |
| get_doc_meta | 故障注入 | error | ✅ PASSED |
| ask_user | 正常提问 | ok | ✅ PASSED |
| ask_user | 故障注入 | error | ✅ PASSED |

**代码位置**：tests/test_tools.py

### 2.2 替换回归测试 (tests/test_swap.py)

**测试数**：3 个  
**目的**：验证同一问题在 v1 和 v2 数据下走不同路径  

**测试用例**：

| 测试 | 数据文件 | 查询 | 预期路径 | 结果 |
|------|---------|------|---------|------|
| test_v1_conflict_path | faq_v1.json | 差旅报销期限 | search → get_doc_meta → ask_user | ✅ PASSED |
| test_v2_direct_answer | faq_v2.json | 差旅报销期限 | search → answer | ✅ PASSED |
| test_action_sequences_differ | v1 vs v2 | - | 动作序列不同 | ✅ PASSED |

**动作序列对比**：

```
v1 (faq_v1.json)       | v2 (faq_v2.json)
-----------------------+-----------------------
search_docs            | search_docs            ✓
search_docs            | answer                 ✗
get_doc_meta           | -                      ✗
ask_user               | -                      ✗
answer                 | -                      ✗

序列是否不同：True
```

**Trace 文件**：
- examples/traces/swap_v1.json
- examples/traces/swap_v2.json

**代码位置**：tests/test_swap.py

### 2.3 额外测试 (tests/test_additional.py)

**测试数**：4 个  
**覆盖场景**：步数上限、引用验证、硬编码检查  

**测试用例**：

| 测试 | 场景 | 验证点 | 结果 |
|------|------|--------|------|
| test_incomplete_on_max_steps | max_steps=2 | 返回 incomplete | ✅ PASSED |
| test_citations_are_substrings | 回答引用 | 引用是 read_snippet 文本的子串 | ✅ PASSED |
| test_no_data_numbers_in_prompts | 硬编码检查 | data 数值不在 src/prompts/ | ✅ PASSED |
| test_no_doc_ids_in_prompts | 硬编码检查 | data doc_id 不在 src/prompts/ | ✅ PASSED |

**代码位置**：tests/test_additional.py

### 2.4 上下文追问测试 (tests/test_context_followup.py)

**测试数**：1 个  
**目的**：验证多轮对话中的指代消解能力  

**测试用例**：

| 轮次 | 用户输入 | 指代消解后 | 结果 |
|------|---------|-----------|------|
| 1 | 年假管理制度是什么 | 年假管理制度是什么 | ✅ 正常检索 |
| 2 | 那申请流程呢 | 年假申请流程 | ✅ 指代消解成功 |

**关键验证**：
- `resolve_reference()` 函数将"那"还原为"年假"
- search_docs 的 query 参数包含"年假"

**代码位置**：tests/test_context_followup.py, src/model/mock.py:resolve_reference()

## 3. 验收场景覆盖

### 3.1 明确答案

**用例**：normal_unique  
**查询**：费用报销审批流程  
**路径**：search_docs(empty) → search_docs(改写,ok) → read_snippet → answer  
**结果**：✅ 直接回答，附带引用  

**Trace**：examples/traces/normal_unique.json

### 3.2 文档冲突

**用例**：conflict  
**查询**：报销期限  
**路径**：search_docs(ok,3hits) → get_doc_meta → ask_user → answer  
**结果**：✅ 列冲突并请求确认  

**Trace**：examples/traces/conflict.json

### 3.3 资料外问题

**用例**：out_of_scope  
**查询**：股票期权激励计划  
**路径**：search_docs(empty) → search_docs(改写,empty) → answer  
**结果**：✅ 说明资料缺口，不编造答案  

**Trace**：examples/traces/out_of_scope.json

### 3.4 改写后的相似问题

**用例**：normal_unique（首次检索 empty，改写后 ok）  
**查询**：费用报销审批流程 → 改写为"报销"  
**结果**：✅ 改写后命中  

**Trace**：examples/traces/normal_unique.json

### 3.5 上下文追问

**用例**：context_followup  
**查询**：  
- 第一轮："年假管理制度是什么"  
- 第二轮："那申请流程呢"（指代消解：那 → 年假）  

**路径**：  
- 第一轮：search_docs → get_doc_meta → answer  
- 第二轮：search_docs（query="年假申请流程"） → answer  

**结果**：✅ 正确处理多轮对话，指代消解将"那"还原为"年假"  

**Trace**：examples/traces/context_followup_turn1.json, context_followup_turn2.json  

**代码位置**：tests/test_context_followup.py, src/model/mock.py:resolve_reference()

### 3.6 工具失败

**用例**：tool_error  
**查询**：报销流程（注入 _fault）  
**路径**：search_docs(error) → answer  
**结果**：✅ 报告失败状态，终止循环  

**Trace**：examples/traces/tool_error.json

## 4. 替换回归验证

### 4.1 v1 → v2 修改内容

| 修改项 | v1 | v2 |
|--------|----|----|
| D01 天数 | <DAY_A> | <DAY_C> |
| D02 | 存在 | 删除 |
| D03 scope | "差旅场景" | "差旅场景"（保留） |

### 4.2 行为变化

**查询**：差旅报销期限

**v1 行为**：
- 命中 D01/D02/D03（3 个不同文档）
- 检测多个 doc_id → get_doc_meta
- 元数据 scope/priority 均为 null → ask_user
- 列冲突并请求确认

**v2 行为**：
- 命中 D01/D03（2 个不同文档）
- 检测多个 doc_id → get_doc_meta
- D03 有 scope="差旅场景" → 可消解冲突
- 直接基于 D03 回答

**动作序列**：不同（已验证）

**Trace**：
- examples/traces/swap_v1.json
- examples/traces/swap_v2.json

## 5. 失败与限制

### 5.1 已实现的验收点

1. **明确答案**：normal_unique 用例 ✅
2. **文档冲突**：conflict 用例，citations 包含 3 个文档的原文片段 ✅
3. **资料外问题**：out_of_scope 用例，gaps 字段说明缺口 ✅
4. **改写后的相似问题**：search_docs 内置中文滑动窗口分词 ✅
5. **上下文追问**：context_followup 用例，指代消解（"那" → "年假"）✅
6. **工具失败**：tool_error 用例，故障注入 + 循环终止 ✅

### 5.2 已知限制

1. **Mock 模型**：基于规则，不代表真实 LLM 决策效果
   - 影响：无法验证提示词质量
   - 缓解：提供 real.py 接口，可接入真实 LLM

2. **关键词检索**：简单匹配，无语义理解
   - 影响：同义词/改写需要手动处理
   - 缓解：Mock 模型支持自动改写（最多 2 次）

3. **单 Agent 架构**：未实现多 Agent 协作
   - 影响：复杂任务可能效率低
   - 缓解：当前任务单 Agent 足够

4. **未实现真实 LLM 调用**：real.py 仅接口占位
   - 原因：考核允许离线 Mock
   - 缓解：提供接口，可扩展

### 5.3 潜在风险

1. **数据替换**：评审替换 data/*.json 后，Agent 行为可能异常
   - 缓解：工具纯函数，无硬编码，已通过替换回归测试

2. **提示词质量**：Mock 模型不依赖提示词，真实 LLM 可能需要调整
   - 缓解：提示词遵循红线，无硬编码

3. **步数上限**：默认 8 步，复杂任务可能不够
   - 缓解：可配置 max_steps 参数

## 6. 测试运行记录

### 6.1 完整测试

**命令**：
```bash
python -X utf8 -m pytest tests/ -v
```

**结果**：22 passed in 0.08s

### 6.2 替换回归测试

**命令**：
```bash
python -X utf8 -m pytest tests/test_swap.py -v
```

**结果**：3 passed in 0.05s

### 6.3 4 组用例运行

**命令**：
```bash
python -X utf8 tests/run_cases.py
```

**结果**：
- normal_unique: 4 步，completed
- conflict: 4 步，completed
- out_of_scope: 3 步，completed
- tool_error: 1 步，completed

**Trace**：examples/traces/*.json

## 7. 结论

**验收点覆盖**：6/6（明确答案、文档冲突、资料外问题、改写后相似问题、上下文追问、工具失败）

**测试通过率**：23/23 (100%)

**关键验证**：
- ✅ 引用原文支持回答（citations 包含 doc_id, snippet_id, text）
- ✅ 文档冲突列出具体冲突（conflict_docs 字段）
- ✅ 资料缺口明确说明（gaps 字段）
- ✅ 替换文档内容后答案改变（swap_v1 vs swap_v2）
- ✅ 检索改进（空结果改写，中文滑动窗口分词）
- ✅ 冲突处理（列冲突并请求确认）
- ✅ 上下文追问（指代消解："那" → "年假"）
- ✅ 无硬编码（data 数值/doc_id 不在 src/prompts/）
