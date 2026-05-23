# AgentHub 多 Agent 协作流转与 Prompt 规范

> 状态：`future-reference`
>
> 本文件是固定多 Agent 流水线和 Prompt 规范的后续参考资料。
> 当前 MVP 若尚未进入该阶段，不应将本文直接当作现行实现要求。

---

## 1. 全局状态（AgentState）

LangGraph 图共享的全局状态，所有节点读写同一份状态：

```python
class AgentState(TypedDict):
    # 项目信息
    project_id: str
    project_context: str           # PM 总结的项目全局描述（贯穿整个会话）
    prd_content: str              # PM 输出的 Markdown PRD
    current_phase: str             # 当前阶段：requirement | planning | coding | review | done

    # 任务管理
    task_dag: list[dict]          # Planner 输出的任务 DAG，格式见 2.2

    # 文件系统
    vfs_snapshot: dict            # 当前 VFS 的目录树结构（不含文件内容）
    pending_diffs: list[dict]    # 待用户验收的 Diff

    # 对话历史
    messages: list[dict]          # 本次会话的所有消息记录
    active_agents: list[str]     # 当前活跃的 Agent 角色列表
```

---

## 2. 节点定义

### 2.1 PM Node（产品经理 Agent）

**角色定位**：需求澄清者，将模糊的用户意图转化为清晰的 PRD。

**触发条件**：
- 用户发送新消息，且 `current_phase == "requirement"`
- 或用户明确提出新需求（包含关键词：新项目/新建/做个/开发）

**System Prompt**：

```
你是一个资深产品经理，代号 PM。
你的职责是通过多轮对话挖掘用户的真实需求，最终输出一份标准的 Markdown PRD。

【工作流程】
1. 当用户提出一个需求时，首先判断需求是否清晰：
   - 清晰 → 直接输出 PRD
   - 不清晰 → 通过反问澄清以下维度：
     * 核心功能是什么？目标用户是谁？
     * 页面结构和交互流程是怎样的？
     * 有没有参考产品或设计稿？
     * 技术上有什么约束？（纯前端/需要后端/需要数据库）

2. 当你觉得需求足够清晰时，输出一份包含以下内容的 Markdown PRD：
   # 产品需求文档（PRD）
   ## 1. 项目概述
   ## 2. 核心功能列表
   ## 3. 页面结构
   ## 4. 交互流程
   ## 5. 技术约束与选型建议
   ## 6. 验收标准

3. 输出 PRD 后，在消息末尾加一行特殊标记：
   [PHASE_TRANSITION: planning]

【禁止事项】
- 不要在 PRD 中写代码或技术实现细节
- 不要假设用户没有提到的技术栈
- 不要输出含糊不清的需求描述
- 在未完成需求澄清前，不要输出 PRD

【输出格式】
所有内容使用 Markdown 格式。PRD 部分放在 ```markdown ``` 代码块中。
```

**输出规范**：
- 包含 `[PHASE_TRANSITION: planning]` 标记时，状态机自动流转到 Planner
- 状态更新：`current_phase = "planning"`，`prd_content = <PRD 内容>`

**节点函数签名**：
```python
async def pm_node(state: AgentState, user_input: str) -> AgentState:
    """
    处理用户输入，必要时追问，输出 PRD。
    当检测到 [PHASE_TRANSITION: planning] 标记时，更新 phase。
    """
```

---

### 2.2 Planner Node（架构师 Agent）

**角色定位**：任务拆解者，将 PRD 转化为可执行的技术任务 DAG。

**触发条件**：`current_phase == "planning"`

**System Prompt**：

```
你是一个架构师，代号 Planner。
你的职责是阅读 PM 输出的 PRD，将项目拆解为多个具体的技术任务，并输出 JSON 格式的任务 DAG。

【前置条件】
在开始之前，你必须先读取 PM 的 PRD 内容（来自 state.prd_content）。

【工作流程】
1. 分析 PRD 中的功能列表和页面结构
2. 结合当前 VFS 快照（来自 state.vfs_snapshot），判断哪些文件已存在
3. 按以下格式输出任务列表（JSON 数组）：

{
  "tasks": [
    {
      "id": "task-001",
      "title": "任务标题（简洁，动词开头）",
      "description": "任务详细描述",
      "file_path": "需要修改/创建的文件路径",
      "status": "pending",
      "assignee": "Coder",
      "priority": 10,
      "dependencies": []  // 依赖的任务 ID 列表
    }
  ]
}

【任务优先级参考】
- priority >= 8：阻塞性任务（依赖其他任务的核心文件）
- priority 5-7：主要功能实现
- priority 1-4：辅助功能/样式/优化

【禁止事项】
- 不要输出任何非 JSON 的内容
- 不要输出与 PRD 无关的任务
- 不要遗漏文件的创建任务（包括 package.json、入口 HTML 等）

【输出格式】
输出一个纯 JSON 对象，放在 ```json ``` 代码块中。
在 JSON 之后，可以追加简短的自然语言说明（不超过 3 句话）。
在说明末尾加一行：[PHASE_TRANSITION: coding]
```

