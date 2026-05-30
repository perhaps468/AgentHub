# 01 - 迁移兼容性与复制边界

> 本文档只解决一件事：**基于当前仓库真实代码，明确从 quantalogic 迁移到 AgentHub 的复制边界、目标文件清单和分类依据。**
>
> 本文档不负责逐步改造顺序、测试编排和里程碑推进；这些由 `02-implementation-guide.md` 负责。

---

## 1. 文档定位

这次迁移不是在 AgentHub 内从零重写一套 Runtime，而是：

- 优先复用 quantalogic 中已经存在且有迁移价值的 ReAct Runtime 资产
- 先把高价值资产完整复制进 AgentHub
- 再在 AgentHub 内逐步做接口适配、安全收口和链路接入

本文档的作用是给后续 AI / 工程实现一个清晰、稳定、可执行的复制清单，避免在复制阶段：

- 误用错误的源路径
- 漏掉运行时依赖闭包
- 把“复制阶段”和“改造阶段”混在一起

---

## 2. 当前仓库真实边界

### 2.1 源项目真实高价值代码位置

本次迁移应以 **`quantalogic/quantalogic_react/quantalogic/`** 为主源，而不是文档中常见的旧写法 `quantalogic/...`。

原因：

- 当前仓库真实存在、可追踪、可复制的 ReAct Runtime 实现位于：
  - `quantalogic_react/quantalogic/agent.py`
  - `quantalogic_react/quantalogic/generative_model.py`
  - `quantalogic_react/quantalogic/memory.py`
  - `quantalogic_react/quantalogic/tool_manager.py`
  - `quantalogic_react/quantalogic/xml_parser.py`
  - `quantalogic_react/quantalogic/xml_tool_parser.py`
  - `quantalogic_react/quantalogic/prompts/*`
  - `quantalogic_react/quantalogic/tools/*`

- 文档中常写的 `quantalogic/agent.py`、`quantalogic/tools/...`、`quantalogic/prompts/...` 在当前仓库中并不是本次迁移应依赖的主实现路径。

### 2.2 AgentHub 当前必须保留的基础设施

迁移不是替换 AgentHub，而是把 quantalogic Runtime 挂接到 AgentHub 既有边界上。

必须保留的边界包括：

- Provider 抽象层
  - `backend/app/providers/base.py`
  - `backend/app/providers/openai_compatible.py`
- Message 持久化模型
  - `backend/app/models/message.py`
- Session / 用户隔离
  - `session_id`
  - `owner_id / user_id`
- WebSocket 协议与前端消费契约
  - `backend/app/api/ws.py`
  - 事件：`message_start / message_delta / message_end / message_error`

### 2.3 AgentHub 当前已有的相关旧链路

在接入新 Runtime 前，必须认清 AgentHub 当前状态：

- 当前 WebSocket 主链路仍由 `FixedAgentResponder` 驱动
- `backend/app/api/ws.py` 已经承载了消息落库、并发保护、事件发送等逻辑
- 仓库中还存在一份旧的 `backend/app/services/agent_stream_service.py`

其中 `agent_stream_service.py` 当前不是可直接复用资产，原因包括：

- 它依赖的消息字段与现有 `Message` 模型不一致
- 它代表的是 AgentHub 既往试验性流式链路，而不是当前主链路

因此：

- **本次迁移不得把 `agent_stream_service.py` 当成既有可信中间层来叠加设计**
- 后续实施文档必须明确它是“废弃参考实现”还是“待删除旧链路”

---

## 3. 复制阶段总原则

### 3.1 复制优先于重写

只要某文件满足以下任一条件，就应进入复制范围：

- 逻辑主体可直接复用
- 经过少量接口适配即可复用
- 即便当前还未接线，但后续高概率会成为 Runtime 主体依赖

### 3.2 复制时只做最小改动

复制阶段允许的改动仅限：

- import 路径调整
- 包结构调整
- 目标目录调整
- 删除明显错误的本地相对路径引用

复制阶段**不应**做：

- Runtime 行为重写
- Provider 语义重构
- 安全模型定稿
- WebSocket 链路替换

### 3.3 运行时依赖必须按闭包复制

不能只复制 `agent.py` 这类入口文件，必须同步评估：

- 模板依赖
- utils 依赖
- Tool 抽象依赖
- 包级导出依赖
- 外部包依赖

任何一个被列入复制范围的文件，都必须同时标明：

- 它的直接依赖
- 这些依赖是“继续复制”还是“在 AgentHub 内重建”

