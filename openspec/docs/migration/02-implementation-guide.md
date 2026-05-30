# 02 - 复制后逐步改造实施指南

> 本文档默认：`01-compatibility-analysis.md` 中的 A/B 类文件已经按真实源路径复制到 AgentHub。
>
> 本文档只解决一件事：**如何把这些已复制资产逐步改造成 AgentHub 可用的 Runtime，并在每一步给出验证与回滚边界。**

---

## 1. 文档定位

本次实施不是“把复制来的文件 import 进去就完事”，而是分阶段完成以下改造：

- 让 quantalogic Runtime 语义对接 AgentHub Provider
- 让 Runtime 语义对接 AgentHub Message / Session / WebSocket 协议
- 让文件/命令类能力进入受控的 workspace / patch / sandbox 边界

本文档不再讨论“哪些文件该不该复制”；那是文档 1 的职责。

---

## 2. 开始前必须确认的现状

### 2.1 当前 AgentHub 主链路

当前 AgentHub 主链路不是 Runtime，而是：

- `backend/app/api/ws.py` 接受用户消息、做鉴权和 session 校验
- 同文件内落库 human message
- 通过 `FixedAgentResponder` 产出 `message_start / delta / end / error`

因此，任何新 Runtime 接入都必须明确替换的是：

- `FixedAgentResponder`

而不是抽象地说“接入 WebSocket”。

### 2.2 当前仓库中的旧试验性链路

`backend/app/services/agent_stream_service.py` 当前不应作为新 Runtime 的实施基座，原因：

- 它不是当前主链路
- 它使用的消息字段与现有 `Message` 模型不一致
- 它更接近旧的 Provider 流式编排实验，而不是本次 Runtime 迁移落点

实施策略：

- **后续里程碑中不应继续扩展这份文件**
- 可以参考其“句子聚合 / typing 生命周期”思路
- 最终应由新的 `runtime_agent_service.py` 取代它在设计上的位置

### 2.3 当前 Provider 契约不足

当前 `BaseProvider` 只接受：

- `system_prompt`
- `user_message`
- `model`

这不足以承接 quantalogic Runtime，因为 quantalogic `GenerativeModel.async_generate_with_history()` 依赖完整 `messages_history`。

所以：

- Provider 契约升级是前置条件
- 不应继续依赖“把多轮历史拼成单个 prompt”这种临时方案

---

## 3. 改造总原则

### 3.1 先接口适配，再替换主链路

顺序必须是：

1. 先让 copied Runtime 可以在 AgentHub 内部独立运行
2. 再让它对接 Provider / Message
3. 最后替换 `ws.py` 中的主 responder

### 3.2 先只读闭环，再受控写入

不要一开始就接入文件写入和命令执行。

先完成：

- 完整 history 推理
- ReAct 主循环
- 只读工具
- WS 流式事件闭环

之后再进入：

- patch / diff
- apply
- run command

### 3.3 每个里程碑都要可验证、可回滚

每个阶段至少要有：

- 单元测试
- 最小集成验证
- 明确回滚点

### 3.4 默认使用 TDD

除复制阶段外，本实施文档默认按 TDD 推进：

- 先补或写失败测试
- 再做最小实现
- 再清理和收口

### 3.5 C 类文件仍需持续跟踪

`01-compatibility-analysis.md` 中的 C 类文件含义是“不要直接复制实现”，不是“后续不再关注”。

后续实施阶段仍需持续跟踪 C 类文件，但跟踪目标应明确限定为：

- 识别其原始能力语义
- 识别其风险边界与不适配 AgentHub 的原因
- 在 AgentHub 内以新的受控实现替代其能力

不允许在后续里程碑中把 C 类文件重新降格为“可直接复制”而绕过前述判断。

---

## 4. 实施范围重排

原始 7 个里程碑方向基本成立，但需要按当前仓库现状重排为：

```text
M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7
```

其中新增：

- `M0` 现状收口与复制资产整理

原因是当前仓库里存在：

- `FixedAgentResponder` 主链路
- `agent_stream_service.py` 旧链路
- copied Runtime 尚未落地

