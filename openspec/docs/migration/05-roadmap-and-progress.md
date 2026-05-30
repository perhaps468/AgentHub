# 后续路线图 + 迁移进度追踪

## 5.1 P4：Artifact 体系

### 迁移内容

quantalogic 的 Artifact 能力：

- `artifact.py` — Artifact 数据模型（富文本、代码块、图片等）
- `artifact_manager.py` — Artifact 生命周期管理
- 前端 Artifact 渲染（CodeBlock / Markdown / Image）

### 与 AgentHub 的对应

AgentHub 原规划 P4 有类似的"产物"体系设计：

- Diff 状态（Phase3 已实现）
- Artifact 卡片（待迁移）
- Workspace 状态快照（待设计）

### 决策锚点（P4 时需重新评估）

| 决策点 | 当前状态 | P4 需评估 |
|--------|----------|-----------|
| Artifact 渲染层 | 前端已有基础渲染 | 是否复用 quantalogic 的 artifact_manager，还是自建？ |
| Artifact 存储 | 数据库 Message.payload | 是否需要独立的 Artifact 表？ |
| 流式 Artifact | 当前仅文本流式 | Artifact 的流式生成如何处理（类似 message_delta）？ |

### 预估工作量

- 复制 `quantalogic/artifact.py` → `agents/models/artifact.py`：1 天
- 实现 `ArtifactManager` → `agents/adapters/artifact_manager.py`：2 天
- 前端 Artifact 渲染适配：2-3 天

---

## 5.2 P5：自建 Agent → RuntimeFactory + Blueprint

### 迁移内容

quantalogic 的 `quantalogic_flow/` 模块：

- `runtime_factory.py` — 运行时工厂（创建不同类型的 Agent 实例）
- `blueprint.py` — Agent 蓝图（配置化定义 Agent 类型）
- `orchestrator.py` — 编排器（多 Agent 协作）

### 与 AgentHub 的对应

AgentHub 原规划 P5 有"自建 Agent"和"运行时工厂"设计：

- `agents/runtime/` 目录（本次 P2 已创建）
- `RuntimeFactory`（待实现）
- `Blueprint`（待设计）

### 决策锚点（P5 时需重新评估）

| 决策点 | 当前状态 | P5 需评估 |
|--------|----------|-----------|
| Agent 类型 | 单一 React Agent | 是否引入 Blueprint 配置多种 Agent 类型（PM / Coder / Reviewer）？ |
| RuntimeFactory | 手动创建 Agent | 是否抽象为工厂模式，支持按配置创建不同 Agent？ |
| Provider 抽象 | QwenAdapter 硬编码 | 是否通过 RuntimeFactory 注入不同 Provider？ |

### 预估工作量

- 实现 `RuntimeFactory` → `agents/runtime/factory.py`：2 天
- 实现 `Blueprint` → `agents/models/blueprint.py`：1-2 天
- 接入 `agents/registry.py`：1 天

---

## 5.3 P6：Orchestrator → quantalogic_flow WorkflowEngine

### 迁移内容

quantalogic 的工作流引擎：

- `workflow_engine.py` — 工作流执行引擎
- `sub_workflow_node.py` — 子工作流节点
- `context_bus.py` — 共享上下文总线

### 与 AgentHub 的对应

AgentHub 原规划 P6 有"多 Agent 协作"和"编排器"设计：

- `Orchestrator`（待实现）
- `SharedContextBus`（待设计）
- 多 Agent 流程（PM → Coder → Reviewer）

### 决策锚点（P6 时需重新评估）

| 决策点 | 当前状态 | P6 需评估 |
|--------|----------|-----------|
| 工作流描述格式 | 无 | 是否引入 YAML/JSON 工作流描述（quantalogic_flow 格式）？ |
| 子 Agent 调用 | 单 Agent | 是否支持 SubWorkflowNode（Agent 调用 Agent）？ |
| 上下文共享 | ToolContext | 是否抽象为 SharedContextBus（跨 Agent 共享状态）？ |

---

## 5.4 决策锚点汇总

以下决策在 P4-P6 阶段需要重新评估：

| 锚点 | 当前决策 | 可能在 P4-P6 调整的原因 |
|------|----------|----------------------|
| **目录结构** | `agents/runtime/` 分层 | P5 RuntimeFactory 可能引入 `agents/factories/`，P6 可能引入 `agents/orchestrator/` |
| **QwenProvider 适配** | QwenAdapter 封装 | P5 可能需要支持多 Provider 切换（不只是 Qwen） |
| **工具白名单** | 固定 ToolRegistry | P5 Blueprint 可能引入"按 Agent 类型配置不同工具集" |
| **EventAdapter** | 硬编码事件映射 | P6 多 Agent 场景可能需要跨 Agent 事件路由 |
| **Workspace 模型** | 单一 Workspace | P6 Orchestrator 场景可能需要共享 Workspace（多 Agent 操作同一项目） |

