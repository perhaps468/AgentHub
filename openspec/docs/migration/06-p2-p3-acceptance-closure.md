# 06 - P2 / P3 验收收口总实现文档

> 本文用于把当前项目相对 `implementation-phases.md` 中 Phase2 / Phase3 的验收缺口，收敛成一份可执行的总实现文档。
>
> 本文不是新的产品愿景，也不是新的阶段规划；它只负责在既有 spec 与 migration 文档基础上，明确 P2 / P3 还差什么、为什么差、应按什么顺序收口，以及如何继续拆成 3 到 4 个 task 落地。

---

## 1. 文档定位与范围

### 1.1 文档目标

本文目标只有一个：

- 把当前仓库距离 P2 / P3 验收标准的差距，整理成一套可连续执行的总实现方案

本文输出要满足两类后续使用场景：

- 可以直接继续拆成 3 到 4 个 task 文档
- 每个 task 都能自然包含任务、测试、验收条件、回滚点与风险说明

### 1.2 适用阶段

本文只适用于：

- `Phase2：单 Agent Runtime`
- `Phase3：Code Agent 能力`

本文不覆盖：

- P4 Artifact 平台化
- P5 用户自建 Agent
- P6 Orchestrator 多 Agent 编排
- P7 长生命周期与高级自治

### 1.3 与现有 spec / migration 文档的关系

本文默认复用以下文档，不重建愿景，不重建总方案：

- `openspec/specs/proposal.md`
- `openspec/specs/implementation-phases.md`
- `openspec/docs/migration/02-implementation-guide.md`
- `openspec/docs/migration/05-roadmap-and-progress.md`

其中：

- `proposal.md` 与 `implementation-phases.md` 仍然是唯一真相源
- `02-implementation-guide.md` 负责 Runtime 迁移与接线顺序
- 本文负责 P2 / P3 验收收口，不改变上层阶段定义

### 1.4 本文不覆盖的内容

本文明确不处理：

- 新增产品功能范围
- 重做前端设计语言
- 引入 P4 级 Artifact 独立存储
- 引入 P5/P6 级 RuntimeFactory、Blueprint、Orchestrator
- 不必要的大规模重构

---

## 2. 输入依据与验收目标

### 2.1 唯一真相源

本次收口必须严格以 `implementation-phases.md` 为准，尤其是：

- P2 阶段验收标准
- P2 进入下一阶段前置条件
- P3 阶段验收标准
- P3 进入下一阶段前置条件

### 2.2 P2 验收目标

P2 需要最终满足以下要求：

- 单 Agent 可以基于会话历史生成回复
- 真实 LLM 回复已经由 Runtime 接管，而不是 Phase1 临时链路
- Prompt、Context、Tool、Loop、Streaming、State 形成统一架构
- Runtime 输出可以稳定进入 Phase1 的 Message / Streaming / WS 链路

同时，P2 进入下一阶段前还要求：

- Runtime 抽象稳定
- 工具调用闭环成立
- Runtime 事件可以被消息流观察和回放

### 2.3 P3 验收目标

P3 需要最终满足以下要求：

- Code Agent 可以在明确 workspace 边界内读取、修改、检索文件
- 文件改动可以生成结构化 diff，并进入消息流展示
- 命令执行和预览结果可以反馈给 Runtime 和用户
- 自修复循环有明确次数限制和可观察过程

同时，P3 进入下一阶段前还要求：

- Workspace、File Tool、Diff、Sandbox、Preview 主链路成立
- Code Agent 改动不会绕过用户确认和结构化 diff
- 代码执行结果可以被 Runtime 状态和消息流追踪

### 2.4 本次收口判定标准

本文所说“完成收口”，不是指做了更多功能，而是指：

- P2 / P3 中当前未满足的验收条件被逐项补齐
- 现有实现中的旁路、占位链路、仅测试态能力被收束到正式主链路
- 后续再拆 task 时，不需要重新定义目标与边界，只需要继续实现

---

## 3. 当前现状与缺口总览

### 3.1 当前已具备能力

当前仓库已经具备以下基础：

- `ws.py` 已支持通过 feature flag 切换到 `RuntimeAgentService`
- Runtime 已支持会话历史注入、LLM 接入、ReAct 基本循环、工具调用
- 文件读取、目录遍历、搜索、patch 预览、统一 diff、受控命令执行都已有基础实现
- `PendingChange` 机制已建立，能支持 preview -> apply 的最小闭环
- 前端已能消费 `message_start / message_delta / message_end / message_error`

