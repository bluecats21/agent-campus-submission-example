# 复盘总结

## 1. 最难问题

### 1.1 Agent 循环中的业务判断

**问题描述**：  
初版 Agent 循环中，我写了如下代码：

```python
# 初版（错误）
if len(hits) >= 2:
    # 检查是否冲突
    doc_ids = set(h["doc_id"] for h in hits)
    if len(doc_ids) > 1:
        # 多个不同文档，走冲突路径
        next_action = "get_doc_meta"
    else:
        # 同一文档的多个片段，直接读取
        next_action = "read_snippet"
```

**被打回原因**：  
违反了 AGENTS.md 硬约束 #3："Agent 循环中不得出现 if '冲突'、if 天数不等、if 命中数>1 这类业务判断。下一步动作只能来自 model_decide(state) 的返回值。"

**解决方案**：  
将业务判断移到 model_decide 中，循环只负责执行：

```python
# 修正版（正确）
decision = model_decide(state)  # 下一步动作来自这一行的返回值
action = decision["action"]
args = decision["args"]
observation = execute_action(action, args)
```

**学习收获**：  
- Agent 循环应该是"执行器"，而非"决策器"
- 业务逻辑应该封装在模型层，便于替换
- 遵循单一职责原则，循环只负责状态更新和工具调用

### 1.2 Mock 模型的决策逻辑

**问题描述**：  
初版 Mock 模型使用文本匹配判断冲突：

```python
# 初版（错误）
if "30" in text and "15" in text:
    # 发现冲突
    return ask_user(...)
```

**被打回原因**：  
违反了 AGENTS.md 硬约束 #2："src/ 下任何提示词、注释、示例中不得出现具体天数、doc_id、业务答案。评审会替换 data 内容重跑，硬编码即关键缺陷。"

**解决方案**：  
改为基于结构信息决策：

```python
# 修正版（正确）
hits = observation.get("hits", [])
unique_doc_ids = set(hit["doc_id"] for hit in hits)

if len(unique_doc_ids) > 1:
    # 多个不同文档，检查元数据
    return {"action": "get_doc_meta", ...}
else:
    # 唯一文档，直接读取
    return {"action": "read_snippet", ...}
```

**学习收获**：  
- 决策应该基于结构信息（status、hits 数量、doc_id 集合），而非文本内容
- 硬编码业务答案是可维护性的大敌
- 替换数据后，Agent 行为应该随之改变

### 1.3 工具返回的三态设计

**问题描述**：  
初版工具只返回两态：成功/失败

```python
# 初版（不完善）
return {"success": True, "data": ...}
return {"success": False, "error": ...}
```

**问题暴露**：  
在测试 out_of_scope 场景时，发现"无结果"和"工具失败"被混为一谈：

```python
# 问题：empty 和 error 都返回 success=False
if not result["success"]:
    # 无法区分是"无结果"还是"工具失败"
    return "处理失败"
```

**解决方案**：  
改为三态设计：

```python
# 修正版（正确）
return {"status": "ok", "hits": [...], "error": None}
return {"status": "empty", "hits": [], "error": None}
return {"status": "error", "hits": [], "error": "工具调用失败"}
```

**学习收获**：  
- `empty` 和 `error` 语义不同：empty 可改写重试，error 需降级处理
- 三态设计让模型决策更精准
- 状态机比布尔值更具表达力

### 1.4 替换回归测试的设计

**问题描述**：  
初版没有替换回归测试，只在固定数据上验证。

**问题暴露**：  
评审提出质疑："如果替换 data/*.json，Agent 行为是否会改变？"

**解决方案**：  
创建 faq_v2.json，设计替换回归测试：

```python
# v1: D01/D02/D03/D04
# v2: D01/D03/D04（删 D02，改 D01 天数）

# 同一查询"差旅报销期限"
# v1: 命中 D01/D02/D03 → 冲突 → ask_user
# v2: 命中 D01/D03 → D03 有 scope → 直接回答
```

**学习收获**：  
- 替换回归是验证"无硬编码"的金标准
- 数据驱动的行为比代码驱动的行为更重要
- 测试应该覆盖"数据变化 → 行为变化"的场景

## 2. 踩坑记录

### 2.1 故障注入的参数传递

**坑**：  
初版 ask_user 不支持 _data_file 参数，导致替换测试报错：

```
TypeError: ask_user() got an unexpected keyword argument '_data_file'
```

**原因**：  
只给 search_docs/read_snippet/get_doc_meta 添加了 _data_file，忘了 ask_user。

**解决**：  
给所有工具统一添加 _data_file 参数（即使 ask_user 不使用）。

**教训**：  
- 接口一致性很重要
- 测试要覆盖所有工具

### 2.2 Mock 模型的改写计数

**坑**：  
初版 Mock 模型在空结果时无限改写：

```python
# 初版（错误）
if status == "empty":
    return {"action": "search_docs", "args": {"query": rewritten}}
```

**结果**：  
死循环，直到触发 max_steps。

**解决**：  
添加改写计数器：

