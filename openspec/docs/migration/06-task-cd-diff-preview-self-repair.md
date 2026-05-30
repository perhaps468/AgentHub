# Task C Remaining + Task D - Diff / Preview / Self-Repair 收口

> 本文建立在以下文档完成的基础上：
>
> - [06-task-bc1-workspace-session-binding.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/06-task-bc1-workspace-session-binding.md)
> - [06-task-c2-helloworld-confirmed-write-flow.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/06-task-c2-helloworld-confirmed-write-flow.md)
>
> 本文负责收口剩余的 `Task C` 与 `Task D`：把当前最小闭环推广成更通用的 diff / apply / command / preview / self-repair 主链路，并明确前端需要补齐的能力与严格测试要求。

---

## 1. 文档目标与范围

### 1.1 目标

本文目标是把当前“单文件预览 + 确认落盘”的最小链路，扩展为 P3 可验收的正式链路：

- diff 可被前端正式展示
- 待确认改动可被管理和追踪
- apply 后状态与结果一致
- 命令执行结果可以进入消息流并反馈给用户
- preview 结果可以正式接入前端展示
- self-repair 具备明确次数上限和可观察过程

### 1.2 本文覆盖内容

- `PendingChange` 生命周期收口
- diff 消息结构与前端渲染
- apply 结果同步
- command 结果消息流
- preview 主链路
- 有限 self-repair 闭环
- 前端状态管理与组件补齐
- 严格测试矩阵

### 1.3 本文不覆盖内容

- 多 Agent 编排
- Artifact 独立平台化
- 长生命周期任务
- 无限自动修复
- 通用 IDE 级编辑体验

---

## 2. 当前现状与缺口总览

### 2.1 已完成前置能力

当前已完成的前置能力包括：

- 所有会话绑定工作区的方案已明确
- runtime / tools 能通过 session 绑定 workspace 取边界
- `PendingChange`、`WriteFileTool`、`ReplaceInFileTool`、`UnifiedDiffTool` 已存在
- `ApplyChangeTool` 已存在
- 最小单文件 `HelloWorld.java` 预览 -> 确认 -> 落盘流程已定义

### 2.2 Task C 已被前置覆盖的部分

原始 `Task C` 中，以下内容已被前置文档覆盖：

- workspace 前置依赖
- 单文件创建预览
- 基础 diff 返回
- 按钮 + 文本确认
- 单文件 apply 落盘

因此后续不需要再重复做一次同样的单文件链路。

### 2.3 Task C 剩余缺口

当前剩余的 Task C 核心缺口是：

- diff 还没有形成正式前端渲染与状态模型
- apply 成功 / 失败后的前端状态更新还没有正式设计
- command 执行结果虽然已有工具输出，但还未正式成为消息流中的一等信息
- 当前链路偏“能力存在”，不够“产品化”

### 2.4 Task D 缺口

Task D 当前仍缺：

- preview 结果正式进入消息流
- preview 面板不再只是占位容器
- self-repair 没有正式状态机
- self-repair 没有明确上限与过程可观察性

### 2.5 当前前端能力落后点判断

基于当前代码实现，可以判断前端大概率落后于后端基础能力，主要体现在：

- diff 仍缺少正式消息卡片与确认状态模型
- apply 结果同步链路不完整
- preview 面板虽然存在，但仍偏占位态
- runtime / command / repair 过程缺少统一展示策略

所以本文必须明确把前端补齐作为核心任务，而不是只补后端。

---

## 3. 目标总流程

### 3.1 生成代码改动预览

runtime 根据用户请求生成一个或多个 `PendingChange`，并返回结构化 diff 预览。

### 3.2 前端展示 diff 与待确认状态

前端把 diff 展示为正式消息卡片，并标记状态：

- `preview`
- `awaiting_confirmation`

### 3.3 用户确认后正式 apply

用户通过以下任一方式确认：

- 消息卡片按钮
- 文本指令

后端根据 `change_id` 执行 apply。

### 3.4 返回落盘结果

apply 后，消息状态与结果必须同步：

- 成功则标记为 `applied`
- 失败则标记为 `rejected` 或 `failed`

### 3.5 命令执行结果进入消息流

代码改动后运行测试或命令时：

- command 的 stdout / stderr / exit code 不再只是工具返回文本
- 而要成为消息流中的正式可展示内容

### 3.6 preview 结果进入消息流

preview 结果不再停留在前端静态面板，而要有正式数据来源：

- preview URL
- preview 状态
- 与当前消息或会话的关联

### 3.7 有限 self-repair 闭环

当命令失败后，系统可以在受控范围内执行：

- 分析失败
- 生成修改
- 再次预览
- 再次确认或自动重试受控步骤
- 重新执行命令

但必须：

- 有明确最大次数
- 全过程可观察

---

## 4. 后端总方案