如果没有 `M0`，后续里程碑会在错误基座上推进。

---

## 5. 里程碑总览

- `M0` 复制资产整理与现状收口
- `M1` copied Runtime 基础可导入与依赖闭包修复
- `M2` Provider 契约升级与 `LLMAdapter` 落地
- `M3` ReAct Runtime 内核最小运行闭环
- `M4` Tool 抽象重建与只读工具接入
- `M5` Runtime -> Message / WebSocket 事件桥接
- `M6` Workspace / Patch / Diff 受控写入闭环
- `M7` RunCommand 受控执行与开发任务闭环

---

## 6. M0：复制资产整理与现状收口

### 6.1 目标

在开始任何行为改造前，先把仓库状态理顺：

- 明确 copied Runtime 文件清单
- 明确哪些文件只是参考，不进入主链路
- 明确当前 `FixedAgentResponder` 与旧 `agent_stream_service.py` 的关系

### 6.2 输入前提

- 文档 1 已修正并确认

### 6.3 修改文件

- `backend/app/runtime/` 下复制资产
- 迁移附录或清单文件
- 必要时补充说明到迁移文档

### 6.4 主要动作

1. 生成“已复制文件清单”
2. 标记“已复制但尚未接线”的 runtime 资产
3. 标记 `agent_stream_service.py` 为旧链路参考，不再继续叠加实现

### 6.5 测试

- `tests/runtime/test_import_inventory.py`

验证点：

- 复制文件路径存在
- 模板目录完整
- 旧链路状态说明存在

### 6.6 回滚点

- 仅回滚清单和说明文档
- 不删除已复制资产

---

## 7. M1：copied Runtime 基础可导入与依赖闭包修复

### 7.1 目标

让复制过来的 runtime / prompts / tools 至少具备：

- 路径正确
- import 可解析
- 必需依赖已补齐或已替换

### 7.2 输入前提

- M0 完成

### 7.3 修改文件

- `backend/app/runtime/react_agent.py`
- `backend/app/runtime/memory.py`
- `backend/app/runtime/generative_model.py`
- `backend/app/runtime/tool_manager.py`
- `backend/app/runtime/xml_parser.py`
- `backend/app/runtime/xml_tool_parser.py`
- `backend/app/runtime/prompts.py`
- `backend/app/runtime/prompts/*.j2`
- `backend/app/runtime/tools/*.py`
- 必需的 `runtime/utils/*` 或等价替代实现

### 7.4 主要动作

1. 修正 import 路径
2. 补齐模板加载路径
3. 处理工具抽象依赖
4. 去掉明显不适合 AgentHub 的入口依赖

特别注意：

- `tools/tool.py` 不能直接复制 re-export 版本，必须在 AgentHub 内重建最小 Tool 抽象
- `event_emitter.py` 不在本里程碑直接接入
- 若 copied `prompts.py` 继续调用 `version.get_version()`，则需同步处理 `version.py`；否则就在本里程碑直接裁剪掉该依赖
- 若 copied `agent.py` 继续使用 `from ...utils import ...` 包级导入，则需同步处理 `utils/__init__.py`；否则统一改为显式子模块导入
- `ask_user_validation.py` 不进入正式 Runtime 依赖闭包；相关调用要么在本里程碑旁路，要么替换成 AgentHub 明确的受控确认接口占位
- `read_http_text_content.py` 不应继续作为 `read_file_tool.py` 的隐式网络能力保留；本里程碑至少要把它标记为待移除依赖

### 7.5 测试

- `tests/runtime/test_imports_smoke.py`

验证点：

- `react_agent` 可导入
- `memory` 可导入
- `tool_manager` 可导入
- `xml_parser` / `xml_tool_parser` 可导入
- 模板渲染不因缺文件报错

### 7.6 验收标准

- Runtime 基础文件可在 AgentHub 项目内被 Python 导入
- 没有因缺模板、缺 utils、缺 Tool 抽象导致的结构性错误

### 7.7 回滚点

- 回滚 import / 依赖修复
- 保留 copied baseline

---