---

## 4. 文件分类规则

### 4.1 A 类：直接复制

判断标准：

- 文件主体相对独立
- 与 AgentHub 现有 Message / Provider / WS 边界耦合低
- 只需 import 或目录调整即可落库

### 4.2 B 类：复制后少量适配

判断标准：

- 主体算法或运行时结构有明确复用价值
- 但需要适配 AgentHub 的：
  - Provider 接口
  - 消息模型
  - WebSocket 事件协议
  - workspace / sandbox 边界

### 4.3 C 类：仅参考，不复制

判断标准：

- 实现语义与 AgentHub 当前目标不一致
- 实现依赖外部运行环境或 SDK，复制收益低
- 安全模型与 AgentHub 目标相冲突

---

## 5. 推荐复制总清单

说明：

- “源路径”全部以 `quantalogic/quantalogic_react/quantalogic/` 为准
- A/B 类属于首批允许复制资产
- “后续动作”只描述复制后需关注的方向，不在本阶段实现

### 5.1 Runtime 核心

| 源路径 | 建议目标路径 | 分类 | 复制理由 | 后续动作 |
|---|---|---:|---|---|
| `quantalogic_react/quantalogic/agent.py` | `backend/app/runtime/react_agent.py` | B | ReAct 主循环、观察/执行闭环、事件发射、memory compact 入口价值高 | 替换模型调用、裁剪 chat/多模态/非必须分支、统一事件语义 |
| `quantalogic_react/quantalogic/memory.py` | `backend/app/runtime/memory.py` | A | `AgentMemory` / `VariableMemory` 相对独立 | 最小 import 调整 |
| `quantalogic_react/quantalogic/generative_model.py` | `backend/app/runtime/generative_model.py` | B | `Message` / `TokenUsage` / `ResponseStats` 语义可复用 | 去除 LiteLLM 直连，改为 AgentHub Provider 适配层 |
| `quantalogic_react/quantalogic/tool_manager.py` | `backend/app/runtime/tool_manager.py` | B | 工具注册、参数转换、markdown 描述能力可复用 | 修正 Tool 抽象来源和参数 schema |
| `quantalogic_react/quantalogic/xml_parser.py` | `backend/app/runtime/xml_parser.py` | A | 容错 XML 解析器独立性高 | 最小 import 调整 |
| `quantalogic_react/quantalogic/xml_tool_parser.py` | `backend/app/runtime/xml_tool_parser.py` | A | 工具调用 XML 解析器可直接复用 | 最小 import 调整 |
| `quantalogic_react/quantalogic/event_emitter.py` | `backend/app/runtime/event_emitter.py` | C | 当前实现内含线程 + 后台 loop 语义，不适合直接落入 FastAPI/asyncio 主链路 | 只参考事件语义，不直接复制实现 |

### 5.2 Prompt 与模板系统

| 源路径 | 建议目标路径 | 分类 | 复制理由 | 后续动作 |
|---|---|---:|---|---|
| `quantalogic_react/quantalogic/prompts.py` | `backend/app/runtime/prompts.py` | B | Prompt 组装入口可复用 | 调整模板名与裁剪非必要 persona |
| `quantalogic_react/quantalogic/prompts/*.j2` | `backend/app/runtime/prompts/` | A | 模板是 Runtime 行为的重要组成部分，应整组复制 | 后续按 AgentHub 语境裁剪 |

复制时至少应包括：

- `system_prompt.j2`
- `task_prompt.j2`
- `tools_prompt.j2`
- `variables_prompt.j2`
- `task_summary_prompt.j2`
- `memory_compaction_prompt.j2`
- `observation_response_format.j2`
- `repeated_tool_call_error.j2`
- `chat_system_prompt.j2`

### 5.3 Tool 抽象与首批工具

