# M0 - 复制资产整理与现状收口

> 本文档是 M0 里程碑的交付物，记录 `backend/app/runtime/` 目录下所有已复制 runtime 文件的清单、分类和状态。
>
> 本文档不涉及任何行为改造，所有文件均为 quantalogic -> AgentHub 迁移的"复制阶段"产物。
>
> **当前状态：** M0 进行中（已完成复制与清单整理）。M1 及后续里程碑尚未开始。

---

## 1. 已复制文件总清单

### 1.1 Runtime 核心

| 目标路径 | 源路径 | 分类 | 状态 | 说明 |
|---|---|---|---|---|
| `runtime/react_agent.py` | `quantalogic_react/quantalogic/agent.py` | B | 已复制，未接线 | ReAct 主循环，依赖 `GenerativeModel`；M1 修复 import，M3 形成闭环 |
| `runtime/memory.py` | `quantalogic_react/quantalogic/memory.py` | A | 已复制，未接线 | `AgentMemory` / `VariableMemory`；相对独立 |
| `runtime/generative_model.py` | `quantalogic_react/quantalogic/generative_model.py` | B | 已复制，未接线 | 依赖 `quantlitellm.py` stub；M2 由 `LLMAdapter` 替换 |
| `runtime/tool_manager.py` | `quantalogic_react/quantalogic/tool_manager.py` | B | 已复制，未接线 | 工具注册与参数转换；M4 重建 Tool 抽象 |
| `runtime/xml_parser.py` | `quantalogic_react/quantalogic/xml_parser.py` | A | 已复制，未接线 | 容错 XML 解析器；独立可用 |
| `runtime/xml_tool_parser.py` | `quantalogic_react/quantalogic/xml_tool_parser.py` | A | 已复制，未接线 | 工具调用 XML 解析器；独立可用 |
| `runtime/prompts.py` | `quantalogic_react/quantalogic/prompts.py` | B | 已复制，未接线 | Prompt 组装入口；依赖 Jinja2 模板 |
| `runtime/version.py` | `quantalogic_react/quantalogic/version.py` | B | 已复制，已收口 | 简化版，固定版本 `"0.1.0-agenthub-migrated"` |

### 1.2 Prompt 模板

| 目标路径 | 源路径 | 分类 | 状态 |
|---|---|---|---|
| `runtime/prompts/system_prompt.j2` | `quantalogic_react/quantalogic/prompts/system_prompt.j2` | A | 已复制 |
| `runtime/prompts/task_prompt.j2` | `quantalogic_react/quantalogic/prompts/task_prompt.j2` | A | 已复制 |
| `runtime/prompts/tools_prompt.j2` | `quantalogic_react/quantalogic/prompts/tools_prompt.j2` | A | 已复制 |
| `runtime/prompts/variables_prompt.j2` | `quantalogic_react/quantalogic/prompts/variables_prompt.j2` | A | 已复制 |
| `runtime/prompts/task_summary_prompt.j2` | `quantalogic_react/quantalogic/prompts/task_summary_prompt.j2` | A | 已复制 |
| `runtime/prompts/memory_compaction_prompt.j2` | `quantalogic_react/quantalogic/prompts/memory_compaction_prompt.j2` | A | 已复制 |
| `runtime/prompts/observation_response_format.j2` | `quantalogic_react/quantalogic/prompts/observation_response_format.j2` | A | 已复制 |
| `runtime/prompts/repeated_tool_call_error.j2` | `quantalogic_react/quantalogic/prompts/repeated_tool_call_error.j2` | A | 已复制 |
| `runtime/prompts/chat_system_prompt.j2` | `quantalogic_react/quantalogic/prompts/chat_system_prompt.j2` | A | 已复制 |
| `runtime/prompts/code_system_prompt.j2` | `quantalogic_react/quantalogic/prompts/code_system_prompt.j2` | A | 已复制 |
| `runtime/prompts/code_2_system_prompt.j2` | `quantalogic_react/quantalogic/prompts/code_2_system_prompt.j2` | A | 已复制 |
| `runtime/prompts/doc_system_prompt.j2` | `quantalogic_react/quantalogic/prompts/doc_system_prompt.j2` | A | 已复制 |
| `runtime/prompts/legal_system_prompt.j2` | `quantalogic_react/quantalogic/prompts/legal_system_prompt.j2` | A | 已复制 |
| `runtime/prompts/legal_2_system_prompt.j2` | `quantalogic_react/quantalogic/prompts/legal_2_system_prompt.j2` | A | 已复制 |

