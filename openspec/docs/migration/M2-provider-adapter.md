# M2 - Provider Contract And LLMAdapter

> 本文档是 `02-implementation-guide.md` 中 `M2：Provider 契约升级与 LLMAdapter 落地` 的执行清单。
>
> 本文档只约束 M2，不覆盖 M3 及后续里程碑。

---

## 1. 目标

M2 的唯一目标是：

- 让 AgentHub Provider 能承接完整 `messages` 历史
- 为 copied runtime 提供稳定的 LLM 适配入口
- 明确把 `generative_model.py` 从 LiteLLM 直连语义推进到 AgentHub Provider 适配语义

M2 完成后，仓库应满足：

- Provider 层具备面向 runtime 的完整 messages 接口
- runtime 侧存在明确的 `LLMAdapter`
- `quantlitellm.py` / `get_model_info.py` 虽可暂时保留，但不再是未来正式路线
- 不接入 WebSocket 主链路
- 不替换 `FixedAgentResponder`

---

## 2. 输入前提

执行 M2 前，以下前提必须成立：

- [02-implementation-guide.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 已确认里程碑顺序
- [M0-inventory.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M0-inventory.md) 已完成复制资产盘点
- [M1-import-closure.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M1-import-closure.md) 已完成 import 闭包修复

---

## 3. 本里程碑允许修改的范围

只允许修改以下范围：

- `backend/app/providers/base.py`
- `backend/app/providers/openai_compatible.py`
- `backend/app/runtime/generative_model.py`
- 新增：`backend/app/runtime/llm_adapter.py`
- 必要时补充或更新：
  - [M1-import-closure.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M1-import-closure.md)
  - 本文档

如果 Provider 适配需要最小补充类型定义或 schema，可在 `backend/app/providers/` 内做增量修改，但不得扩展到 WS、service、model 层。

允许的改动类型仅限：

- Provider 抽象接口扩展
- Provider 实现补齐完整 messages 调用能力
- runtime 到 Provider 的适配层新增
- `generative_model.py` 的最小裁剪和重定向
- 面向 M2 的测试补充

---

## 4. 本里程碑禁止修改的范围

M2 明确禁止：

- 修改 `backend/app/api/ws.py`
- 修改 `backend/app/services/fixed_agent_responder.py`
- 修改 `backend/app/services/agent_stream_service.py` 的主行为
- 修改 `backend/app/models/*`
- 直接接入 Runtime 到 WebSocket
- 实现事件桥接
- 引入 workspace guard / patch / diff / command guard 正式能力
- 在 M2 内启动 Tool 体系重建

---

## 5. 本里程碑必须处理的事项

### 5.1 Provider 契约升级

需要在 Provider 抽象层中显式区分：

- 兼容旧链路的简单接口
- 面向 runtime 的完整 messages 接口

建议形态：

- `chat()` / `stream_chat()`
- `chat_with_messages()` / `stream_chat_with_messages()`

要求：

- 不破坏当前已有简单链路
- 新接口必须能接收完整 `messages` 历史
- 接口命名和语义要稳定，供后续 M3/M5 继续使用

### 5.2 Provider 实现补齐

需要让当前实际 Provider 实现具备：

- 接收完整 `messages`
- 非流式文本返回
- 流式 delta 返回
- 错误可向上层稳定暴露

要求：

- 不再依赖“把多轮历史拼成一个 `user_message`”的临时路径
- 保持对现有调用方的兼容

### 5.3 新增 `LLMAdapter`

需要新增：

- `backend/app/runtime/llm_adapter.py`

职责：

- 对 runtime 暴露统一的生成接口
- 内部调用 AgentHub Provider，而不是 LiteLLM
- 作为后续 M3 中 `ReactAgent` 替换模型调用的唯一入口

建议最小能力：

- `async_generate_with_history()`
- 非流式生成
- 流式生成
- 最小 usage / model / finish_reason 返回结构

### 5.4 `generative_model.py` 收口

M2 中需要开始收口 copied `generative_model.py` 的未来方向。

允许保留的内容：

- `Message`
- `TokenUsage`
- `ResponseStats`

需要明确旁路或弱化的内容：

- `quantlitellm.py` 导入链
- `get_model_info.py` 导入链
- image generation 分支
- 任何暗示“LiteLLM 仍是正式方案”的表达

要求：

- 可以保留过渡兼容代码
- 但必须让后续调用方向清晰落到 `LLMAdapter`

### 5.5 过渡依赖状态更新

M2 完成后，需要明确：

- `quantlitellm.py` 仍只是过渡 stub，或已完全不再被主路线依赖
- `get_model_info.py` 仍只是过渡 stub，或已完全不再被主路线依赖

这项状态必须回写到迁移记录中。

---

## 6. 建议执行顺序

1. 读取 `M1-import-closure.md`
2. 检查当前 `BaseProvider` / 实现 Provider 的现状
3. 设计并补齐完整 messages 接口
4. 新增 `llm_adapter.py`
5. 让 `generative_model.py` 开始对齐新的调用方向
6. 运行 Provider / Adapter 级测试
7. 回写 M2 结果到迁移记录

---

## 7. 验收标准

M2 完成时，至少应满足：

| 验收项 | 要求 |
|---|---|
| Provider 新接口存在 | 存在完整 `messages` 历史输入接口 |
| Provider 实现可用 | 实现类可处理完整 messages 输入 |
| `LLMAdapter` 存在 | runtime 侧新增统一 LLM 适配入口 |
| copied runtime 有新方向 | `generative_model.py` 不再只代表 LiteLLM 直连路线 |
| 旧链路未被破坏 | 现有简单 provider 调用仍可保留 |
| 未越界到 M3/M5 | 未接入 WS，未替换 responder |

---

## 8. 建议测试

至少应补充或执行以下测试：

- `tests/providers/test_provider_messages.py`
- `tests/runtime/test_llm_adapter.py`

建议验证点：

- Provider 接收到完整 `messages`
- 非流式调用返回文本
- 流式调用返回 delta
- `LLMAdapter.async_generate_with_history()` 在多轮历史下可工作
- 旧简单接口未被破坏

---

## 9. M2 执行记录

> 执行时间：2026-05-28
> 执行方式：TDD（先写失败测试，再做最小实现）

### 9.1 修改文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `backend/app/providers/base.py` | 修改 | 新增 `ProviderMessage`、`LLMUsage`、`ProviderMessagesInput`、`ProviderMessagesOutput` dataclass；`BaseProvider` 新增 `chat_with_messages()` / `stream_chat_with_messages()` 抽象方法 |
| `backend/app/providers/openai_compatible.py` | 修改 | `QwenProvider` 实现 `chat_with_messages()` / `stream_chat_with_messages()`；转发完整 messages 到上游 API；支持从响应提取 usage |
| `backend/app/runtime/llm_adapter.py` | 新增 | 新文件：`LLMAdapter` 类，包装 `BaseProvider`，暴露 `async_generate_with_history()` 和 `async_stream_generate_with_history()`，返回 `ResponseStats` |
| `backend/app/runtime/__init__.py` | 修改 | 新增 `LLMAdapter` 到导出列表 |
| `backend/app/runtime/generative_model.py` | 修改 | 文件头注释更新，明确 LLMAdapter 为正式路线；`async_generate_with_history` 添加 M2 note |
| `tests/providers/test_provider_messages.py` | 新增 | M2 Provider messages 完整测试（21 个测试用例） |
| `tests/providers/__init__.py` | 新增 | provider tests 包初始化文件 |
| `tests/runtime/test_llm_adapter.py` | 新增 | M2 LLMAdapter 完整测试（22 个测试用例） |

### 9.2 新增/修改测试清单

| 测试文件 | 测试数量 | 覆盖内容 |
|---|---|---|
| `tests/providers/test_provider_messages.py` | 21 | `ProviderMessage`、`ProviderMessagesInput`、`ProviderMessagesOutput` dataclass 验证；`BaseProvider` 新接口抽象契约；`QwenProvider` messages 实现；向后兼容验证 |
| `tests/runtime/test_llm_adapter.py` | 22 | `LLMAdapter` 模块可导入；接口签名；非流式/流式生成；Provider 错误传播；不依赖 quantlitellm 验证 |

### 9.3 Provider 新接口说明

#### 简单接口（向后兼容）

```python
async def chat(self, input: ProviderInput) -> ProviderOutput
async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]
```

- `ProviderInput`: `system_prompt: str`, `user_message: str`, `model: str`
- `ProviderOutput`: `text: str`
- 用途：兼容当前 WS/Responder 链路

#### 完整 messages 接口（M2 新增）

```python
async def chat_with_messages(self, input: ProviderMessagesInput) -> ProviderMessagesOutput
async def stream_chat_with_messages(self, input: ProviderMessagesInput) -> AsyncIterator[ProviderStreamEvent]
```

- `ProviderMessagesInput`: `messages: list[ProviderMessage]`, `model: str`
- `ProviderMessage`: `role: str`, `content: str`
- `ProviderMessagesOutput`: `text: str`, `usage: LLMUsage | None`
- `LLMUsage`: `prompt_tokens: int`, `completion_tokens: int`, `total_tokens: int`
- 用途：支持 Runtime 完整多轮历史

### 9.4 `LLMAdapter` 对外接口说明

```python
class LLMAdapter:
    def __init__(self, provider: BaseProvider, default_temperature: float = 0.7)

    async def async_generate_with_history(
        self,
        messages_history: list,   # runtime.memory.Message 对象列表
        model: str,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> ResponseStats  # 含 response, usage, model, finish_reason

    async def async_stream_generate_with_history(
        self,
        messages_history: list,
        model: str,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]  # yield text delta
```

- 不依赖 quantlitellm
- 调用 `BaseProvider.chat_with_messages()` / `stream_chat_with_messages()`
- 返回 `runtime.generative_model.ResponseStats`，与 `react_agent.py` 现有接口兼容

### 9.5 测试执行结果

```
tests/providers/test_provider_messages.py  — 21 passed
tests/runtime/test_llm_adapter.py         — 22 passed
tests/runtime/test_import_inventory.py   — 13 passed  (原有)
tests/test_provider.py                   — 22 passed  (原有)

总计：78 passed, 0 failed
```

### 9.6 仍未解决的问题

| 问题 | 说明 | 留至里程碑 |
|---|---|---|
| `generative_model.Message` 与 `memory.Message` 同名并存 | 两个类字段不同：前者有 `image_url`，后者没有。M2 中 `LLMAdapter` 用 `memory.Message` 避免冲突 | M3 |
| `quantlitellm.py` / `get_model_info.py` 仍存在 | M2 中状态明确为过渡 stub。`LLMAdapter` 不依赖它们。`GenerativeModel` 内部方法仍引用（需 M3 切断） | M3 |
| `token_counter` 方法仍依赖 `quantlitellm` | `generative_model.py` 的 `token_counter` 等方法仍调用 `quantlitellm` | M3 |
| Provider 层 usage 返回 | 上游 DashScope API 并非所有模型都返回 usage，`LLMAdapter` 对 None usage 做了降级处理 | M3 验证 |

### 9.7 M2 与文档的偏差说明

M2-provider-adapter.md 假设 QwenProvider 只支持简单接口，但 QwenProvider 实际上已有完整的 `chat()` / `stream_chat()` 实现。M2 以最小方式添加新接口到现有实现，使代码与文档目标保持一致。

### 9.8 禁止修改边界的确认

| 禁止项 | 状态 |
|---|---|
| 修改 `ws.py` | 未修改 |
| 修改 `fixed_agent_responder.py` | 未修改 |
| 修改 `agent_stream_service.py` 主行为 | 未修改 |
| 修改 `backend/app/models/*` | 未修改 |
| 接入 WebSocket 主链路 | 未接入 |
| 实现 Runtime 事件桥接 | 未实现 |
| 新增 workspace / patch / diff / command guard | 未实现 |

---

## 10. 输出要求

执行 M2 的 AI 或工程实现，完成后必须输出：

1. 本次修改的文件清单 — 见 9.1 节
2. Provider 新增/修改接口说明 — 见 9.3 节
3. `LLMAdapter` 对外接口说明 — 见 9.4 节
4. 测试或 smoke check 结果 — 见 9.5 节
5. 仍未解决的问题清单 — 见 9.6 节
6. 明确哪些问题留给 M3 — 见 9.6 节及第 12 节

**本节已于 2026-05-28 完成上述全部输出。**

---

## 11. M3 交接边界

M2 结束后，以下问题应明确留给 M3，而不是在 M2 提前实现：

- 用 `LLMAdapter` 替换 `ReactAgent` 中的实际模型调用路径
- Runtime 事件模型收口
- ReAct 主循环最小可运行闭环
- 工具调用的实际运行链验证
- `GenerativeModel` 中 `async_generate_with_history` 去除 `quantlitellm` 引用
- `token_counter` / `token_counter_with_history` 方法的迁移或废弃

---

## 12. 一句话约束

M2 的本质不是"把 runtime 跑起来"，而是：

**先把 AgentHub 的 LLM 边界做对，让 copied runtime 后续能建立在 Provider 契约之上，而不是继续挂在 LiteLLM 兼容桩上。**
