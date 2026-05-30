---
name: task-planning-from-spec
description: Use when an approved implementation plan needs to be decomposed into backend/API scoped tasks with implementation steps, test plans, acceptance criteria, and request/response contracts.
---

# Task Planning From Spec

把已确认的总愿景和总实现方案拆成可执行 task。

本技能只负责拆 task，不重新澄清需求、不评审 task、不进入编码。

## 核心规则

1. task 必须严格基于总愿景和总实现方案，不得自行扩 scope。
2. 不要写前端任务；如涉及前后端协作，只定义后端/API 契约和联调要求。
3. 一个 task 只覆盖一个清晰目标，不要把多个阶段目标揉在一起。
4. task 必须能验证；必须包含测试方案和验收标准。
5. 接口是 task 文档的重要部分。（但是不一定，有些task没有具体要实现的接口的话就不用）
   - 请求方法、路径、认证方式
   - 请求参数、query、path、body 字段
   - 响应字段
   - 每个字段的含义、类型、是否必填
   - 字段的可能值或枚举范围
   - 主要错误响应和触发条件
6. 拆完 task 后停止，下一步交给 `task-review-from-spec`。

## 输入

优先读取项目已确认的总愿景、总实现方案和已有 task，避免重复拆分。

在 AgentHub 中，默认以以下文档为准：

- `openspec/specs/proposal.md`
- `openspec/specs/roadmap.md`
- `openspec/specs/implementation-phases.md`

如果 spec 还模糊或互相冲突，停止拆分，返回上游修 spec。

## 每个 task 至少包含

- 任务目标
- 当前范围
- 不做什么
- 依赖与前置条件
- 需要改动的后端模块、数据模型、接口或配置
- 接口契约（如涉及接口）
- 详细实现步骤
- 测试方案
- 验收标准

## 工作顺序

1. 读取 spec，确认当前阶段目标、边界和不做事项。
2. 按阶段、后端模块、数据模型、接口依赖拆分 task。
3. 为每个 task 写清实现步骤、接口契约、测试方案和验收标准。
4. 检查粒度：不要横跨多个阶段，也不要拆成没有独立业务意义的微任务。
5. 输出本次生成或更新的 task、依赖/阻塞，以及下一步应进入 `task-review-from-spec`。

## 需求变更处理

如果 spec 有更新，只增量修改受影响 task；不要整批重写，除非阶段边界已经变化。