### 1.3 Tools

| 目标路径 | 源路径 | 分类 | 状态 | 说明 |
|---|---|---|---|---|
| `runtime/tools/tool.py` | — | C→自建 | 已重建 | 在 AgentHub 内自建 Tool / ToolArgument 抽象，非直接复制 |
| `runtime/tools/read_file_tool.py` | `quantalogic_react/quantalogic/tools/read_file_tool.py` | B | 已复制，未接线 | M4 需接入 workspace guard |
| `runtime/tools/list_directory_tool.py` | `quantalogic_react/quantalogic/tools/list_directory_tool.py` | B | 已复制，未接线 | M4 需接入 workspace guard |
| `runtime/tools/replace_in_file_tool.py` | `quantalogic_react/quantalogic/tools/replace_in_file_tool.py` | B | 已复制，未接线 | M6 改为受控 patch 语义 |
| `runtime/tools/unified_diff_tool.py` | `quantalogic_react/quantalogic/tools/unified_diff_tool.py` | B | 已复制，未接线 | M6 参考价值 |
| `runtime/tools/task_complete_tool.py` | `quantalogic_react/quantalogic/tools/task_complete_tool.py` | A | 已复制，未接线 | 语义简单稳定 |

### 1.4 Utils

| 目标路径 | 源路径 | 分类 | 状态 | 说明 |
|---|---|---|---|---|
| `runtime/utils/get_environment.py` | `quantalogic_react/quantalogic/utils/get_environment.py` | B | 已复制，未接线 | 环境提示构造 |
| `runtime/utils/read_file.py` | `quantalogic_react/quantalogic/utils/read_file.py` | B | 已复制，未接线 | read_file_tool 依赖 |
| `runtime/utils/__init__.py` | `quantalogic_react/quantalogic/utils/__init__.py` | B | 已复制，已收口 | 包级导出 |

---

## 2. 未接线文件清单

以下文件已复制到 `backend/app/runtime/`，但当前未接入任何主链路：

| 文件 | 未接线原因 | 计划接线里程碑 |
|---|---|---|
| `runtime/react_agent.py` | 依赖 `GenerativeModel` stub，无真实 LLM 调用 | M3 |
| `runtime/memory.py` | 被 `react_agent.py` 引用，但 agent 未接入 | M3 |
| `runtime/generative_model.py` | 依赖 `quantlitellm` stub | M2 |
| `runtime/tool_manager.py` | 被 `react_agent.py` 引用，但 agent 未接入 | M4 |
| `runtime/xml_parser.py` | 被 `react_agent.py` 引用，但 agent 未接入 | M3 |
| `runtime/xml_tool_parser.py` | 被 `react_agent.py` 引用，但 agent 未接入 | M3 |
| `runtime/prompts.py` | 被 `react_agent.py` 引用，但 agent 未接入 | M3 |
| `runtime/tools/*.py` | 所有 tools 均未注册到 ToolManager | M4 |
| `runtime/version.py` | 已被 `runtime/__init__.py` 引用 | 已收口（固定版本） |

**重要：** 未接线不等于"无效"或"待删除"。这些文件是后续里程碑的资产基础。

---

## 3. 过渡依赖（兼容桩）

以下文件是原 quantalogic 依赖链中的占位实现，在 M2 之前保证 import 不断裂：

### 3.1 `runtime/quantlitellm.py` — LiteLLM 直连桩

| 属性 | 说明 |
|---|---|
| 分类 | C → stub |
| 来源 | AgentHub 内自建，不复制自 quantalogic |
| 目的 | 保证 `generative_model.py` import 不断裂 |
| 后续 | M2 由 `LLMAdapter`（对接 AgentHub Provider）替换 |
| 当前行为 | `acompletion()` / `aimage_generation()` 均抛出 `NotImplementedError` |
| 依赖方 | `generative_model.py` |

### 3.2 `runtime/get_model_info.py` — 模型元信息桩

| 属性 | 说明 |
|---|---|
| 分类 | C → stub |
| 来源 | AgentHub 内自建，不复制自 quantalogic |
| 目的 | 保证 `generative_model.py` 的 `get_max_tokens` 等方法有返回值 |
| 后续 | M2 从 AgentHub Provider 层获取真实模型元信息 |
| 当前行为 | 所有函数返回固定默认值 |
| 依赖方 | `generative_model.py` |

