# Task: 主 Agent 语义拆分并分发

## 0. 文档定位

- 本文档描述从“后端规则拆分 task”升级到“主 agent 语义拆分 task 并分发给子 agent”的改进任务。
- 本文档面向当前代码现状：
  - 已有 group session / primary agent / orchestration run / orchestration task
  - 已有主 agent 主持消息
  - 已有并行 task 执行链路
  - 当前 task 仍主要由 `backend/app/services/task_splitter.py` 的规则逻辑生成
- 本文档不要求本期同时完成：
  - DAG 调度
  - 自动重规划
  - 多轮博弈式 planner-reviewer 规划
  - 复杂能力图谱和动态负载均衡

## 1. 背景

当前系统已经能做到：

1. 用户在群聊中发送一个复合请求。
2. 主 agent 生成主持性计划消息。
3. 后端按规则拆出若干 task。
4. task 被分配给子 agent 并执行。

当前主要缺陷不是执行器，而是“规划权”没有真正交给主 agent：

- 用户说法稍微自然一点，规则拆分就可能误判任务数。
- 主 agent 的计划消息与真实 task 结构是两套来源，存在语义漂移风险。
- 分配逻辑目前更像后端轮询，不是主 agent 基于语义做的决策。
- 后续如果要做“为什么这样拆”“为什么给这个 agent”“是否需要串行依赖”，规则拆分会很快碰到天花板。

因此，这个任务的目标不是“继续增强正则”，而是把编排链路升级成：

1. 主 agent 先做语义规划。
2. 主 agent 输出结构化 plan。
3. 后端校验并落库。
4. 后端按 plan 分发给子 agent。
5. 主 agent 继续作为唯一主持人对用户汇报。

## 2. 目标

实现一条稳定的主链路：

1. 用户在 group session 提交复合请求。
2. 主 agent 输出一份结构化 plan，而不是只输出自然语言摘要。
3. plan 至少包含 `N` 个任务的标题、目标、分配对象、输入摘要、依赖关系。
4. 后端对 plan 做强校验、修复或降级。
5. 校验通过后创建 orchestration run / tasks。
6. 子 agent 按 plan 执行。
7. 主 agent 用自然语言向用户说明拆分结果和分配方案。

本期的关键成功标准：

- task 数量由主 agent 的语义规划决定，不再由规则拆分器主导。
- 主 agent 规划结果必须结构化，可校验，可落库，可回放。
- 当规划失败时，系统仍可安全降级，不让整条链路失效。

## 3. 非目标

- 本期不做通用 DAG 引擎。
- 本期不做 planner 自我反思和多次迭代优化。
- 本期不做完全自动的 agent 能力学习。
- 本期不做跨 run 的长期调度。
- 本期不把所有 UI 一次性重写成“任务操作台”。

## 4. 现状问题拆解

### 4.1 任务拆分来源不统一

- 主 agent 对用户说的是一套计划。
- 实际落库的 tasks 是另一套由规则生成的结构。
- 一旦两者不一致，用户看到的主持话术就不可信。

### 4.2 对自然语言鲁棒性不足

- 当前规则更适合“创建 A 并创建 B”。
- 对“先做 X，再顺手补一个 Y”“把后端接口和前端调用一起补掉”这类真实表达不稳。

### 4.3 agent 分配缺乏可解释性

- 目前分配更多是固定规则或轮询。
- 主 agent 没有显式输出“为什么把这个任务给这个 agent”。

### 4.4 缺少 planner 失败兜底机制

- 如果未来直接依赖 LLM planner，但没有 schema 校验和 fallback，系统会更脆弱。

## 5. 目标设计

### 5.1 规划分两层输出

主 agent 需要同时输出两层结果：

1. 面向系统的结构化 plan
2. 面向用户的自然语言主持说明

要求：

- 结构化 plan 是唯一 task 真值来源。
- 自然语言主持说明由结构化 plan 派生，不能再独立编故事。

### 5.2 后端掌握最终写入权

主 agent 负责“提案”，后端负责“准入”：

- LLM 不能直接决定任意字段都落库。
- 后端必须校验 task 数量、字段完整性、agent 是否存在、依赖是否合法。
- 校验失败时，要么修复，要么降级，要么拒绝本次编排。

### 5.3 规则拆分降级为 fallback

现有 `task_splitter.py` 不应立刻删除，而应调整为 fallback：