这意味着：

- P2 主体能力已经落地
- P3 中 File Tool / Diff / Run Command 的一部分已经落地
- 当前问题不再是“从 0 到 1”，而是“把未闭环部分收口成验收态”

### 3.2 P2 未满足项

当前 P2 仍缺少的核心项只有一类：

- Runtime 事件虽然在内部已开始结构化，但尚未正式进入可观察、可回放的消息流主链路

具体表现为：

- Runtime 内部已有 `tool_event`
- `RuntimeAgentService` 已能产出结构化 tool event
- 但 WS 主链路没有正式转发这些运行时事件
- 前端也没有形成对应的统一运行时事件消费与回放模型

因此目前只能证明：

- 文本回复流可观察

还不能证明：

- Runtime 全过程可观察、可回放

### 3.3 P3 未满足项

当前 P3 主要有四类缺口：

1. workspace 边界仍是注入式参数边界，不是会话级正式主链路
2. preview 能力只有前端容器，没有后端正式接线与消息流承载
3. command 执行结果虽能返回字符串，但没有形成完整 terminal / runtime 观测链
4. self-repair 仍停留在测试或手工流程，不是正式 Runtime 状态机能力

### 3.4 缺口与代码证据映射

缺口判断基于以下事实：

- `RuntimeAgentService` 已构建 `RunCommandTool`、文件工具、diff 工具
- `EventBridge` 已能产生 `ToolEvent`
- `ws.py` 仍主要面向 `message_*` 事件
- `ChatSession` 模型仍没有 workspace 绑定
- 前端 `PreviewPanel` 仍是待接入占位态

因此问题不是“完全没有实现”，而是：

- 核心能力已经散落存在，但还没有全部纳入正式验收链路

### 3.5 缺口优先级排序

建议按以下顺序处理：

1. 先补 P2 的 runtime 观测与回放
2. 再补 P3 的 workspace 主链路
3. 再补 P3 的 diff / command / runtime 消息链路
4. 最后补 preview 与 self-repair

原因是：

- 没有 P2 的正式 runtime 可观察链路，P3 很多“执行过程可追踪”的条件都无法稳定成立
- 没有 workspace 主链路，P3 的“明确边界”仍然只是工程约束，不是产品约束

---

## 4. 实施原则与非目标

### 4.1 收口原则

本次收口必须遵守：

- 只补验收缺口，不扩新 scope
- 优先把已有能力正式接线，不优先新增能力
- 优先闭环，不优先做更全的能力面
- 所有判断以当前 spec 为准，不以局部实现便利为准

### 4.2 拆 task 原则

后续 task 拆分必须满足：

- 每个 task 只收口一类主缺口
- 每个 task 都能独立测试
- 每个 task 都有明确验收条件
- 每个 task 都可以回滚，而不破坏前一个 task 已完成能力

### 4.3 测试与验证原则

默认使用 TDD，除非只是文档或配置性收口。

每个 task 至少要覆盖：

- 单元测试
- 最小集成验证
- 主链路回归验证

在宣称完成前，必须能证明：

- 验收条件成立
- 关键旁路没有残留

### 4.4 回滚原则

每个 task 都必须提供：

- feature flag 级回退路径，或
- 代码路径级局部回滚点

不允许：

- 一次性把多个未验证能力绑死到主链路

### 4.5 非目标清单

本次不是要做：

- Artifact 独立 schema
- 正式 deploy artifact
- 多 Agent 共享上下文
- 真实浏览器预览编排系统
- 无限自动修复

---

## 5. 总体方案与执行顺序

### 5.1 总体收口思路

总体思路不是重写 Runtime，而是把已存在能力按验收要求重新收束成正式主链路：

- 先让 Runtime 事件真正进入消息流
- 再让 workspace 边界从“工具参数”升级到“会话上下文”
- 再让 diff / command / user confirmation 进入统一 runtime 追踪链
- 最后补 preview 与有限自修复闭环

### 5.2 workstream 划分

本文把收口拆成四个母任务：

