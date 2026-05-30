# M1 - Copied Runtime Import Closure

> 本文档是 `02-implementation-guide.md` 中 `M1：copied Runtime 基础可导入与依赖闭包修复` 的执行清单。
>
> 本文档只约束 M1，不覆盖 M2 及后续里程碑。

---

## 1. 目标

M1 的唯一目标是：

- 让 `backend/app/runtime/` 下 copied runtime 基础模块可被正确导入
- 修复 import 路径、模板路径和最小依赖闭包
- 保持当前阶段仍然是“复制后结构收口”，不是“正式功能改造”

M1 完成后，仓库应满足：

- runtime 基础模块 import 不因路径或缺少本地依赖而断裂
- prompts 模板可被正确加载
- copied runtime 仍未接入 AgentHub 主链路
- Provider / WS / Tool 安全模型仍保持未改造状态

---

## 2. 输入前提

执行 M1 前，以下前提必须成立：

- [01-compatibility-analysis.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/01-compatibility-analysis.md) 已确认复制边界
- [02-implementation-guide.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 已确认里程碑顺序
- [M0-inventory.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M0-inventory.md) 已完成复制资产盘点

---

## 3. 本里程碑允许修改的范围

只允许修改以下范围：

- `backend/app/runtime/*.py`
- `backend/app/runtime/prompts/*.j2`
- `backend/app/runtime/tools/*.py`
- `backend/app/runtime/utils/*.py`
- 必要时补充或更新：
  - [M0-inventory.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M0-inventory.md)
  - 本文档

允许的改动类型仅限：

- import 路径修正
- 包级导出修正
- 模板加载路径修正
- 最小依赖闭包补齐
- 明确过渡依赖的注释和状态
- 为保证 import smoke check 通过而做的最小兼容处理

---

## 4. 本里程碑禁止修改的范围

M1 明确禁止：

- 修改 `backend/app/providers/*`
- 修改 `backend/app/api/ws.py`
- 修改 `backend/app/services/fixed_agent_responder.py`
- 修改 `backend/app/models/*`
- 接入或替换 WebSocket 主链路
- 升级 Provider 契约
- 实现 `LLMAdapter`
- 引入 workspace guard / patch / apply / command guard 正式能力
- 把 C 类文件重新恢复为正式 runtime 实现

---

## 5. 本里程碑必须处理的事项

### 5.1 import 闭包修复

需要逐项确认以下模块的导入链：

- `runtime/react_agent.py`
- `runtime/memory.py`
- `runtime/generative_model.py`
- `runtime/tool_manager.py`
- `runtime/xml_parser.py`
- `runtime/xml_tool_parser.py`
- `runtime/prompts.py`
- `runtime/tools/*.py`
- `runtime/utils/*.py`

要求：

- 不允许存在明显错误的包路径
- 不允许存在已经删除但仍被引用的模块
- 不允许因为包级导出不一致导致 import 断裂

### 5.2 模板加载路径修复

需要确认：

- `prompts.py` 的模板目录定位方式正确
- `react_agent.py` 的模板渲染路径正确
- prompts 目录下最小模板集合完整

### 5.3 过渡依赖状态明确

以下文件在 M1 中允许临时保留，但必须明确它们只是过渡依赖，不是正式迁移完成状态：

- `runtime/quantlitellm.py`
- `runtime/get_model_info.py`
- `runtime/version.py`（若继续保留）

要求：

- 文件注释或迁移清单中要明确说明用途
- 不得把这些文件表述为“AgentHub 已正式采用的新运行方案”

### 5.4 C 类边界继续保持

M1 中必须继续保持 01 文档定义的 C 类边界。

尤其不允许恢复或新增以下正式实现：

- `event_emitter.py`
- `utils/ask_user_validation.py`
- `utils/read_http_text_content.py`
- 任何直接代表 LiteLLM 正式接入的实现表述

---

## 6. 建议执行顺序

1. 读取 `M0-inventory.md`
2. 检查 `backend/app/runtime/` 当前导入链
3. 修复 `__init__.py`、包级导出和直接 import 问题
4. 修复模板加载路径
5. 明确过渡依赖状态
6. 运行 import smoke check
7. 回写 M1 结果到迁移记录

---

## 7. 验收标准

M1 完成时，至少应满足：

| 验收项 | 要求 |
|---|---|
| Runtime 基础模块可导入 | `react_agent`、`memory`、`tool_manager`、`xml_parser`、`xml_tool_parser` 可被导入 |
| Prompt 路径正确 | 模板加载不因路径错误失败 |
| 包结构闭合 | import 链不因已删除文件或错误导出断裂 |
| C 类边界未回退 | 未重新引入已移除的 C 类正式实现 |
| 过渡依赖已标注 | `quantlitellm.py`、`get_model_info.py` 的过渡状态已明确 |

---

## 7.1. 执行结果（M1 完成记录）

> 执行时间：2026-05-28

### 7.1.1 本次修改的文件

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `backend/app/runtime/prompts.py` | 模板路径修正 | `chat_prompt.j2` → `chat_system_prompt.j2`；修复 `system_prompt()` 对 `chat_system_prompt.j2` 的变量映射（`expertise`→`persona`，`tools`→`tools_prompt`） |

### 7.1.2 无需修改、确认通过的模块

以下文件经 import smoke check 验证通过，M1 阶段无需改动：

| 模块 | 状态 |
|---|---|
| `runtime/react_agent.py` | import 路径正确 |
| `runtime/memory.py` | import 路径正确 |
| `runtime/generative_model.py` | import 路径正确（依赖 `quantlitellm.py` stub） |
| `runtime/tool_manager.py` | import 路径正确 |
| `runtime/xml_parser.py` | import 路径正确 |
| `runtime/xml_tool_parser.py` | import 路径正确 |
| `runtime/version.py` | import 路径正确，固定版本 `"0.1.0-agenthub-migrated"` |
| `runtime/quantlitellm.py` | C 类 stub，状态明确 |
| `runtime/get_model_info.py` | C 类 stub，状态明确 |
| `runtime/tools/tool.py` | C→自建 stub，状态明确 |
| `runtime/tools/task_complete_tool.py` | import 正确 |
| `runtime/tools/list_directory_tool.py` | import 正确 |
| `runtime/tools/read_file_tool.py` | import 正确 |
| `runtime/tools/replace_in_file_tool.py` | import 正确 |
| `runtime/tools/unified_diff_tool.py` | import 正确 |
| `runtime/utils/get_environment.py` | import 正确 |
| `runtime/utils/read_file.py` | import 正确 |
| `runtime/__init__.py` | 包级导出正确 |
| `runtime/tools/__init__.py` | 包级导出正确 |
| `runtime/utils/__init__.py` | 包级导出正确 |
| 14 个 `.j2` 模板文件 | 全部存在且完整 |

### 7.1.3 import smoke check 结果

```
ALL CLEAN - no errors detected

测试覆盖：
- 17 个独立模块 import（含所有 tools 和 utils）
- react_agent / generative_model 导入
- runtime 包级 __init__ 导出
- tools 包级 __init__ 导出
- 8 种 agent_mode 模板渲染（react/chat/code/code_enhanced/legal/legal_enhanced/doc/default）
- Tool 实例化（TaskCompleteTool / ReadFileTool / ListDirectoryTool / ReplaceInFileTool / UnifiedDiffTool）
- ToolManager 工作链
- AgentMemory / VariableMemory 工作链
- ToleranceXMLParser 工作链
```

### 7.1.4 C 类边界确认

M1 执行后确认以下 C 类边界未回退：

- `event_emitter.py` 未接入 Runtime（`react_agent.py` 和 `generative_model.py` 各使用本地 `_NoopEventEmitter`）
- `ask_user_validation.py` 未被引用（`react_agent.py` 中使用 `_deny_user_validation` 本地兼容函数）
- `read_http_text_content.py` 未被引用
- LiteLLM 未作为 Runtime 直连入口

### 7.1.5 仍未解决的问题

以下问题在 M1 阶段未处理，留给后续里程碑：

| 问题 | 留至里程碑 |
|---|---|
| `memory.py` 和 `generative_model.py` 各定义同名 `Message` 类（字段不完全一致） | M2，由 `LLMAdapter` 层统一消息模型 |
| `generative_model.py` 依赖 `quantlitellm.py` stub，调用时抛出 `NotImplementedError` | M2，由 `LLMAdapter` 替换 |
| `token_counter` 等方法依赖 `quantlitellm` 粗糙字符估算 | M2 |
| `version.py` 含未使用的 `import importlib.metadata` | 无害，M1 最小改动原则不动 |
| `read_file_tool.py` 依赖 `utils/read_file.py`，无 workspace guard | M4 |

---

## 7.2. M2 执行结果（M2 解决 M1 遗留问题）

> 执行时间：2026-05-28（与 M1 同日完成）

### 7.2.1 M2 解决的 M1 遗留问题

| M1 遗留问题 | M2 解决方案 |
|---|---|
| `memory.py` 和 `generative_model.py` 同名 `Message` 类不一致 | M2 中 `LLMAdapter` 通过 `runtime.memory.Message` 路由到 `ProviderMessage`，避免直接依赖 `generative_model.Message` |
| `generative_model.py` 依赖 `quantlitellm` stub（`NotImplementedError`） | `LLMAdapter` 调用 AgentHub Provider 层，提供真实 LLM 路径 |
| `token_counter` 粗糙字符估算 | M2 中 `LLMAdapter` 从 Provider 响应提取真实 usage，不再依赖 `quantlitellm.token_counter` |

### 7.2.2 M2 未解决、继续留给 M3

| 问题 | 留至里程碑 |
|---|---|
| `generative_model.py` 中 `async_generate_with_history` 仍通过 `quantlitellm` stub | M3，`ReactAgent` 直接调用 `LLMAdapter` |
| `memory.py` 和 `generative_model.py` 同名 `Message` 类并存 | M3，Runtime 消息模型收口 |
| `token_counter` / `token_counter_with_history` 仍通过 `quantlitellm` | M3，废弃或迁移到 Provider usage 提取 |
| `get_model_info.py` stub | M3，由 Provider 层或配置提供 |

---

## 8. 输出要求

执行 M1 的 AI 或工程实现，完成后必须输出：

1. 本次修改的文件清单 — 见 7.1.1 节
2. import smoke check 结果 — 见 7.1.3 节
3. 仍未解决的问题清单 — 见 7.1.5 节
4. 明确哪些问题留给 M2 — 见 7.1.5 节及第 9 节

**本节已于 2026-05-28 完成上述全部输出。**

---

## 9. M2 交接边界

M1 结束后，以下问题应明确留给 M2，而不是在 M1 提前实现：

- Provider 契约升级
- `chat_with_messages()` / `stream_chat_with_messages()` 设计
- `LLMAdapter` 落地
- 去除 `quantlitellm` 真实运行语义
- 去除 `get_model_info` 真实模型推断语义

**M2 已于 2026-05-28 完成上述全部交接内容。** 详细执行结果见 7.2 节。

---

## 10. 一句话约束

M1 的本质不是“让 runtime 可用”，而是：

**让 copied runtime 的结构闭合、导入稳定、边界清晰，从而为 M2 的 Provider 改造提供可信基线。**