## 8. M2：Provider 契约升级与 LLMAdapter 落地

### 8.1 目标

让 AgentHub Provider 能承接完整 `messages` 历史，并为 Runtime 提供稳定入口。

### 8.2 输入前提

- M1 完成

### 8.3 修改文件

- `backend/app/providers/base.py`
- `backend/app/providers/openai_compatible.py`
- `backend/app/runtime/generative_model.py`
- `backend/app/runtime/llm_adapter.py`

### 8.4 主要动作

#### Step 1：升级 Provider 抽象

新增支持完整消息历史的接口，建议显式区分：

- 兼容旧链路的 `chat()` / `stream_chat()`
- 面向 Runtime 的 `chat_with_messages()` / `stream_chat_with_messages()`

#### Step 2：扩展 QwenProvider

让 provider 真正把完整 `messages` 发给上游，而不是继续退化为：

- 一个 `system_prompt`
- 一个 `user_message`

#### Step 3：实现 `LLMAdapter`

由 `LLMAdapter` 对外暴露 quantalogic 风格的：

- `async_generate_with_history()`

其内部调用 AgentHub Provider，而不是 LiteLLM。

#### Step 4：裁剪 copied `GenerativeModel`

保留：

- `Message`
- `TokenUsage`
- `ResponseStats`

移除或旁路：

- LiteLLM 直连
- `quantlitellm.py` 导入链
- `get_model_info.py` / model info 推断链
- 非本次必须的 image generation 分支

### 8.5 测试

- `tests/providers/test_provider_messages.py`
- `tests/runtime/test_llm_adapter.py`

验证点：

- provider 接收到完整 `messages`
- `chat_with_messages()` 正常返回文本
- `stream_chat_with_messages()` 正常返回 delta
- `LLMAdapter.async_generate_with_history()` 在多轮历史下可工作

### 8.6 验收标准

- AgentHub 内存在一个面向 Runtime 的完整 history LLM 接口
- 不再把“拼 system prompt”作为正式实现路线

### 8.7 回滚点

- 保留旧 provider 接口
- 新接口增量引入，不破坏现有简单链路

---

## 9. M3：ReAct Runtime 内核最小运行闭环

### 9.1 目标

让 copied `react_agent.py` 在不接 WebSocket 的情况下，先形成可独立运行的最小闭环。

### 9.2 输入前提

- M2 完成

### 9.3 修改文件

- `backend/app/runtime/react_agent.py`
- `backend/app/runtime/memory.py`
- `backend/app/runtime/tool_manager.py`
- `backend/app/runtime/xml_parser.py`
- `backend/app/runtime/xml_tool_parser.py`

### 9.4 主要动作

1. 用 `LLMAdapter` 替换原模型调用
2. 裁剪 chat mode、非必须 persona 和多模态逻辑
3. 保留 ReAct 主循环、工具调用、memory compact 主体
4. 明确内部事件模型

建议内部事件最小集合：

- `thinking_started`
- `model_delta`
- `tool_started`
- `tool_finished`
- `final_answer`
- `runtime_error`

### 9.5 测试

- `tests/runtime/test_react_agent_basic.py`
- `tests/runtime/test_react_agent_events.py`
- `tests/runtime/test_xml_parser.py`

验证点：

- 无工具场景可得到最终回答
- 工具调用场景可完成 observe / execute 闭环
- 工具不存在时错误可控
- 达到最大迭代数时可收口
- Runtime 能产出标准事件流

### 9.6 验收标准

- Runtime 可在不接 WS 的情况下独立运行
- Runtime 事件流稳定
- ReAct 闭环可用

### 9.7 回滚点

- 保留 copied baseline
- 每次只改一层：模型调用、事件语义、工具接入分开提交

---

## 10. M4：Tool 抽象重建与只读工具接入

### 10.1 目标

在不引入危险写入能力的前提下，让 Runtime 具备最小代码观察能力。

### 10.2 输入前提

- M3 完成

### 10.3 修改文件