---

## 4. 旧链路说明

### 4.1 当前主链路

```
backend/app/api/ws.py
  └── FixedAgentResponder
        (固定文本流式输出，非真实 LLM 调用)
```

- `FixedAgentResponder` 是当前 WebSocket 主链路的响应器
- 输出 deterministic 固定文本，带 `source = "fixed_responder"` 标记
- **后续里程碑（≥M5）由 `RuntimeAgentService` 替换此响应器**

### 4.2 旧试验性链路（废弃参考）

```
backend/app/services/agent_stream_service.py
```

**重要声明：**
- `agent_stream_service.py` **不是**当前主链路
- 它代表的是 AgentHub 既往试验性流式链路尝试
- 它使用的消息字段（`content_type`、`delivery_status`）与现有 `Message` 模型不一致
- **后续里程碑不得以此文件作为新 Runtime 的实施基座**
- 可参考其"句子聚合 / typing 生命周期"思路，但最终由 `runtime_agent_service.py`（M5 新增）取而代之
- 此文件状态：**保留参考，不继续扩展**

### 4.3 新 Runtime 目标落位

```
backend/app/runtime/react_agent.py   ← M3 形成闭环
backend/app/runtime/llm_adapter.py   ← M2 新增（对接 Provider）
backend/app/runtime/event_bridge.py  ← M5 新增
backend/app/runtime/runtime_agent_service.py ← M5 新增
backend/app/api/ws.py                 ← M5 接入新 Runtime
```

---

## 5. 迁移分类规则说明（来自 01-compatibility-analysis.md）

| 分类 | 含义 | 本次操作 |
|---|---|---|
| **A** | 直接复制，最小改动即可复用 | 已复制 |
| **B** | 复制后需少量适配 | 已复制，待后续里程碑适配 |
| **C** | 仅参考，不复制；或 C→自建 / C→stub | 已在 AgentHub 内自建等价实现 |
| **stub** | 占位实现，保证 import 不断裂 | 已创建，M2 替换 |

---

## 6. 外部包依赖记账

| 依赖 | 本次处理 | 后续 |
|---|---|---|
| `jinja2` | Runtime 模板渲染必需 | 保留，后续可替换为 AgentHub 模板接口 |
| `pydantic` | `agent.py`、`generative_model.py` 必需 | 保留 |
| `loguru` | 多文件使用 | 保留，后续可统一为 AgentHub 日志接口 |
| `openai` | `generative_model.py` 异常类型引用 | 保留，M2 旁路 |
| `litellm` | **不得作为 Runtime 直连入口** | M2 通过 AgentHub Provider 层替代 |

---

## 7. M0 验收状态

| 验收项 | 状态 | 说明 |
|---|---|---|
| A/B 类文件已落到目标目录 | ✅ | 35 个文件全部落位 |
| Runtime 模板目录已完整复制 | ✅ | 14 个 .j2 文件 |
| 未接线文件已明确标注 | ✅ | 见本文档第 2 节 |
| C 类文件已重标记（stub/自建） | ✅ | 见本文档第 3 节 |
| 旧链路状态已明确说明 | ✅ | 见本文档第 4 节 |
| 复制文件路径存在 | ✅ | 35/35 |
| 模板目录完整 | ✅ | 14/14 |

**M0 里程碑状态：已完成（复制资产整理与现状收口）**

---

## 8. M1 入口条件

M1（copied Runtime 基础可导入与依赖闭包修复）的前置条件：

- [x] M0 完成
- [x] M1 已完成

M1 已处理：
1. 修正 import 路径 — 所有路径正确，无需修改
2. 补齐模板加载路径 — 修复 `prompts.py` 中 `chat_prompt.j2` → `chat_system_prompt.j2`，修复 `system_prompt()` 对 `chat_system_prompt.j2` 的变量映射
3. 处理工具抽象依赖 — `tools/tool.py` 已在 AgentHub 内自建 stub
4. 去掉明显不适合 AgentHub 的入口依赖 — C 类边界已保持
5. import smoke check 通过

**M1 里程碑状态：已完成（copied Runtime 基础可导入与依赖闭包修复）**

---

*M1 完成时间：2026-05-28*

---

*本文档为 M0 里程碑交付物，生成时间：2026-05-28*