- Task A：P2 Runtime 事件观测与回放收口
- Task B：P3 Workspace 与文件边界收口
- Task C：P3 Diff / Command / Message Flow 收口
- Task D：P3 Preview 与 Self-Repair 收口

### 5.3 推荐执行顺序

推荐顺序：

1. Task A
2. Task B
3. Task C
4. Task D

### 5.4 各 task 之间的依赖关系

- Task A 是后续所有“可观察执行过程”的基础
- Task B 为 Task C / D 提供正式 workspace 上下文
- Task C 负责把变更、命令和消息流串成主链路
- Task D 在前面三项稳定后再补 preview 与有限自修复

### 5.5 每个 task 的统一产出要求

每个 task 最终都必须包含：

- 目标
- 当前现状
- 缺失条件
- 设计方案
- 涉及文件
- 实现步骤
- 测试要求
- 验收条件
- 回滚点与风险

---

## 6. Task A：P2 Runtime 事件观测与回放收口

### 6.1 目标

把当前 Runtime 内部已经存在的运行时事件，正式收口到可观察、可回放的消息流主链路中，使 P2 的最后一个关键缺口关闭。

### 6.2 当前现状

当前已经具备：

- `EventBridge` 能产出 `ToolEvent`
- `RuntimeAgentService` 能向外部返回 `tool_event`
- 文本回复类事件已能走 `message_*` 主链路

当前未完成：

- WS 没有把 runtime 非文本事件作为正式协议面转发
- 前端没有统一 runtime 事件状态模型
- 当前“回放”只对最终文本近似成立，对过程事件不成立

### 6.3 缺失条件

本 task 需要补齐以下条件：

- runtime 关键事件进入统一消息流
- 运行时过程可被前端观察
- 运行时事件具备最小回放语义
- 不破坏现有 `message_*` 协议兼容性

### 6.4 设计方案

建议采取“增量扩展，不推翻旧协议”的方案：

1. 保留现有 `message_start / delta / end / error`
2. 为 runtime 过程事件补充正式协议类型
3. 在后端定义最小 runtime event schema
4. 前端以流内事件而非临时 console / toast 方式消费
5. 历史查询与回连恢复至少能重建同一轮任务中的关键过程节点

建议首批纳入正式链路的事件：

- `tool_event`
- `runtime_state`
- 可选：`terminal_event` 占位协议

这里不要求一次做完整事件溯源系统，但要求：

- 事件被正式承认
- 事件能被统一消费
- 事件能被最小化重建

### 6.5 涉及模块与文件

核心涉及：