- `backend/app/runtime/tool_manager.py`
- `backend/app/runtime/tools/tool.py`
- `backend/app/runtime/tools/read_file_tool.py`
- `backend/app/runtime/tools/list_directory_tool.py`
- 新增：`backend/app/runtime/tools/glob_tool.py`
- 新增：`backend/app/runtime/tools/grep_tool.py`
- 新增：`backend/app/runtime/workspace.py`

### 10.4 主要动作

#### Step 1：重建 Tool 抽象

在 AgentHub 内重建最小：

- `Tool`
- `ToolArgument`
- 参数 schema / 校验语义

#### Step 2：优先接只读工具

首批只接：

- `read_file`
- `list_directory`
- `glob`
- `grep`

说明：

- `glob` 和 `grep` 不来自直接复制文件，应在 AgentHub 内按 workspace 语义实现
- 不应继续使用 `grep_app_tool.py` 的公网 API 逻辑
- copied `read_file_tool.py` 应在本里程碑改造成“仅工作区本地文件读取”，并去掉对 `read_http_text_content.py` 的依赖

#### Step 3：统一 workspace guard

所有文件读取类工具都必须统一经过 `workspace_root` 约束。

### 10.5 测试

- `tests/runtime/test_tool_manager.py`
- `tests/runtime/tools/test_read_file_tool.py`
- `tests/runtime/tools/test_glob_tool.py`
- `tests/runtime/tools/test_grep_tool.py`
- `tests/runtime/tools/test_workspace_guard.py`

### 10.6 验收标准

- ToolManager 可驱动只读工具
- Runtime 具备最小代码观察能力
- 所有文件访问都经过 workspace guard

### 10.7 回滚点

- 工具逐个接入
- 写入类工具继续保持未接线

---

## 11. M5：Runtime -> Message / WebSocket 事件桥接

### 11.1 目标

用真实 Runtime 替换 `FixedAgentResponder`，但不破坏现有前端协议。

### 11.2 输入前提

- M3 完成
- M4 至少完成只读工具接入

### 11.3 修改文件

- 新增：`backend/app/runtime/event_bridge.py`
- 新增：`backend/app/runtime/runtime_agent_service.py`
- `backend/app/api/ws.py`
- 必要时：`backend/app/services/fixed_agent_responder.py`

### 11.4 主要动作

#### Step 1：定义 bridge 语义

把 Runtime 内部事件映射到现有 WS 协议：

- `model_delta` -> `message_delta`
- `final_answer` -> `message_end`
- `runtime_error` -> `message_error`

可选扩展：

- `thinking_started`
- `tool_started`
- `tool_finished`

#### Step 2：实现 `RuntimeAgentService`

职责：

- 消费 `ReactAgent` 事件流
- 创建 agent message
- 增量更新 message 内容
- 在完成或失败时落正确的 `status`

#### Step 3：在 `ws.py` 中引入 feature flag

不要直接删掉 `FixedAgentResponder`。

建议：

- 先保留旧 responder
- 用 feature flag 或配置开关切换到 `RuntimeAgentService`

#### Step 4：统一消息模型字段

必须以当前 `Message` 模型真实字段为准：

- `type`
- `status`
- `payload`
- `msg_metadata`

不要沿用旧 `agent_stream_service.py` 中的：

- `content_type`
- `delivery_status`

### 11.5 测试

- `tests/runtime/test_event_bridge.py`
- `tests/runtime/test_runtime_agent_service.py`
- `tests/api/test_ws_runtime_agent.py`

验证点：

- 事件顺序正确：`message_start -> delta* -> end`
- 异常时输出 `message_error`
- DB 中 agent message 内容逐步累积
- 失败时消息 `status` 正确更新

### 11.6 验收标准

- `ws.py` 可接入真实 Runtime
- 前端协议无需重写即可消费
- 主链路不再依赖假流式 responder

### 11.7 回滚点

- 通过 feature flag 切回 `FixedAgentResponder`

---

## 12. M6：Workspace / Patch / Diff 受控写入闭环

### 12.1 目标

让 Runtime 具备“先生成变更，再展示 diff，再决定 apply”的受控改写能力。

### 12.2 输入前提

- M4 完成
- M5 完成