- planner 输出不可解析时，允许走规则拆分。
- planner 输出为空时，允许退回规则拆分。
- planner 输出非法但可局部修复时，优先修复。

## 6. 后端实施任务

### 6.1 定义 planner 输出 schema

新增一个明确的结构化 plan schema，例如：

- `planner_summary`
- `tasks`
  - `title`
  - `goal`
  - `assigned_agent_id`
  - `input_payload`
  - `depends_on`
  - `reason`

要求：

- schema 要能表达 `1 -> N` task。
- `depends_on` 第一版允许为空数组或引用前置 task 临时 ID。
- `reason` 主要用于解释分配依据，供审计和 UI 展示。

建议新增：

- `backend/app/schemas/orchestration_planner.py`

#### 6.1.1 推荐 JSON 顶层结构

第一版建议主 agent 严格输出 JSON，对应一个 `PlannerPlan`：

```json
{
  "planner_summary": "将需求拆成 2 个任务，分别由后端 agent 与前端 agent 并行处理。",
  "planning_mode": "parallel",
  "tasks": [
    {
      "client_task_id": "task_1",
      "title": "新增后端接口",
      "goal": "在 backend 中新增 hello 接口并返回约定字段",
      "assigned_agent_id": "glm_backend",
      "reason": "该 agent 负责后端实现，适合处理 API 与数据结构变更",
      "input_payload": {
        "target_paths": [
          "backend/app/api/hello.py"
        ],
        "requested_changes": [
          "新增 GET /api/hello"
        ]
      },
      "depends_on": []
    },
    {
      "client_task_id": "task_2",
      "title": "接入前端调用",
      "goal": "在 frontend 中接入 hello 接口并展示返回结果",
      "assigned_agent_id": "glm_frontend",
      "reason": "该 agent 负责前端页面和接口接入",
      "input_payload": {
        "target_paths": [
          "frontend/src/api/modules/hello.ts",
          "frontend/src/views/Hello.vue"
        ],
        "requested_changes": [
          "新增 hello API 调用",
          "在页面展示返回内容"
        ]
      },
      "depends_on": [
        "task_1"
      ]
    }
  ]
}
```

字段约束建议：

- `planner_summary`: `string`，必填，长度 1-500。
- `planning_mode`: `parallel | sequential | mixed`，必填。
- `tasks`: `array`，必填，长度 1-8。
- `client_task_id`: `string`，必填，仅允许 `a-zA-Z0-9_-`，用于 planner 内部引用。
- `title`: `string`，必填，长度 1-80。
- `goal`: `string`，必填，长度 1-300。
- `assigned_agent_id`: `string`，必填。
- `reason`: `string`，必填，长度 1-200。
- `input_payload`: `object`，必填，允许为空对象。
- `depends_on`: `array[string]`，必填，可为空。

#### 6.1.2 落库前后的 ID 规则

需要明确两套 ID：

- `client_task_id`
  - 由 planner 输出
  - 仅用于 plan 内部引用和 `depends_on`
- `task.id`
  - 由后端落库时生成
  - 是真正的 orchestration task 主键

落库映射要求：

1. 先解析全部 planner tasks。
2. 校验 `client_task_id` 唯一。
3. 先创建数据库 task 记录。
4. 再把 `depends_on` 从 `client_task_id` 映射成真实 task 主键，或映射成内部可追踪关系。

#### 6.1.3 合法与非法输出示例

合法示例：

- 两个 task 都有 `title / goal / assigned_agent_id / reason`
- `depends_on` 只引用已有 `client_task_id`
- `planning_mode=parallel` 且两个 task 互不依赖

非法示例 1：缺少关键字段

```json
{
  "planner_summary": "拆成两个任务",
  "tasks": [
    {
      "title": "只写了标题"
    }
  ]
}
```

非法示例 2：引用不存在依赖

```json
{
  "planner_summary": "拆成一个串行任务",
  "planning_mode": "sequential",
  "tasks": [
    {
      "client_task_id": "task_1",
      "title": "任务 A",
      "goal": "完成 A",
      "assigned_agent_id": "glm_backend",
      "reason": "后端处理",
      "input_payload": {},
      "depends_on": [
        "task_404"
      ]
    }
  ]
}
```

非法示例 3：分配给不存在 agent