| 源路径 | 建议目标路径 | 分类 | 复制理由 | 后续动作 |
|---|---|---:|---|---|
| `quantalogic_react/quantalogic/tools/tool.py` | `backend/app/runtime/tools/tool.py` | C | 当前文件只是对 `quantalogic_toolbox.tool` 的 re-export，不是完整抽象实现 | 在 AgentHub 内重建 Tool / ToolArgument 抽象 |
| `quantalogic_react/quantalogic/tools/read_file_tool.py` | `backend/app/runtime/tools/read_file_tool.py` | B | 文件读取能力可复用 | 接入 workspace guard，去掉 HTTP 读取能力或单独拆分 |
| `quantalogic_react/quantalogic/tools/list_directory_tool.py` | `backend/app/runtime/tools/list_directory_tool.py` | B | 目录遍历与分页逻辑可复用 | 接入 workspace guard |
| `quantalogic_react/quantalogic/tools/replace_in_file_tool.py` | `backend/app/runtime/tools/replace_in_file_tool.py` | B | SEARCH/REPLACE 语义有迁移价值 | 改成仅对 workspace 内文件生效，并纳入 patch 流程 |
| `quantalogic_react/quantalogic/tools/unified_diff_tool.py` | `backend/app/runtime/tools/unified_diff_tool.py` | B | patch/diff 结构可参考 | 改成 AgentHub 受控 patch/apply 语义 |
| `quantalogic_react/quantalogic/tools/task_complete_tool.py` | `backend/app/runtime/tools/task_complete_tool.py` | A | 任务完成语义简单稳定 | 最小 import 调整 |
| `quantalogic_react/quantalogic/tools/write_file_tool.py` | `backend/app/runtime/tools/write_file_tool.py` | C | 当前实现是直接写文件，不符合 AgentHub 目标安全模型 | 只参考参数设计，后续重写 |
| `quantalogic_react/quantalogic/tools/execute_bash_command_tool.py` | `backend/app/runtime/tools/run_command_tool.py` | C | 当前实现强依赖 `/tmp`、shell 行为和弱安全校验，不适合直接迁移 | 后续按 AgentHub sandbox 模型重写 |
| `quantalogic_react/quantalogic/tools/grep_app_tool.py` | `backend/app/runtime/tools/grep_tool.py` | C | 这是 grep.app 远程搜索，不是本地仓库 grep，语义不匹配 | 后续重写为本地 workspace 搜索工具 |

### 5.4 需要同步评估的依赖文件

以下不是“主功能文件”，但如果复制 Runtime 主体，必须同步处理：

| 源路径 | 处理策略 | 原因 |
|---|---|---|
| `quantalogic_react/quantalogic/utils/get_environment.py` | B：可复制后裁剪 | `agent.py` 依赖环境提示构造 |
| `quantalogic_react/quantalogic/utils/ask_user_validation.py` | C：仅参考 | AgentHub 当前没有同语义的人机确认链路 |
| `quantalogic_react/quantalogic/utils/__init__.py` | B：按 import 形态决定 | 若继续保留 `from ...utils import ...` 这类包级导入，则需同步复制；若在 M1 改成显式子模块导入，则可不保留原结构 |
| `quantalogic_react/quantalogic/utils/read_file.py` | B：可复制后收口 | `read_file_tool.py` 依赖 |
| `quantalogic_react/quantalogic/utils/read_http_text_content.py` | C：仅参考 | 默认不应给 Runtime 加开放网络读取能力 |
| `quantalogic_react/quantalogic/version.py` | B：可复制后简化或在 M1 去依赖 | `prompts.py` 通过 `get_version()` 注入版本信息；若不复制，需同步裁剪 prompt 组装逻辑 |
| `quantalogic_react/quantalogic/get_model_info.py` 及相关 model info 文件 | C：仅参考 | 这些服务于 LiteLLM / 模型元信息，不应原样迁入 |
| `quantalogic_react/quantalogic/quantlitellm.py` | C：仅参考 | `generative_model.py` 的直连模型依赖，后续应由 AgentHub Provider/LLMAdapter 替换 |

### 5.5 外部包依赖不是复制文件，但必须显式记录

以下依赖在本次语境里属于“运行环境前提”，不是“需要继续复制的源码文件”，但文档和实施阶段都必须显式记账：

| 依赖 | 当前来源 | 处理策略 |
|---|---|---|
| `jinja2` | `prompts.py`、模板渲染 | 作为 Runtime 模板依赖保留 |
| `pydantic` | `agent.py`、`generative_model.py`、工具抽象 | 视 AgentHub 当前版本兼容性保留或薄封装 |
| `loguru` | 多个 Runtime 文件 | 可保留，也可在实施阶段统一替换为 AgentHub 日志接口 |
| `openai` | `generative_model.py` | 不应继续作为 Runtime 直连入口；若 Provider 层已封装，可从 Runtime 侧去依赖 |

这里的判断原则是：

- “源码文件依赖闭包”必须保证 import 不断裂
- “第三方包依赖”必须保证运行环境和改造方案里有明确落点
- 不允许既不复制源码依赖，也不在实施文档中写清楚替代路径