### 4.1 `PendingChange` 生命周期收口

需要把当前 `PendingChange` 收口为正式生命周期：

- `preview`
- `awaiting_confirmation`
- `applied`
- `rejected`
- `failed`

当前如果 `PendingChange` 只有部分状态，需要补齐状态语义或等价状态映射。

### 4.2 diff 消息结构与返回契约

后端需要定义正式 diff 返回结构，至少包含：

- `change_id`
- `file_path`
- `operation`
- `unified_diff`
- `status`
- `created_at`

这样前端才能稳定渲染 diff 卡片，而不是从自由文本里反解析。

### 4.3 apply 确认链路

apply 需要正式化：

- 前端按钮确认请求
- 文本确认请求
- 当前会话中待确认变更的定位规则
- apply 成功 / 失败响应结构

### 4.4 命令执行结果结构化返回

`RunCommandTool` 目前已有结构化字符串输出，但还需要进一步进入正式消息结构。

建议后端在 runtime / ws 层补一个统一 command result 结构，至少包含：

- `command`
- `cwd`
- `stdout`
- `stderr`
- `exit_code`
- `success`
- `timed_out`

### 4.5 preview 结果结构化返回

preview 需要正式结构，而不是前端本地拼状态。

建议至少包含：

- `preview_id`
- `workspace_id`
- `preview_url`
- `status`
- `source_message_id`
- `created_at`

### 4.6 self-repair 状态机与重试上限

需要定义一个最小状态机，至少包含：

- `IDLE`
- `ANALYZING_FAILURE`
- `GENERATING_FIX`
- `AWAITING_CONFIRMATION`
- `APPLYING_FIX`
- `RERUNNING_COMMAND`
- `FINISHED`
- `ERROR`

同时定义：

- `MAX_REPAIR_RETRY`

必须保证：

- 超过上限后停止
- 停止原因明确可见

### 4.7 runtime / ws 事件链路调整

后端需要把以下内容正式纳入 runtime / ws 链路：

- diff preview 事件或消息
- apply result 事件或消息
- command result 事件或消息
- preview result 事件或消息
- self-repair 状态变化

---

## 5. 前端总方案

### 5.1 diff 消息卡片与展示模型

前端应新增正式 diff message 模型，而不是只把 diff 当普通文本。

最小卡片内容：

- 文件名
- 操作类型
- diff 内容
- 当前状态

### 5.2 待确认状态展示

diff 卡片需要明确显示：

- 待确认
- 已应用
- 已拒绝
- 应用失败

不允许用户看不出当前状态。

### 5.3 确认按钮与文本确认兜底

前端 diff 卡片应至少提供：

- `确认写入`
- 可选：`拒绝`

同时继续保留文本输入兜底：

- `确认应用`
- `apply`

### 5.4 apply 成功/失败状态更新

前端在收到 apply 结果后必须：

- 更新原 diff 卡片状态
- 展示最终成功或失败消息
- 避免重复确认同一 change

### 5.5 preview 面板正式接线

前端 `PreviewPanel` 需要从正式后端数据驱动：

- 不再只依赖本地构造的临时 `PreviewState`
- 接收 preview result 并展示 URL 或状态

### 5.6 命令结果展示

前端需要为 command result 提供最小渲染方式：

- 命令摘要
- 是否成功
- 可展开查看 stdout / stderr

### 5.7 self-repair 过程展示与最小可观察性

前端不需要复杂时间线，但至少要能让用户知道：

- 当前是否在修复
- 已尝试第几次
- 成功还是失败
- 为什么停止

---

## 6. 子任务拆分

### 6.1 Task C-3：前端 diff 展示与确认闭环

负责：

- diff 卡片
- 待确认状态
- 确认按钮
- 文本确认兜底的前端配合

### 6.2 Task C-4：apply 后消息状态与结果同步

负责：

- apply 成功 / 失败协议
- 前端状态回写
- 避免重复确认

### 6.3 Task C-5：命令执行结果消息流收口

负责：

- command result 正式结构
- ws / 消息流接入
- 前端 command result 展示

### 6.4 Task D-1：preview 主链路接入

负责：

- preview result 结构
- preview 面板正式数据驱动
- preview 状态展示

### 6.5 Task D-2：有限 self-repair 闭环

负责：

- retry 上限
- repair 状态机
- repair 过程展示

### 6.6 子任务依赖关系

推荐顺序：

1. Task C-3
2. Task C-4
3. Task C-5
4. Task D-1
5. Task D-2

原因：

- 没有前端 diff 卡片，后续 apply / command / repair 链路都难以验收

---

## 7. 接口契约

### 7.1 diff 预览响应契约

建议结构：

- `type = "diff_preview"`
- `change_id`
- `file_path`
- `operation`
- `unified_diff`
- `status`