```json
{
  "planner_summary": "拆成一个任务",
  "planning_mode": "parallel",
  "tasks": [
    {
      "client_task_id": "task_1",
      "title": "任务 A",
      "goal": "完成 A",
      "assigned_agent_id": "ghost_agent",
      "reason": "随意填写",
      "input_payload": {},
      "depends_on": []
    }
  ]
}
```

### 6.2 新增 planner 服务层

新增主 agent 规划服务，例如：

- `backend/app/services/orchestration_planner.py`

职责：

1. 组装主 agent 的 planner prompt。
2. 注入当前 group 成员列表、primary agent、workspace、用户请求。
3. 调用 LLM 获取结构化 plan。
4. 解析结果。
5. 返回统一的 planner result。

planner result 建议包含：

- `status`
- `raw_output`
- `parsed_plan`
- `validation_errors`
- `fallback_used`

### 6.3 设计 planner prompt

主 agent 的 planner prompt 要明确约束：

- 你是唯一主持人。
- 你负责拆解用户请求为可执行任务。
- 你必须先判断任务数，再决定是否并行。
- 你必须从候选 agent 中选出执行者。
- 你必须输出结构化 plan。
- 若请求本质上只能拆成 1 个 task，不要为了凑数硬拆。

还要明确禁止：

- 不要把主持性说明混进结构化字段。
- 不要给不存在的 agent 分配任务。
- 不要生成空 goal。
- 不要把一个 task 写成多个互相冲突的目标。

建议放在：

- `backend/app/runtime/prompts/orchestration_planner_prompt.j2`

#### 6.3.1 planner 输入上下文建议

传给 planner 的上下文建议至少包括：

- 用户原始请求
- 当前 session 模式和 workspace 根信息
- primary agent 自身信息
- 候选执行 agent 列表
  - `agent_id`
  - `name`
  - `role`
  - `capability_tags`
  - `is_primary`
  - `is_active`
- 当前系统限制
  - 最大 task 数
  - 是否允许分配给 primary agent 自己
  - 第一版支持的 task kind 列表

#### 6.3.2 agent 选择策略矩阵

第一版不要让 planner 完全自由发挥，建议给出明确的选择优先级：

1. 优先按 `capability_tags` 匹配
2. 其次按显式 `role` 匹配
3. 再其次按用户请求里出现的技术域匹配
4. 若仍有多个候选，按稳定排序选择
5. 若没有合适子 agent，再考虑 primary agent 自己兜底

建议具体规则：

- 请求明显是前端工作：
  - 优先选择 `capability_tags` 包含 `frontend`、`ui`、`vue`、`react` 的 agent
- 请求明显是后端工作：
  - 优先选择 `capability_tags` 包含 `backend`、`api`、`python`、`fastapi` 的 agent
- 请求明显是测试工作：
  - 优先选择 `capability_tags` 包含 `test`、`qa`、`pytest`、`vitest` 的 agent
- 请求明显是文档工作：
  - 优先选择 `capability_tags` 包含 `docs`、`spec`、`writing` 的 agent

若多个候选都满足：

- 先看 `role` 是否更精确
- 再按 `agent_id` 字典序稳定选择

若一个 task 同时需要多域能力：

- 优先拆成多个 task
- 只有当拆分代价显著大于收益时，才允许分给单个全栈 agent

#### 6.3.3 primary agent 自己接单规则

第一版建议明确如下：

- 默认目标：primary agent 只主持，不执行
- 允许 primary agent 自己接单的场景：
  - 没有任何可用子 agent
  - 所有子 agent 都不匹配当前任务域
  - 用户请求本质上只有 1 个非常小的任务，拆分给别人没有收益
- 只要 primary agent 给自己分配任务，`reason` 必须明确说明原因

### 6.4 校验与修复

新增 plan validator，例如：

- `backend/app/services/orchestration_plan_validator.py`

校验内容至少包括：

1. `tasks` 非空
2. 每个 task 有 `title / goal / assigned_agent_id`
3. `assigned_agent_id` 必须属于当前 session 成员
4. 不能分配给不存在或 inactive agent
5. `depends_on` 不能引用不存在的 task
6. 不能出现简单循环依赖
7. task 数量不能超过系统上限

可自动修复的场景：

- 缺少 `input_payload` 时补空对象
- `depends_on` 缺失时补空数组
- `assigned_agent_id` 缺失但只有一个可用子 agent 时自动补全

不可自动修复时：

- 返回 planner_invalid
- 进入 fallback

#### 6.4.1 validator 输出结构建议