### 12.3 修改文件

- `backend/app/runtime/tools/replace_in_file_tool.py`
- `backend/app/runtime/tools/unified_diff_tool.py`
- 新增：`backend/app/runtime/tools/write_file_tool.py`
- `backend/app/runtime/workspace.py`
- 可选新增：`backend/app/runtime/patch_store.py`

### 12.4 主要动作

1. 定义 `workspace_root`
2. 定义 patch / pending change 结构
3. 默认禁止直接覆盖正式文件
4. 生成 diff 并进入消息链路
5. 明确 apply 行为由受控路径触发

说明：

- `write_file_tool.py` 不应来自源文件直接复制，应按 AgentHub 安全模型重写

### 12.5 测试

- `tests/runtime/test_workspace.py`
- `tests/runtime/tools/test_replace_in_file_tool.py`
- `tests/runtime/tools/test_unified_diff_tool.py`
- `tests/runtime/test_patch_flow.py`

### 12.6 验收标准

- Agent 可生成结构化代码变更
- 用户可看到 diff
- 默认主链路不是直接覆写正式文件

### 12.7 回滚点

- 暂时关闭 apply
- 保留 patch only 模式

---

## 13. M7：RunCommand 受控执行与开发任务闭环

### 13.1 目标

让 Runtime 在受控边界内具备执行测试/构建命令的能力。

### 13.2 输入前提

- M6 完成

### 13.3 修改文件

- 新增：`backend/app/runtime/tools/run_command_tool.py`
- 新增：`backend/app/runtime/command_guard.py`
- `backend/app/runtime/react_agent.py`

### 13.4 主要动作

1. 定义命令执行边界
   - cwd 限制
   - timeout
   - stdout/stderr 捕获
   - exit code 结构化返回
2. 定义命令白名单或受限命令集
3. 接入 Runtime 工具链

说明：

- 不应直接复用 `execute_bash_command_tool.py`
- 当前源实现中的 `/tmp`、shell 直跑、弱黑名单模型都不适合作为正式方案

### 13.5 测试

- `tests/runtime/tools/test_run_command_tool.py`
- `tests/runtime/test_dev_task_loop.py`

### 13.6 验收标准

- Agent 能完成最小开发任务闭环
- 命令执行受控
- 文件变更、diff、命令执行能统一进入消息链路

### 13.7 回滚点

- 默认关闭高风险命令
- 命令执行能力可单独 feature flag 关闭

---

## 14. 测试矩阵

### 14.1 Provider 层

- 完整 messages 历史输入
- 非流式输出
- 流式 delta 输出
- 错误映射

### 14.2 Runtime 层

- 基础回答
- 多轮上下文
- 工具调用
- 最大迭代
- 解析错误
- 事件流输出

### 14.3 Message / WS 集成层

- `message_start`
- `message_delta`
- `message_end`
- `message_error`
- DB 状态同步

### 14.4 Tool / Workspace 层

- 文件读取
- 目录遍历
- glob
- grep
- patch
- diff
- apply
- workspace guard

### 14.5 命令执行层

- 正常命令返回 stdout/stderr/exit code
- timeout
- 非法 cwd 拒绝
- 非白名单命令拒绝

### 14.6 端到端闭环

- 用户消息进入
- Runtime 基于完整历史响应
- 工具调用
- patch / diff 展示
- 测试命令执行
- 最终结果返回

---

## 15. 当前未接线资产的记录规则

允许存在以下状态：

- 文件已复制
- import 已修正
- 当前里程碑尚未挂入主链路

但必须满足：

- 在里程碑记录中明确标注“已复制但未接线”
- 不得在清理过程中误删

---

## 16. 与复制文档的关系

本文档默认以下前提成立：

- 文档 1 已修正真实源路径
- 文档 1 已明确 A/B/C 分类
- 文档 1 已明确哪些工具不能直接复制

因此：

- 文档 1 决定“先复制哪些资产”
- 本文档决定“先改造哪些资产、以什么顺序改造”

前者负责资产入库，后者负责把这些资产逐步改造成 AgentHub 可用能力。