---

## 5.5 当前状态

### 已完成

- [x] M1-M3：迁移方案文档 + 关键架构决策
- [x] M4：只读工具收口（read_file / list_directory / glob / grep / task_complete）
- [x] M5：Runtime 主链路 + ws.py event bridge
- [x] M6：Workspace Patch Diff 受控写入闭环（pending_change + 3 个写工具 preview 模式）
- [x] M7：apply 链路 — PendingChange.PREVIEW 如何变为 APPLIED
- [x] P2/P3 验收收口 (2026-05-30)

### P2 / P3 Acceptance Closure (2026-05-30)

- P2 Runtime 事件现在运行在正式 runtime 路径上，并在最终 assistant 消息上持久化 replay 元数据。
- P3 apply 确认、command 执行、preview 和 repair 状态都通过正式 WS 事件发送。
- Legacy responder fallback 通过 feature flag 控制，不再是默认业务路径。

### 进行中

- [ ] (无)

### 待启动

- [ ] P4: Artifact 体系
- [ ] P5: 自建 Agent → RuntimeFactory + Blueprint

---

## 5.6 待完成任务清单（按优先级）

### P0（必须完成，系统可运行）

| # | 任务 | 依赖 | 预估工时 |
|---|------|------|----------|
| 1 | 创建 `agents/runtime/` 目录结构 | - | 0.5h |
| 2 | 实现 `agents/runtime/providers/qwen_adapter.py` | 目录结构 | 2h |
| 3 | 实现 `agents/models/tool_context.py` | - | 0.5h |
| 4 | 实现 `agents/models/events.py` | - | 1h |
| 5 | 复制 `agents/runtime/memory.py` | - | 1h |
| 6 | 复制 `agents/runtime/tool_manager.py` | - | 1h |
| 7 | 复制并适配 `agents/runtime/agent.py`（移除 litellm，注入 QwenAdapter） | qwen_adapter | 3h |
| 8 | 复制 `agents/runtime/templates/*.j2` | - | 1h |
| 9 | 实现 `agents/adapters/event_adapter.py` | events.py, ws.py | 2h |
| 10 | 实现 `agents/adapters/event_bridge.py` | event_adapter | 1h |
| 11 | 实现 `agents/adapters/runtime_stream_service.py` | agent.py, event_bridge | 3h |
| 12 | 扩展 ws.py `message_delta` 支持 `event_type` | - | 0.5h |
| 13 | 端到端测试（Agent ReAct 循环 + ws.py 流式输出） | 以上全部 | 4h |

### P1（Phase3，系统能力完整）

| # | 任务 | 依赖 | 预估工时 |
|---|------|------|----------|
| 14 | 实现 `agents/tools/file_tool.py`（Read/Write/List） | tool_context | 3h |
| 15 | 实现 `agents/tools/diff_tool.py` | - | 2h |
| 16 | 实现 `agents/models/workspace.py` | - | 1h |
| 17 | 实现 `agents/adapters/workspace_manager.py` | workspace.py | 2h |
| 18 | 实现 `agents/models/diff_state.py` | - | 1h |
| 19 | 实现 `agents/adapters/memory_persister.py` | - | 1h |
| 20 | 集成 ToolContext 到 Agent 工具执行链 | tool_context, file_tool | 2h |
| 21 | 端到端测试（文件读写 + diff） | 以上全部 | 3h |

**P0 合计：约 21 小时**（不含测试修复时间）
**P1 合计：约 16 小时**（不含测试修复时间）

---

## 5.7 风险点与依赖

### 高风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **QwenProvider 不支持历史消息** | Agent 无法多轮对话 | P0 阶段用 system_prompt 注入历史；P1 阶段扩展 QwenProvider 支持 messages 参数 |
| **ws.py 协议兼容性** | 前端需适配 event_type | event_type 为可选字段，向后兼容；前端忽略未知 event_type |
| **Token 计数不准确** | Memory compaction 可能误触发 | P0 阶段用简单字符估算；后续接入 tiktoken |

### 中风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **XML Tool Call 解析失败** | Agent 工具调用异常 | 复用 quantalogic 的 `ToleranceXMLParser`，已有容错机制 |
| **文件操作安全边界** | 路径穿越漏洞 | ToolContext 沙盒检查 + resolve 真实路径后二次验证 |
| **长对话 token 溢出** | Agent 无法处理长对话 | P0 阶段设 max_tokens_working_memory；P1 实现 MemoryPersister 分段持久化 |

### 低风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Jinja2 模板路径** | 模板找不到 | 使用 Path 计算模板目录，相对路径 |
| **依赖版本冲突** | quantalogic 依赖与 AgentHub 冲突 | P0 阶段只复制核心文件，不依赖 quantalogic 包；通过文件复制而非 pip 依赖 |