```python
# 修正版（正确）
def __init__(self):
    self.rewrite_count = 0
    self.max_rewrites = 2

if status == "empty":
    if self.rewrite_count < self.max_rewrites:
        self.rewrite_count += 1
        return {"action": "search_docs", ...}
    else:
        return {"action": "answer", "args": {"content": "未找到相关文档"}}
```

**教训**：  
- 状态机需要终止条件
- 计数器要重置（每次 run_agent 调用）

### 2.3 Trace 文件的重复保存

**坑**：  
run_agent 和 test_swap 都保存 trace，导致同一文件被写两次。

**原因**：  
run_agent 内部调用 save_trace，test_swap 又手动保存一次。

**解决**：  
统一由 run_agent 保存，测试只负责调用。

**教训**：  
- 职责要清晰，避免重复逻辑
- 测试不应该修改被测函数的行为

### 2.4 硬编码检查的误判

**坑**：  
初版硬编码检查把所有数字都当作硬编码：

```python
# 初版（过于严格）
for num in numbers:
    if num in content:
        pytest.fail(f"包含数值：{num}")
```

**结果**：  
提示词中的"最多 2 次改写"的"2"也被报错。

**解决**：  
跳过长度<2 的数值：

```python
# 修正版（合理）
for num in numbers:
    if len(num) < 2:  # 跳过 1, 2, 3 等
        continue
    if num in content:
        pytest.fail(...)
```

**教训**：  
- 测试规则要合理，避免误判
- 占位符和通用数值应该被允许

## 3. 学习收获

### 3.1 架构设计

**ReAct 模式**：  
- 思考（Thought）→ 动作（Action）→ 观察（Observation）→ 循环
- 关键是"决策与执行分离"：model_decide 负责决策，loop 负责执行

**纯函数设计**：  
- 工具不依赖全局状态，便于测试和替换
- 通过参数传递数据源（_data_file），支持多版本数据

**三态设计**：  
- ok / empty / error 语义清晰
- 不同状态触发不同决策路径

### 3.2 工程实践

**测试驱动**：  
- 先写测试，再写实现
- 测试覆盖正常/异常/边界场景

**文档即代码**：  
- 文档中引用的文件必须存在
- 文档中描述的函数必须实现
- 文档是代码的延伸

**渐进式开发**：  
- 小步走，每步验收
- 先实现核心链路，再扩展功能
- 避免一次性改动过多

### 3.3 AI 协作

**提示词工程**：  
- 明确的约束比模糊的期望更有效
- 红线（不能做什么）比目标（要做什么）更重要
- 示例（few-shot）要谨慎，避免引入硬编码

**代码审查**：  
- AI 生成的代码必须人工审查
- 重点关注：业务逻辑、硬编码、接口一致性
- 不要盲目信任 AI 的输出

**验证方法**：  
- 运行测试是最直接的验证
- grep 检查硬编码
- 替换数据验证行为变化

## 4. 下一步改进

### 4.1 功能扩展

1. **真实 LLM 接入**  
   - 实现 src/model/real.py 的 decide 方法
   - 接入 OpenAI/Claude API
   - 验证提示词质量

2. **多轮对话**  
   - 扩展 conversation_history 处理
   - 实现上下文追问
   - 支持指代消解

3. **向量检索**  
   - 替换关键词匹配为 embedding + 相似度
   - 提升语义理解能力
   - 支持同义词检索

### 4.2 工程优化

1. **日志系统**  
   - 添加详细的执行日志
   - 记录每步决策理由
   - 便于调试和审计

2. **性能优化**  
   - 缓存文档加载结果
   - 优化检索算法
   - 减少重复计算

3. **错误处理**  
   - 更细粒度的错误分类
   - 优雅降级策略
   - 用户友好的错误提示

### 4.3 测试增强

1. **覆盖率检查**  
   - 集成 pytest-cov
   - 目标：代码覆盖率 > 80%

2. **集成测试**  
   - 端到端测试
   - 多场景组合测试
   - 压力测试

3. **回归测试**  
   - 自动化 CI/CD
   - 每次提交自动运行
   - 防止引入新 bug

## 5. 总结

**项目成果**：  
- ✅ 实现了完整的 ReAct Agent 循环
- ✅ 4 个工具，三态返回，支持故障注入
- ✅ Mock 模型，基于规则决策，无硬编码
- ✅ 22 个测试，全部通过
- ✅ 替换回归验证，v1/v2 行为不同
- ✅ 完整文档，引用真实文件

**核心经验**：  
1. **决策与执行分离**：循环不做业务判断，模型负责决策
2. **数据驱动行为**：不硬编码业务答案，替换数据后行为改变
3. **测试即验证**：运行测试、grep 检查、替换回归，三重验证
4. **小步快跑**：每完成一个模块就验收，避免积累问题

**不足之处**：  
- ❌ 未实现多轮对话上下文追问
- ❌ 未接入真实 LLM
- ❌ 检索算法简单（关键词匹配）

**自我评价**：  
项目达到了考核要求的核心目标，实现了可运行、可测试、可替换的 Agent 系统。虽然功能有限，但工程实践规范，测试覆盖充分，文档完整准确。

**感谢**：  
感谢 Qoder Desktop (Claude Sonnet 4.5) 的代码生成和文档编写辅助，节省了约 30% 的工作量。核心设计决策和验证仍由人工完成。
