# Quantalogic 迁移方案总览

> 本文档记录从 quantalogic 参考库向 AgentHub 的逐步迁移方案，覆盖 **Phase 2（Runtime 层）** 和 **Phase 3（Code Agent 能力）**。

## 决策记录

| # | 决策点 | 选择 | 理由 |
|---|--------|------|------|
| 1 | 迁移范围 | P2-P3（不含 P4 Artifact） | Agent Runtime + Code Agent 能力优先，P4 留待后续 |
| 2 | 执行路线 | **React（XML Tool Call）** | 多用户平台安全优先，工具白名单机制。XML 格式比 JSON 更易于 LLM 生成和解析 |
| 3 | LLM Provider | **适配现有 QwenProvider** | 不替换已有 Provider，保留认证/超时/错误处理积累 |
| 4 | 事件模型 | **双层架构**（传输层 + 业务层） | `ws.py` 协议稳定不变，内部 Agent 可使用丰富的业务层事件 |
| 5 | 代码放置 | **`agents/runtime/` 分层** | 与 Phase5 RuntimeFactory / Phase6 Orchestrator 命名体系一致 |
| 6 | Tool 绑定 | **独立 ToolContext 对象** | 与 quantalogic_flow context 机制一致，Phase6 迁移成本最低 |

## 文档目录

```
openspec/docs/migration/
├── README.md                              ← 本文档
├── 01-architecture.md                     ← 整体架构设计
├── 02-p2-runtime-layer.md               ← Phase2：Runtime 层迁移
├── 03-p3-code-agent.md                  ← Phase3：Code Agent 能力
├── 04-integration.md                     ← 与现有系统对接
└── 05-roadmap-and-progress.md           ← 后续路线图 + 迁移进度追踪
```

## 迁移目标（里程碑）

| 里程碑 | 完成条件 | 价值 |
|--------|----------|------|
| **M1: Agent 可运行** | QwenProvider 适配 + ws.py 接入，ReAct 循环能跑、能流式输出到前端 | 系统跑起 Agent 的最小可行版本 |
| **M2: Code Agent 完整** | M1 + FileTool + DiffTool + Workspace 隔离，Agent 能读写文件、diff、隔离执行 | 完整的代码操作能力 |
| **M3: Phase2 验收** | M2 + 事件系统完善 + 会话管理，所有 spec 验收标准满足 | Phase2 正式完成 |

> **关键结论**：完成"ws.py 双层事件接入"后，系统就可以真正跑起 Agent。之后的 FileTool / DiffTool / Workspace 隔离都是能力增强，不是"能不能跑"的前提条件。

## 迁移原则

1. **不破坏现有协议**：`ws.py` 的 `message_start/delta/end` 协议保持不变
2. **不替换已有 Provider**：`QwenProvider` 的认证、超时、重试逻辑保留
3. **逐步替换**：每次只替换一个组件，替换后验证后再进行下一步
4. **向后兼容**：Session / Message / Project 数据模型保持兼容
5. **与 Phase5-6 对齐**：目录结构和命名与后续 RuntimeFactory / Orchestrator 体系一致