---

## 6. 明确不复制的内容

以下内容建议归为 C 类：

| 内容 | 原因 |
|---|---|
| LiteLLM 直连实现与 `quantlitellm` 相关链路 | AgentHub 已有 Provider 层，应复用接口而不是复用 SDK 耦合 |
| `event_emitter.py` 中线程 + 后台 event loop 实现 | 与 AgentHub 当前 FastAPI / asyncio 主运行模型不匹配 |
| `grep_app_tool.py` 的远程搜索行为 | 目标应是本地 workspace 搜索，而不是公网 API |
| `write_file_tool.py` 的直接写盘行为 | 与“先 patch / diff，再决定 apply”的安全目标冲突 |
| `execute_bash_command_tool.py` 的 `/tmp + shell` 执行模型 | 与 AgentHub 目标中的 sandbox / cwd / 命令白名单模型冲突 |
| `read_http_text_content.py` 的网络读取能力 | 与当前最小闭环“本地 workspace 观察”目标不一致 |
| chat mode、多模态 image_url、外部检索和非开发型工具 | 不属于本次最小迁移闭环 |

---

## 7. 复制后的目标目录布局

建议首批复制后的落盘目录如下：

```text
backend/app/runtime/
├── __init__.py
├── react_agent.py
├── memory.py
├── generative_model.py
├── tool_manager.py
├── xml_parser.py
├── xml_tool_parser.py
├── prompts.py
├── prompts/
│   ├── system_prompt.j2
│   ├── task_prompt.j2
│   ├── tools_prompt.j2
│   ├── variables_prompt.j2
│   ├── task_summary_prompt.j2
│   ├── memory_compaction_prompt.j2
│   ├── observation_response_format.j2
│   ├── repeated_tool_call_error.j2
│   └── ...
└── tools/
    ├── tool.py              # AgentHub 内自建抽象，不直接复制源文件
    ├── read_file_tool.py
    ├── list_directory_tool.py
    ├── replace_in_file_tool.py
    ├── unified_diff_tool.py
    └── task_complete_tool.py
```

说明：

- 允许存在“已复制但未接线”的文件
- 不允许因为当前尚未接入主链路就省略模板或核心依赖
- `glob_tool.py`、`grep_tool.py`、`run_command_tool.py` 不应以“直接复制文件”的方式落盘，它们应在后续实施阶段重写

---

## 8. 给 AI 的复制指令建议

若后续让 AI 按本文档执行复制阶段，应遵循以下顺序：

1. 创建 `backend/app/runtime/`、`backend/app/runtime/prompts/`、`backend/app/runtime/tools/`
2. 以 `quantalogic_react/quantalogic/` 为唯一主源路径
3. 先复制 A 类文件
4. 再复制 B 类文件
5. 同步处理这些文件的直接模板和 utils 依赖
6. 只做 import / 目录级最小调整
7. 输出一份“已复制文件清单 + 未复制但必须重写的清单”

禁止事项：

- 不要把 `quantalogic/...` 旧路径当成源路径
- 不要在复制阶段直接重写 Runtime 主行为
- 不要把不安全工具误标为“少量适配即可复用”

---

## 9. 复制完成后的验收标准

复制阶段的验收目标不是“功能已经跑通”，而是“迁移资产完整且边界正确”。

### 9.1 必须满足

- A/B 类文件都已落到目标目录
- Runtime 所需模板目录已完整复制
- 已明确列出未复制但必须重写的 C 类文件
- 已明确列出复制文件的依赖闭包处理策略

### 9.2 建议验证

- Runtime 目录可做一次 import smoke check
- 不存在因为缺模板或缺 utils 导致的结构性断裂
- 不存在错误源路径、错误文件名或错误分类

### 9.3 本阶段不要求

- 不要求 `ws.py` 已接入新 Runtime
- 不要求 Provider 已完成完整 history 适配
- 不要求写文件 / 命令执行工具已经可用
- 不要求端到端会话已经跑通

---

## 10. 与实施文档的关系

本文档产出的是：

- 一套基于真实仓库状态整理后的“可复制迁移资产集合”
- 一份明确的 A/B/C 分类边界
- 一份对 AgentHub 现有旧链路状态的前置说明

后续由 [02-implementation-guide.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 负责：

- 基于这些已复制文件逐步改造
- 处理 Provider / Message / WS / workspace / sandbox 适配
- 给出测试、回滚和里程碑推进方案