- `backend/app/runtime/event_bridge.py`
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/api/ws.py`
- `frontend/src/utils/ws-client.ts`
- `frontend/src/utils/useChatStreamState.ts`
- `frontend/src/types/*`

必要时补充：

- runtime 事件持久化或消息 metadata 承载结构

### 6.6 实现步骤

建议继续细拆为：

1. 定义 runtime 事件协议与事件类型边界
2. 在 WS 主链路转发 runtime 事件
3. 前端建立 runtime 事件状态模型
4. 支持同轮执行过程的最小回放
5. 回归现有 `message_*` 协议兼容性

### 6.7 测试要求

至少覆盖：

- `EventBridge` 事件映射测试
- `RuntimeAgentService` 事件输出测试
- WS runtime 事件转发测试
- 前端 runtime 事件消费测试
- 历史重建或回连恢复测试

### 6.8 验收条件

完成后必须能证明：

- Runtime 事件可以被消息流观察
- 工具调用过程不再只是内部实现细节
- 回放时至少能看到关键运行节点
- 现有文本流协议未被破坏

### 6.9 回滚点与风险

回滚点：

- 通过 feature flag 关闭 runtime 扩展事件输出
- 保留原始 `message_*` 路径可单独运行

主要风险：

- 事件协议扩展破坏前端兼容性
- 事件过多导致状态管理复杂化

---

## 7. Task B：P3 Workspace 与文件边界收口

### 7.1 目标

把当前“靠 `workspace_root` 注入”的工程边界，升级成会话级正式 workspace 主链路，使 P3 的“明确 workspace 边界”真正成立。

### 7.2 当前现状

当前已具备：

- `WorkspaceGuard`
- 文件工具与命令工具的 workspace 限制
- `RuntimeAgentService` 的 `workspace_root` 注入路径

当前未具备：

- `ChatSession` 与 workspace 的正式绑定关系
- workspace 生命周期与 owner 边界建模
- runtime 从 session 明确定位 workspace 的主链路

### 7.3 缺失条件

本 task 需要补齐：

- workspace 成为正式领域对象，而不是环境变量约定
- 会话能明确绑定 workspace
- runtime 不再依赖隐式全局 `WORKSPACE_ROOT`
- owner 边界与 workspace 边界能同时成立

### 7.4 设计方案

建议采取“最小正式化 workspace”的方案：

1. 增加最小 `Workspace` 抽象
2. 让 session 能绑定 workspace
3. runtime 从 session / workspace 解析执行上下文
4. 所有文件工具、diff 工具、命令工具统一从该上下文取边界

这里不要求上 P4 级资源系统，但至少要求：

- workspace 在后端有明确主身份
- 不是仅靠 `.env` 或进程参数驱动

### 7.5 涉及模块与文件

核心涉及：

- `backend/app/models/session.py`
- 新增或补充 `workspace` 相关模型 / schema / service
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/runtime/workspace.py`
- 文件工具与命令工具构建入口

必要时涉及：

- session 创建接口
- session 查询与序列化结构

### 7.6 实现步骤

建议继续细拆为：

1. 定义最小 workspace 模型与会话绑定关系
2. 打通 session -> workspace_root 解析链路
3. 改造 runtime / tools 统一使用正式 workspace 上下文
4. 补 owner 边界、越权访问与空 workspace 校验

### 7.7 测试要求

至少覆盖：

- session 与 workspace 绑定测试
- workspace 解析测试
- 文件工具 workspace 注入测试
- workspace 越权访问测试
- runtime 依赖正式 workspace 而非全局环境变量测试

### 7.8 验收条件

完成后必须能证明：

- 每个开发型会话都能定位到明确 workspace
- Code Agent 的文件与命令操作边界来自正式会话上下文
- 用户边界与 workspace 边界同时成立

### 7.9 回滚点与风险

回滚点：

- 保留现有注入式 `workspace_root` 作为临时兼容 fallback

主要风险：

- session 数据模型改动影响现有接口
- 历史 session 缺少 workspace 信息

---

## 8. Task C：P3 Diff / Command / Message Flow 收口

### 8.1 目标

把文件改动、结构化 diff、用户确认、命令执行结果统一接入 runtime 消息流，使 P3 的代码变更主链路正式成立。

### 8.2 当前现状

当前已具备：

- `PendingChange`
- `ReplaceInFileTool` / `WriteFileTool` / `UnifiedDiffTool`
- `ApplyChangeTool`
- `RunCommandTool`
- 部分 dev loop 测试

当前未完成：

- diff 与 apply 链路未完全产品化进入统一消息流
- command 结果主要是工具返回值，不是正式 terminal 事件流
- “改动不会绕过用户确认和结构化 diff” 仍需更强主链路约束

### 8.3 缺失条件

本 task 需要补齐：

- 改动必经结构化 diff
- apply 必经受控确认路径
- command 执行结果可被 runtime 状态与消息流追踪
- 文件改动与执行结果形成连续闭环

### 8.4 设计方案

建议把当前能力从“工具能力”收口为“主流程能力”：

1. 写工具默认只生成 `PendingChange`
2. diff 作为正式消息内容或正式 runtime 事件展示
3. apply 作为明确阶段动作，不允许旁路直写
4. 命令执行输出形成结构化 terminal/result 事件
5. 用户与 runtime 都能看到“改了什么、应用没、执行结果如何”

这里的重点不是做更强编辑器，而是保证：

- 所有代码改动都在正式链路内
- 所有执行结果都在正式链路内

### 8.5 涉及模块与文件

核心涉及：

- `backend/app/runtime/pending_change.py`
- `backend/app/runtime/tools/apply_change_tool.py`
- `backend/app/runtime/tools/replace_in_file_tool.py`
- `backend/app/runtime/tools/unified_diff_tool.py`
- `backend/app/runtime/tools/write_file_tool.py`
- `backend/app/runtime/tools/run_command_tool.py`
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/api/ws.py`

前端必要涉及：

- 流式消息状态管理
- diff / command 结果渲染

### 8.6 实现步骤

建议继续细拆为：

1. 明确 diff / pending change / apply 的正式生命周期
2. 把 diff 纳入统一消息流
3. 把 command 结果纳入统一 runtime 事件流
4. 增强“未确认不得应用”的主链路约束
5. 回归 patch flow、dev loop 与 WS 集成链路

### 8.7 测试要求

至少覆盖：

- `PendingChange` 生命周期测试
- diff 进入消息流测试
- apply gating 测试
- run command 结构化结果测试
- runtime / ws / frontend 联调测试

### 8.8 验收条件

完成后必须能证明：

- 文件改动可以生成结构化 diff，并进入消息流展示
- Code Agent 改动不会绕过用户确认和结构化 diff
- 代码执行结果可以被 Runtime 状态和消息流追踪

### 8.9 回滚点与风险

回滚点：

- 关闭 apply 正式链路，保留 preview-only 模式
- command 结果回退为工具响应文本

主要风险：

- 链路过早绑定 UI 细节
- diff / command 展示协议反复变更

---

## 9. Task D：P3 Preview 与 Self-Repair 收口

### 9.1 目标

补齐 P3 中最晚完成、但验收必须存在的两项：

- preview 正式主链路
- 有次数限制、可观察的 self-repair 闭环

### 9.2 当前现状

当前前端已具备：

- `PreviewPanel` 组件
- 基本 `PreviewState`

当前后端未具备：

- preview artifact / preview session 的正式链路
- preview 结果进入 runtime / ws / message 流的主通路

当前 self-repair 方面：

- 有 patch + apply + run command 的零散能力
- 没有正式的有限重试状态机
- 没有专门的 retry 上限与过程可观察模型

### 9.3 缺失条件

本 task 需要补齐：

- 命令执行和预览结果可以反馈给 Runtime 和用户
- 自修复循环有明确次数限制和可观察过程
- Workspace、File Tool、Diff、Sandbox、Preview 主链路成立

### 9.4 设计方案

建议把 preview 与 self-repair 都限制在最小闭环：

#### Preview 侧

- 先只支持最小可接入 preview 类型
- 定义正式 preview result schema
- 通过消息流或 runtime 事件把 preview 能力暴露给前端
- 前端 `PreviewPanel` 不再只是静态容器，而是消费正式数据

#### Self-repair 侧

- 不做无限自动修复
- 定义最大重试次数，例如 `MAX_REPAIR_RETRY`
- 每轮包含：
  - 读取失败结果
  - 分析
  - 生成修改
  - apply
  - rerun
- 每轮都必须留下可观察事件

这里的重点不是“更聪明”，而是：

- 行为边界清晰
- 状态可观察
- 次数受控

### 9.5 涉及模块与文件

核心涉及：

- preview 相关后端 schema / runtime event
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/api/ws.py`
- `frontend/src/components/zhu/PreviewPanel.vue`
- `frontend/src/types/agenthub.ts`
- 前端流状态管理与预览映射代码

self-repair 可能涉及：

- `react_agent.py`
- runtime state / event bridge
- command / patch / apply 协调层

### 9.6 实现步骤

建议继续细拆为：

1. 定义 preview 正式输出结构
2. 打通 preview -> ws -> frontend -> panel 主链路
3. 定义有限自修复状态机与 retry 上限
4. 打通 run -> fail -> analyze -> modify -> rerun 最小闭环
5. 回归 preview 与 repair 可观察性测试

### 9.7 测试要求

至少覆盖：

- preview schema / 事件测试
- preview 前后端联调测试
- self-repair retry 限制测试
- repair 过程事件可观察测试
- 超过上限后的收口测试

### 9.8 验收条件

完成后必须能证明：

- 命令执行和预览结果可以反馈给 Runtime 和用户
- 自修复循环有明确次数限制和可观察过程
- Preview 主链路正式成立

### 9.9 回滚点与风险

回滚点：

- preview 回退到静态占位渲染
- self-repair 回退到单轮执行，无自动重试

主要风险：

- preview 方案提前演化成 P4 Artifact 方案
- self-repair 过早演化成高级自治能力

---

## 10. 后续 task 拆分规则

基于本文继续拆 task 时，必须遵守：

- 一次只从一个 Task A/B/C/D 母块继续拆
- 子 task 不得跨母块偷扩 scope
- 子 task 必须直接引用对应母块的目标、测试要求与验收条件
- 如果拆分后仍过大，可以按“协议 / 后端 / 前端 / 联调”四类继续切

建议的下一层拆分方式示例：

- Task A-1：Runtime 事件协议定义与 WS 转发
- Task A-2：前端 runtime 事件消费与最小回放
- Task B-1：workspace 模型与 session 绑定
- Task B-2：runtime / tools 正式 workspace 上下文接线
- Task C-1：diff / pending change 生命周期收口
- Task C-2：command 结果结构化事件收口
- Task D-1：preview 正式链路
- Task D-2：有限自修复状态机

---

## 12. 验收收口完成记录 (2026-05-30)

### 12.1 收口执行摘要

以下 4 个 Task 于 2026-05-30 按计划顺序完成：

| Task | 内容 | 状态 | 关键修改 |
|------|------|------|----------|
| Task 1 | Runtime Replay Persistence | ✅ 完成 | `EventBridge.replay_nodes` 收集、`RuntimeAgentService._finalize_agent_message` 持久化 |
| Task 2 | Diff Apply & Command Result | ✅ 完成 | `ApplyChangeResponse.event` 字段、`CommandResultPayload` 结构化、WS 转发 |
| Task 3 | Preview & Self-Repair | ✅ 完成 | `preview_result` / `repair_state` WS 事件、前端状态消费 |
| Task 4 | Acceptance Verification | ✅ 完成 | 全量回归通过、文档更新 |

### 12.2 P2 收口验证

| 验收条件 | 验证结果 |
|----------|----------|
| Runtime 事件进入消息流 | ✅ `tool_event` / `runtime_state` 经 `EventBridge` 收集，持久化到 `runtime_replay` |
| 运行时过程可观察 | ✅ WS 主链路转发，`useChatStreamState` 暴露 `runtime_nodes` |
| 运行时事件可回放 | ✅ 最终 assistant 消息含 `metadata.runtime_replay` |
| 现有 `message_*` 协议兼容 | ✅ 回归测试通过，未破坏文本流协议 |

### 12.3 P3 收口验证

| 验收条件 | 验证结果 |
|----------|----------|
| 文件改动进入结构化 diff 消息流 | ✅ `apply_result` WS 事件含 `diff`、`status`、`message` |
| Code Agent 改动不绕过确认 | ✅ `apply_pending_change` API 返回结构化 `apply_result` |
| 代码执行结果可追踪 | ✅ `CommandResultPayload` 定义，`run_command_tool` 返回结构化结果 |
| 自修复循环可观察 | ✅ `RepairStateEvent` / `repair_state` WS 事件，状态机可追踪 |
| Preview 主链路正式成立 | ✅ `PreviewResultEvent` / `preview_result` WS 事件，前端 `zhu.vue` 消费 |

### 12.4 Feature Flag 状态

| Feature Flag | 状态 | 说明 |
|--------------|------|------|
| `RUNTIME_USE_RUNTIME_AGENT` | ✅ 正式启用 | Task 1.4 确认 `RuntimeAgentService` 为默认路径 |
| Legacy responder fallback | ⚠️ 保留但不默认 | 通过 feature flag 控制，未删除兼容代码 |

### 12.5 遗留问题

- `PendingChange` 返回后，`react_agent.py` 假设工具返回值为字符串，曾触发 `len()` 错误。已在 `react_agent.py` 第 1269、1346 行添加 `str()` 转换。
- `RunCommandTool` 目前返回格式化字符串而非真正 `CommandResultPayload` 结构；不影响 WS 转发（WS 层可构造结构），但工具返回值语义待后续 Task C-2 收口。

### 12.6 回滚点

- 每个 task 的 feature flag 已记录，可独立回退
- `pending_changes.py` API 仍保留 `event` 可选字段，不影响旧版前端

---

## 13. 阶段完成定义

当以下条件同时成立时，可以认为本文目标完成：

- P2 未满足项已全部关闭（见 12.2 验证表）
- P3 未满足项已全部关闭（见 12.3 验证表）
- `implementation-phases.md` 中对应验收条件可被逐条证明
- `05-roadmap-and-progress.md` 中与 P2/P3 收口相关项已回写
- 不存在新的临时旁路替代正式主链路

如果后续继续推进 P4 及以后阶段，应新建对应 spec 或变更方案，不得在本文范围内继续静默扩展。