建议 validator 返回：

```json
{
  "status": "valid",
  "normalized_plan": {},
  "errors": [],
  "warnings": [],
  "repair_actions": []
}
```

其中：

- `status`: `valid | repaired | invalid`
- `normalized_plan`: 修复后的最终 plan
- `errors`: 不可接受问题
- `warnings`: 可接受但需要记录的问题
- `repair_actions`: 实际做过的自动修复动作

#### 6.4.2 planner/validator/fallback 状态机

建议明确成以下状态机：

1. `planner_requested`
2. `planner_returned_raw`
3. `planner_parsed`
4. `validator_valid`
5. `validator_repaired`
6. `validator_invalid`
7. `fallback_started`
8. `fallback_succeeded`
9. `fallback_failed`
10. `plan_committed`

转换规则：

- `planner_requested -> planner_returned_raw`
  - LLM 有返回原始文本
- `planner_returned_raw -> planner_parsed`
  - JSON 解析成功
- `planner_returned_raw -> fallback_started`
  - JSON 无法解析
- `planner_parsed -> validator_valid`
  - 结构与内容全部通过
- `planner_parsed -> validator_repaired`
  - 存在轻微问题，但后端修复成功
- `planner_parsed -> validator_invalid`
  - 存在不可修复问题
- `validator_valid -> plan_committed`
  - 直接落库
- `validator_repaired -> plan_committed`
  - 用修复后的 plan 落库
- `validator_invalid -> fallback_started`
  - 进入规则拆分
- `fallback_started -> fallback_succeeded`
  - 规则拆分成功生成 tasks
- `fallback_started -> fallback_failed`
  - 规则拆分也失败

#### 6.4.3 何时修复、何时 fallback、何时失败

自动修复：

- 缺 `input_payload`
- 缺 `depends_on`
- `planning_mode` 缺失但可从依赖关系推断
- 只有一个可用子 agent 时缺 `assigned_agent_id`

直接 fallback：

- planner 输出不是合法 JSON
- `tasks` 为空
- 存在不存在的 `assigned_agent_id`
- `client_task_id` 重复
- 依赖关系引用丢失且无法修复

直接失败，不进入 fallback 的场景建议尽量少，只保留系统级错误：

- 当前 session 没有任何可用 agent
- workspace 或 session 关键信息缺失
- 数据库落库失败
- planner 与 fallback 都失败

#### 6.4.4 fallback 成功后的标记要求

如果最终用了 fallback splitter，run 或 plan message 至少要打出以下标记之一：

- `planning_source=planner`
- `planning_source=planner_repaired`
- `planning_source=fallback_splitter`

这样前后端和审计日志都能知道这次计划的真实来源。

### 6.5 编排入口改造

改造 [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py) 的 group orchestration 链路：

当前：

1. 收到消息
2. 后端 `plan_tasks_from_message`
3. 创建 run/tasks
4. 主 agent 发计划消息

目标：

1. 收到消息
2. 调用 orchestration planner 获取结构化 plan
3. 校验 plan
4. 通过后创建 run/tasks
5. 用结构化 plan 生成主 agent 计划消息
6. 进入执行链路

#### 6.5.1 推荐编排伪流程

建议在 `ws` 群聊编排入口按以下顺序实现：

1. 保存 human message
2. 收集当前 session agent 列表
3. 调用 planner service
4. 记录 raw output
5. 解析并调用 validator
6. 若 `valid/repaired`，则创建 run/tasks
7. 若 `invalid`，则进入 fallback splitter
8. 若 fallback 也成功，则创建 run/tasks 并打 fallback 标记
9. 基于最终 plan 生成 host plan message
10. 进入 task execution

#### 6.5.2 run/task 落库字段补充

建议在 run 或 task 层增加与 planner 相关的审计字段，至少二选一：

- run 级：
  - `planning_source`
  - `planner_model`
  - `planner_status`
- task 级：
  - `assignment_reason`
  - `planner_client_task_id`

如果不想立即改数据库，也至少要写入 message metadata 或审计日志。

### 6.6 调整主 agent 计划消息来源

计划消息不能再手写一个“已拆解出 X 个任务”模板就结束，而应基于结构化 plan 生成：

- 总体判断
- 拆成几个任务
- 每个任务交给谁
- 为什么这么分
- 哪些并行，哪些串行

第一版可以仍然用模板渲染，不要求再调一次 LLM。