### 7.2 apply 确认请求契约

建议结构：

- `action = "confirm_apply"`
- `session_id`
- `change_id`

### 7.3 apply 结果响应契约

建议结构：

- `type = "apply_result"`
- `change_id`
- `status`
- `message`
- `file_path`

### 7.4 command result 契约

建议结构：

- `type = "command_result"`
- `command`
- `cwd`
- `stdout`
- `stderr`
- `exit_code`
- `success`
- `timed_out`

### 7.5 preview result 契约

建议结构：

- `type = "preview_result"`
- `preview_id`
- `preview_url`
- `status`
- `workspace_id`
- `message_id`

### 7.6 self-repair runtime event 契约

建议结构：

- `type = "repair_state"`
- `state`
- `attempt`
- `max_attempts`
- `message`

### 7.7 错误响应与状态枚举

需要统一枚举：

- diff 状态枚举
- apply 状态枚举
- preview 状态枚举
- repair 状态枚举

避免前后端各自定义一套名字。

---

## 8. 详细实现步骤

### 8.1 后端 diff / apply 主链路收口

- 补齐 `PendingChange` 生命周期
- 明确 diff preview 返回结构
- 明确 apply 结果结构

### 8.2 前端 diff 卡片接线

- 建立 diff 消息模型
- 渲染 diff 卡片
- 展示待确认状态
- 提供确认按钮

### 8.3 命令结果进入消息流

- 后端把 command result 正式输出
- 前端提供最小 command result 视图

### 8.4 preview 正式接线

- preview 结果进入消息流或正式状态
- `PreviewPanel` 用正式数据驱动

### 8.5 self-repair 状态机落地

- 实现最小 repair 状态机
- 限制最大重试次数
- 前端展示最小过程状态

### 8.6 联调与回归

- diff / apply 回归
- command result 回归
- preview 回归
- repair 回归

---

## 9. 严格测试方案

### 9.1 后端单元测试

至少覆盖：

- `PendingChange` 状态转换
- apply 成功 / 失败
- command result 结构输出
- preview result 结构输出
- repair 状态机转移

### 9.2 runtime / ws 集成测试

至少覆盖：

- diff preview 进入消息流
- apply result 进入消息流
- command result 进入消息流
- preview result 进入消息流
- repair state 进入消息流

### 9.3 前端组件测试

至少覆盖：

- diff 卡片渲染
- 确认按钮可点击
- preview 面板正式显示
- command result 组件渲染

### 9.4 前端状态管理测试

至少覆盖：

- diff 状态更新
- apply 结果同步
- preview 状态同步
- repair attempt 同步

### 9.5 diff 确认端到端测试

至少覆盖：

- 预览后未确认不落盘
- 按钮确认后落盘
- 文本确认后落盘

### 9.6 preview 端到端测试

至少覆盖：

- preview result 到前端面板的完整链路

### 9.7 self-repair 端到端测试

至少覆盖：

- 失败 -> 修复 -> 重试
- 达到上限后停止

### 9.8 回归测试矩阵

必须回归：

- session / workspace 主链路
- 单文件 HelloWorld 流程
- 写文件 / apply / diff 现有测试
- runtime / ws 主消息流

---

## 10. 验收条件

### 10.1 diff 可展示且可确认

- 前端能正式展示 diff
- 用户能确认写入

### 10.2 未确认前不落盘

- preview 状态下真实文件不能提前写入

### 10.3 确认后状态与结果一致

- apply 成功后状态正确
- apply 失败后状态正确

### 10.4 命令结果可追踪

- 用户能看到命令是否成功以及主要输出

### 10.5 preview 可展示

- preview 有正式数据来源
- 前端面板能展示 preview

### 10.6 self-repair 有明确上限与可观察过程

- 用户能看到修复尝试过程
- 超过上限会停止

---

## 11. 风险与回滚

### 11.1 前端落后导致的联调风险

- 后端已能返回结构，但前端不能稳定消费

### 11.2 协议不一致风险

- 前后端状态枚举不一致
- `change_id` / `preview_id` / `message_id` 关联混乱

### 11.3 状态同步风险

- apply 成功但前端仍显示待确认
- repair 已停止但前端仍显示处理中

### 11.4 回滚策略

- preview / apply / repair 分开 feature flag 控制
- 如 preview 或 repair 不稳定，可回退到 diff + 手动确认最小链路
- command result 可临时降级为文本消息，但不能丢失执行结论

---

## 12. 与原 Task C / Task D 的关系

本文完成后：

- 原 Task C 剩余部分将基本被本文覆盖
- 原 Task D 的首版收口也由本文承接

后续若还保留 Task C / D，只需要继续扩展：

- 更通用的多文件操作
- 更复杂的 preview 类型
- 更复杂的 repair 策略

不需要再重复做当前这条首版主链路。

