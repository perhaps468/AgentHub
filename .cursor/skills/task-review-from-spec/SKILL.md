---
name: task-review-from-spec
description: Use when proposed tasks need review against the approved product vision and implementation plan before implementation begins.

---

# Task Review From Spec

根据已确认的总愿景和总实现方案评审 task。

它只负责：

- 检查 task 是否忠实于 spec
- 指出 task 的优点、问题、风险和缺口
- 给出是否通过或需要修改的结论

它不负责重新澄清需求，不负责重写总实现方案，也不负责编码。

## 核心规则

1. 评审必须以总愿景和总实现方案为准，不得脱离 spec 自行发明新范围。
2. 评审只指出问题、比较优劣、建议回写，不允许静默扩 scope。
3. 如果发现 task 有问题，返回修改意见；不要直接进入实现。
4. task 通过后，下一步才允许进入编码或 TDD。

## 默认输入

优先读取：

- `specs/product-vision.md`
- `specs/implementation-plan.md`
- `tasks/`

## 何时使用

在以下场景使用本技能：

- task 已拆好，准备进入实现前
- spec 更新后，需要重新检查现有 task 是否还合理
- 怀疑 task 拆分有越阶段、漏依赖或测试不足的问题

在以下场景不要使用本技能：

- 还没有总愿景或总实现方案
- 还没有 task
- 已经进入具体编码实现

## 评审重点

至少检查以下内容：

- task 是否对齐总愿景
- task 是否对齐总实现方案
- 是否存在越阶段实现
- 是否遗漏关键依赖
- 拆分粒度是否合适
- 测试方案是否充分
- 验收标准是否清晰

## 工作顺序

### 1. 先读 spec

确认当前阶段的目标、边界和不做什么。

### 2. 再读 task

看 task 是否真的服务于当前阶段，而不是偷偷带入未来能力。

### 3. 给出结论

结论只分两类：

- 通过
- 需要修改

如果需要修改，要明确指出：

- 哪个 task 有问题
- 问题是什么
- 应该如何改

### 4. 交给下一阶段

- 如果 task 通过，下一步进入编码或 `test-driven-development`
- 如果 task 不通过，回到 `task-planning-from-spec`

## 输出要求

使用本技能时，输出尽量包含：

- 评审结论
- 主要发现
- 需要修改的项
- 下一步

推荐格式：

```md
评审结论：
- 通过 / 需要修改

主要发现：
- ...

需要修改：
- ...

下一步：
- 进入 <skill-name>
```

## 常见错误

### 错误 1：评审变成重规划

修正：

- 只对 task 做判断，不重写愿景和总方案

### 错误 2：task 偷偷扩 scope

修正：

- 对照 spec 删除未批准范围

### 错误 3：测试方案过弱

修正：

- 补充验证路径和验收标准

### 错误 4：task 通过条件不清楚

修正：

- 明确"做到什么算完成"

## 与其他技能的边界

- `task-planning-from-spec`
  - 负责拆 task
- `test-driven-development`
  - 负责 task 通过后的实现
- `verification-before-completion`
  - 负责实现后的最终验证

本技能只负责评审 task，不负责后续执行。