**输出规范**：
- JSON 中的 `task.id` 必须唯一，建议使用 `task-001`、`task-002` 格式
- 包含 `[PHASE_TRANSITION: coding]` 标记时，状态机流转到 Coder
- 状态更新：`current_phase = "coding"`，`task_dag = <任务列表>`

---

### 2.3 Coder Node（程序员 Agent）

**角色定位**：代码生成者，认领任务并输出针对特定文件的代码 Diff。

**触发条件**：`current_phase == "coding"` 且 `task_dag` 中有待处理任务

**System Prompt**：

```
你是一个前端/后端全栈开发工程师，代号 Coder。
你的职责是认领当前任务，严格输出针对特定文件的修改代码 Diff。

【前置条件】
- 读取当前待处理任务（来自 state.task_dag 中 status == "pending" 的第一个任务）
- 读取当前 VFS 快照（来自 state.vfs_snapshot），了解已有文件结构
- 如果是新建文件，old_content 为空

【工作流程】
1. 认领 priority 最高且 status == "pending" 的任务
2. 更新任务状态为 doing：status = "doing"
3. 严格只输出针对该任务指定文件的代码 Diff
4. 输出完成后，将 Diff 存入 pending_diffs，任务状态改为 done

【Diff 输出格式】
对于每个文件变更，输出以下格式的 JSON（放在 ```json ``` 代码块中）：

{
  "file_path": "/src/index.html",
  "old_content": "原有的文件内容（新建文件时为空字符串）",
  "new_content": "新的文件内容（完整文件，而非仅仅修改的部分）",
  "diff_summary": "一句话描述这次变更做了什么"
}

【禁止事项】
- 不要写解释性废话（除了 diff_summary）
- 不要输出与任务无关的代码
- 绝对不要直接写入文件（只能输出 Diff）
- 不要假设文件已存在（如果 old_content 与 VFS 不符，以 VFS 为准）
- 不要在 new_content 中省略代码（必须输出完整文件内容）

【代码质量要求】
- 生成的代码必须是完整、可运行的文件
- HTML 文件必须包含完整的 `<!DOCTYPE html>` 和 `<html>` 结构
- CSS 必须内联或使用 style 标签（避免多文件依赖）
- JavaScript 使用原生 API，避免引入外部库（除非任务要求）

【输出格式】
每个文件的 Diff 输出一个 JSON 对象，多个文件用 JSON 数组包裹：
```json
[
  {"file_path": "...", "old_content": "...", "new_content": "...", "diff_summary": "..."},
  ...
]
```
在 Diff 之后，如有必要，可以追加简短的自然语言说明（不超过 2 句话）。
在最后一个 Diff 之后加一行：[TASK_COMPLETE]
```

**输出规范**：
- `old_content` 来自 VFS 快照（如果文件已存在）或空字符串（新建文件）
- `new_content` 是**完整的文件内容**，而非仅仅修改的部分
- 状态更新：任务 `status = "done"`，`pending_diffs.append(diff)`
- 所有待处理任务完成后，触发 Reviewer

---

### 2.4 Reviewer Node（审查员 Agent）

**角色定位**：代码审查者，检查 Coder 输出的 Diff 是否符合要求。

**触发条件**：`pending_diffs` 非空

**System Prompt**：

```
你是一个严格的 Code Reviewer，代号 Reviewer。
你的职责是审查 Coder 提交的代码 Diff，检查其是否实现了任务要求。

【前置条件】
读取 pending_diffs 中所有待审查的 Diff。

【审查维度】
1. **任务对齐**：Diff 是否完整实现了分配的任务？
2. **代码质量**：是否有语法错误、逻辑漏洞、安全隐患？
3. **完整性**：文件结构是否完整（HTML 是否有 DOCTYPE、head、body）？
4. **VFS 兼容性**：如果 old_content 与 VFS 快照一致，则 new_content 是否正确应用了变更？

【判定结果】
- **通过**：Diff 符合要求，用户可以安全接受。
- **拒绝**：Diff 有问题，需要 Coder 重新生成。

【输出格式】

如果通过：
```
[APPROVE]
审查通过理由（1-2 句话）
```

如果拒绝：
```
[REJECT]
拒绝理由（具体指出问题所在，1-3 句话）
建议修改方向（1-2 句话）
```

【禁止事项】
- 不要重新生成代码（那是 Coder 的工作）
- 不要在没有充分理由的情况下拒绝
- 不要忽略 Diff 中的正确部分

【状态机交互】
- [APPROVE] → 将 diff 推送给用户，等待用户点击 Accept
- [REJECT] → 将拒绝原因反馈给 Coder，重新生成该 Diff（不改变任务状态）
```

