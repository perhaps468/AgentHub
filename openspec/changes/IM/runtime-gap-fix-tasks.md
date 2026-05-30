# Task: Runtime Gap Fix Against 02-Implementation-Guide

## 0. 文档定位

- 本文档不是新 spec，只是对 [openspec/docs/migration/02-implementation-guide.md](/D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 的补缺任务收口。
- “总愿景”和“总实现方案”继续以 migration 文档和现有 roadmap/spec 为准，本文件只列修复任务，不重建方案。
- 本文档只覆盖当前审计确认的未完成项，不扩 scope。

## 1. 背景

当前 AgentHub 已落地：

- copied runtime 基础导入
- Provider messages 接口与 `LLMAdapter`
- `RuntimeAgentService` + `ws.py` feature flag 接入
- 只读工具、patch preview、run command 工具
- 对应的大量后端测试

但对照 [02-implementation-guide.md](/D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 的 M0-M7 验收标准，当前仍不能判定“全部完成”。

## 2. 本次确认的缺陷

### G1. 运行时主链路未注入完整历史

- `ws.py` 当前只把本轮 `content` 传给 `RuntimeAgentService`
- `RuntimeAgentService` 用新的空 `AgentMemory()` 启动 agent
- 主链路没有把 session 历史消息装入 runtime memory

影响：

- 不满足 M2/M3/M5 对“完整 messages 历史”“多轮上下文”的要求
- 当前 runtime 主链路只能算单轮任务执行，不是完整会话运行时

### G2. 当前不是文档要求的真实流式 delta

- `react_agent.py` 主任务路径仍使用非流式生成
- `EventBridge` 把 `task_think_end` 映射成 `message_delta`
- 当前 `message_delta` 更接近“整段生成完成后的伪增量”，不是 `model_delta`

影响：

- 不满足 M3/M5 对事件语义的要求
- 前端虽然能消费 `message_delta`，但不是基于真实 token/delta 的流式闭环

### G3. Patch preview 到 apply 的正式链路未打通

- `write_file` / `replace_in_file` 只返回 `PendingChange`
- `PendingChange.apply()` 仍是测试侧或临时集成能力
- 运行时主链路没有正式的 apply 确认路径
- `ask_for_user_validation` 目前默认拒绝

影响：

- M6 的“先生成变更，再展示 diff，再决定 apply”未完成
- 当前只有 preview，不具备正式受控写入闭环

### G4. 工具事件、diff、命令结果未统一进入消息链路

- `EventBridge` 当前忽略 `tool_started` / `tool_finished`
- patch preview、diff、run command 输出没有定义成正式 WS 事件或消息类型

影响：

- 不满足 M6/M7 对“diff 可见”“命令结果进入消息链路”的要求
- 前端只能看到最终文本，不能消费结构化开发过程

### G5. RunCommand 白名单过宽

- `CommandGuard` 允许 `python` / `node` / `npx` 等宽前缀
- 当前校验逻辑是简单 `startswith`

影响：

- 仍可执行解释器级任意脚本
- 不满足 M7 “白名单或受限命令集”的安全边界要求

### G6. 只读工具的 workspace_root 注入方式不对

- `read_file` / `list_directory` / `glob` / `grep` 把 `workspace_root` 暴露成模型必填参数
- 运行时没有把它作为内部注入参数统一收口

影响：

- 工具调用对模型输出格式敏感
- 不符合 M4 “统一 workspace guard、最小代码观察能力”的设计目标

## 3. 修复目标

- 让 runtime 主链路真正基于 session 历史运行
- 让 `message_delta` 来自真实模型流式增量
- 让 patch preview、diff、apply、run command 进入统一受控链路
- 收紧命令执行白名单
- 把 workspace root 改成运行时注入，而不是模型显式填写

## 4. 不做什么

- 不重写整套 migration 方案
- 不引入新的多 Agent 编排
- 不扩展到 artifact/deploy/workflow 等后续阶段
- 不做“能跑就行”的临时旁路

## 5. 任务拆分

### T1. 打通 session 历史注入

目标：

- `RuntimeAgentService` 在构建 agent 前，从当前 session 读取历史消息
- 转换为 runtime `Message` 列表并注入 `AgentMemory`
- 明确 human / agent / system 到 runtime role 的映射规则

修改范围：

- [backend/app/runtime/runtime_agent_service.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/runtime_agent_service.py)
- [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
- 必要时补充历史映射 helper

测试：

- 新增多轮历史用例
- 验证第二轮请求能看到第一轮 human/agent 内容
- 验证失败消息、空消息、非 text 消息的过滤策略

验收：

- runtime 主链路不再是空 memory 启动
- `LLMAdapter` 在主链路中收到完整历史

### T2. 把伪流式改成真实流式

目标：

- `react_agent.py` 在 runtime 主链路中走 `async_stream_generate_with_history()`
- 运行时内部发出 `model_delta`
- `EventBridge` 从 `model_delta` 映射到 `message_delta`

修改范围：

- [backend/app/runtime/react_agent.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/react_agent.py)
- [backend/app/runtime/event_bridge.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/event_bridge.py)
- [backend/app/runtime/llm_wrapper.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/llm_wrapper.py) 如需

测试：

- 增加真实流式事件顺序测试
- 验证多个 delta 顺序输出
- 验证 `message_end.final_content` 仍是最终答案而不是中间 XML

验收：

- `message_delta` 不再来自整段 `task_think_end`
- 主链路具备真实 delta 语义

### T3. 建立正式 apply 确认路径

目标：

- 设计 AgentHub 内的受控 apply 入口
- preview 先入消息链路，再由显式确认触发 apply
- 去掉“测试里直接调 `PendingChange.apply()` 就算产品闭环”的状态

修改范围：

- [backend/app/runtime/pending_change.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/pending_change.py)
- [backend/app/runtime/runtime_agent_service.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/runtime_agent_service.py)
- [backend/app/runtime/react_agent.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/react_agent.py)
- 必要时新增 `patch_store.py` / apply service

测试：

- preview -> confirm -> apply 成功路径
- preview -> reject 路径
- preview 后文件被外部修改的拒绝路径

验收：

- apply 不再只是测试辅助方法
- M6 正式具备受控写入闭环

### T4. 让工具事件与结构化结果进入消息链路

目标：

- 至少把 `tool_started` / `tool_finished` / patch preview / run command result 建模为可消费消息
- 前端能看到 diff 预览与命令结果，不只看到最后自然语言总结

修改范围：

- [backend/app/runtime/event_bridge.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/event_bridge.py)
- [backend/app/runtime/runtime_agent_service.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/runtime_agent_service.py)
- [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py) 如需新增类型
- 前端消费层，如已有对应渲染则复用

测试：

- patch preview 进入消息流
- run command 结构化结果进入消息流
- 失败路径也能看到结构化错误

验收：

- M6/M7 的开发过程信息可被前端消费

### T5. 收紧 RunCommand 安全边界

目标：

- 将解释器级宽前缀白名单收紧为受限命令集
- 禁止 `python -c`、`node -e`、`npx arbitrary` 等任意脚本执行
- 明确允许的测试/构建/诊断命令模式

修改范围：

- [backend/app/runtime/command_guard.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/command_guard.py)
- [backend/app/runtime/tools/run_command_tool.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tools/run_command_tool.py)
- [backend/tests/runtime/tools/test_run_command_tool.py](/D:/code/ZiJieAI/AgentHub/backend/tests/runtime/tools/test_run_command_tool.py)

测试：

- 放行：`pytest`、受限 `python -m pytest`、受限 `npm run test`
- 拒绝：`python -c`、`node -e`、`npx tsx script.ts`、任意解释器命令

验收：

- 命令白名单按能力收口，不再按解释器放行

### T6. 把 workspace_root 改成内部注入

目标：

- 文件类工具不再要求模型显式填写 `workspace_root`
- 运行时统一注入 workspace guard 所需根路径
- 工具 schema 对模型只暴露业务参数

修改范围：

- [backend/app/runtime/tools/read_file_tool.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tools/read_file_tool.py)
- [backend/app/runtime/tools/list_directory_tool.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tools/list_directory_tool.py)
- [backend/app/runtime/tools/glob_tool.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tools/glob_tool.py)
- [backend/app/runtime/tools/grep_tool.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tools/grep_tool.py)
- [backend/app/runtime/tools/tool.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tools/tool.py)
- [backend/app/runtime/tool_manager.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/tool_manager.py)

测试：

- 模型侧调用不再需要 `workspace_root`
- 工具仍然只能访问工作区内路径

验收：

- M4 的 workspace guard 通过内部注入统一生效

## 6. 推荐实施顺序

1. T1 历史注入
2. T2 真实流式
3. T6 workspace_root 内部注入
4. T5 run command 安全收紧
5. T3 apply 正式链路
6. T4 结构化事件进消息链路

## 7. 统一验证

至少执行：

- `python -m pytest tests/runtime tests/providers tests/api/test_ws_runtime_agent.py`
- 针对新增历史注入、真实流式、apply 路径、命令白名单的定向测试

额外要求：

- 在 `D:\code\ZiJieAI\AgentHub\backend` 目录下运行 pytest
- 不允许只依赖测试里直接调用 `PendingChange.apply()` 证明产品链路完成