### 6.7 审计与可观测性

为后续排查 planner 质量，建议记录：

- 用户原始请求
- 候选 agent 列表
- planner raw output
- parsed plan
- validator errors
- fallback reason

不要只记录最终 tasks，否则无法知道“planner 想了什么，后端改了什么”。

## 7. 前端实施任务

### 7.1 展示结构化分配依据

现有 plan message 已能显示主持文本，未来需要补充从 payload 中读取：

- 每个 task 的 `assigned_agent_id`
- `reason`
- `depends_on`

第一版不必做复杂图形化，仅需让用户能看出：

- 为什么拆成这些任务
- 为什么给这些 agent
- 是否并行

### 7.2 标记 fallback 情况

如果本次任务不是 planner 主链路，而是 fallback 规则拆分，前端应能识别并显示轻提示，例如：

- “本次使用系统回退拆分策略”

这样用户能理解为什么计划质量可能偏弱。

### 7.3 兼容已有 task 视图

不要破坏当前 run/task 展示、task_start/task_end 和 pending change 链路。

要求：

- 旧字段继续兼容
- 新字段按增量方式接入

## 8. 测试任务

### 8.1 后端单测

新增 planner / validator 测试：

1. 主 agent 输出 2 个合法 tasks，可成功解析
2. 输出缺字段 plan，会被修复或拒绝
3. 输出非法 agent_id，会触发 fallback
4. 输出空 tasks，会触发 fallback
5. 输出 3 个 tasks 时，系统不写死双任务
6. `depends_on` 合法时可通过
7. 简单循环依赖会被拒绝

### 8.2 编排链路测试

补 group orchestration 入口测试：

1. 使用 planner 输出创建 run/tasks
2. plan message 内容来自结构化 plan
3. planner 失败时走 fallback splitter
4. fallback 情况下仍能生成 run/tasks
5. host 仍是唯一主持人
6. `planning_source` 能正确反映 planner / repaired / fallback
7. primary agent 自己接单时 `reason` 不为空

### 8.3 前端测试

1. 计划消息可展示结构化分配说明
2. fallback 标记能正确渲染
3. 多 task 时依赖关系展示不报错
4. 老 run/task 数据结构仍可正常渲染

## 9. 验收标准

### 9.1 行为标准

- 对于“一个用户请求包含两个不同工作项”的场景，主 agent 能稳定拆成 2 个结构化 tasks。
- 主 agent 的自然语言计划说明与实际落库 tasks 一致。
- 分配给哪个子 agent，不再主要由后端轮询决定，而由主 agent plan 决定。
- planner 失败时系统仍可降级，不会让群聊编排整体失效。

### 9.2 工程标准

- planner schema 明确且可测试。
- validator 独立存在，不把“解析+校验+修复”全部揉进 ws 入口。
- fallback 路径保留且可观测。
- 没有把系统写死成 “最多 2 个 tasks”。

### 9.3 兼容标准

- 单聊链路无回归。
- 现有 task 执行、pending change、run summary 主链路无回归。
- planner 不可用时仍能用旧规则链路完成基础任务。

## 10. 推荐实施顺序

建议按以下顺序拆子任务实施：

1. 定义 planner schema 和 validator
2. 新增 orchestration planner service
3. 接入 ws orchestration 主链路
4. 让 plan message 改为从结构化 plan 派生
5. 保留并接通 fallback splitter
6. 增加前端 plan 展示和 fallback 标记
7. 补全测试与审计

## 11. 风险与决策点

### 11.1 结构化输出格式

需要尽早定：

- JSON
- XML
- 还是工具调用式结构

建议优先 JSON 或明确 schema 的工具调用，便于校验。

### 11.2 主 agent 是否允许把任务分配给自己

需要明确定策：

- 默认允许，但只在没有更合适子 agent 时使用
- 或默认禁止，只做主持

建议第一版：

- 允许，但要显式记录 `reason`
- 若 session 中存在可用子 agent，优先分给子 agent

### 11.3 planner 与执行 agent 是否使用同一模型

第一版允许相同模型，但实现上最好解耦：

- planner 是 planner
- executor 是 executor

后续才能独立优化成本和质量。

## 12. 交付物

- planner schema
- planner service
- validator service
- ws orchestration 主链路改造
- fallback splitter 接入
- plan message 结构化派生
- 前端分配说明展示
- 单测、集成测试、回归测试