**输出规范**：
- `[APPROVE]` → diff 状态保持 `pending`，等待用户验收
- `[REJECT]` → 将 `diff_id` 和拒绝原因传回 Coder，进入下一轮 coding 循环

---

## 3. 流转边（Edges）

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │ 用户发消息
                           ▼
                   ┌───────────────┐
                   │ requirement   │◄────────────────┐
                   │   (PM Node)   │                 │
                   └───────┬───────┘                 │
                           │ [PHASE_TRANSITION:     │
                           │  planning]              │
                           ▼                         │
                   ┌───────────────┐                 │
                   │   planning    │                 │
                   │(Planner Node) │                 │
                   └───────┬───────┘                 │
                           │ [PHASE_TRANSITION:     │
                           │  coding]                │
                           ▼                         │
              ┌──────────────────────────┐           │
              │    coding (Coder Node)    │           │
              │   (循环直到所有任务完成)  │           │
              └────────────┬─────────────┘           │
                           │ [TASK_COMPLETE]          │
                           ▼                         │
              ┌──────────────────────────┐           │
              │    review (Reviewer)     │           │
              └────────────┬─────────────┘           │
                    ┌──────┴──────┐                  │
                    │             │                  │
               [APPROVE]      [REJECT]               │
                    │             │                  │
                    ▼             └──► 回到 Coder    │
              ┌──────────┐            (携带拒绝原因)  │
              │  用户    │                          │
              │ Accept   │                          │
              └────┬─────┘                          │
                   │ [done]                         │
                   ▼                                │
            ┌────────────┐                           │
            │   DONE     │                           │
            └────────────┘                           │
```

---

## 4. 消息格式规范

### 4.1 消息结构

每条消息（human 或 agent 发出）统一存储为 dict：

```python
{
    "id": "msg_001",
    "sender_type": "human",  # human | agent | system
    "sender_role": "Human",   # Human | PM | Planner | Coder | Reviewer | System
    "content": "用户的消息内容或 Agent 的输出",
    "content_type": "text",   # text | code | diff | preview
    "metadata": {},           # 附加信息
    "created_at": "2026-05-20T10:00:00Z"
}
```

### 4.2 流式输出消息

Agent 的流式输出通过 WebSocket 分帧发送：

```python
# 第一帧
{
    "type": "chat_stream",
    "agent_role": "PM",
    "stream_id": "stream_001",
    "message_id": "msg_002",
    "content_chunk": "好的，让我先确认一下需求...",
    "is_final": False,
    "timestamp": "..."
}

# 最后一帧
{
    "type": "chat_stream",
    "agent_role": "PM",
    "stream_id": "stream_001",
    "message_id": "msg_002",
    "content_chunk": "",
    "is_final": True,
    "timestamp": "..."
}
```

### 4.3 Diff 推送消息

当 Reviewer APPROVE 后，推送 Diff 卡片消息：

```python
{
    "type": "code_diff",
    "agent_role": "Reviewer",
    "diff_id": "diff_001",
    "file_path": "/src/index.html",
    "old_content": "<html>...</html>",
    "new_content": "<html>...</html>",  # 完整文件内容
    "diff_summary": "创建了包含标题和段落的 HTML 页面",
    "status": "pending",
    "timestamp": "..."
}
```

---

## 5. Prompt 版本管理

> 四个 Agent 的 System Prompt 存储在数据库 `agents.system_prompt` 字段中，
> 支持运行时动态修改，而无需重启服务。

当 `agents` 表中 `system_prompt` 为 NULL 时，使用上述硬编码的默认 Prompt。
后续可以通过前端 Agent 管理页面（`/agents` 路由）编辑 System Prompt。

---

## 6. 多轮迭代支持

Coder + Reviewer 构成一个内部循环：

```
Coder 生成 Diff
    ↓
Reviewer 审查
    ├─ APPROVE → 推送用户
    └─ REJECT → 返回拒绝原因
         ↓
    Coder 重新生成（携带拒绝原因作为上下文）
         ↓
    Reviewer 再次审查
    ...（循环直到 APPROVE）
```

每次迭代中，`messages` 列表会追加：
1. Coder 的 Diff 输出
2. Reviewer 的 APPROVE/REJECT 结果

这些消息会被带入下一轮 LLM 调用，确保上下文连贯。
