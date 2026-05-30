# Task C-2 - 最小代码生成与确认落盘闭环

> 本文建立在 [06-task-bc1-workspace-session-binding.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/06-task-bc1-workspace-session-binding.md) 完成的基础上。
>
> 目标是基于当前代码实现，先跑通一个最小但完整的 Code Agent 流程：
> 用户创建会话并绑定工作区，要求“帮我实现一个 java 程序，helloworld”，系统读取当前工作区、发现无文件、生成 `HelloWorld.java` 预览改动、返回 diff 和确认，用户确认后才真正落盘。

---

## 1. 文档目标与范围

### 1.1 目标

实现以下最小闭环：

1. 用户在已绑定工作区的会话中提出 `HelloWorld.java` 需求
2. runtime 读取当前工作区
3. 若文件不存在，则创建 `HelloWorld.java` 的预览改动
4. 返回给用户 diff 与确认请求
5. 用户通过按钮或文本确认
6. 后端正式把文件写入工作区

### 1.2 本文覆盖内容

- 当前工作区文件状态读取
- 固定文件名 `HelloWorld.java`
- 创建文件预览与结构化 diff
- 前端确认按钮
- 文本确认兜底
- 确认后真正落盘

### 1.3 本文不覆盖内容

- 多文件生成
- 智能文件命名
- preview iframe
- 自动测试 / 自修复
- 通用代码生成产品化策略

---

## 2. 需求背景与目标场景

### 2.1 目标场景

用户进入已绑定工作区的会话后输入：

- `帮我实现一个java程序，helloworld`

系统应完成：

- 读取当前工作区
- 判断 `HelloWorld.java` 不存在
- 生成 Java HelloWorld 代码
- 通过写文件工具生成 `PendingChange`
- 向用户展示 diff
- 用户确认后再真正落盘

### 2.2 当前代码现状

当前仓库已经具备：

- `ReadFileTool`、目录读取与搜索工具
- `WriteFileTool`、`ReplaceInFileTool`、`UnifiedDiffTool`
- `PendingChange`
- `ApplyChangeTool`
- runtime 与消息流主链路

当前仍缺少：

- 面向用户的“确认后落盘”闭环
- diff 的前端确认交互
- 文本确认与按钮确认的统一协议

### 2.3 当前缺口

当前虽然已经能做 preview / apply 的底层能力，但还不能证明：

- 用户可见 diff
- 用户可确认或拒绝
- 未确认前文件不会落盘
- 确认后文件会真正写入工作区

---

## 3. 目标流程

### 3.1 用户提出需求

用户在已绑定工作区的会话中输入：

- `帮我实现一个java程序，helloworld`

### 3.2 runtime 读取当前工作区

runtime 使用当前 session 绑定的 workspace：

- 列目录或检查目标文件
- 确认 `HelloWorld.java` 是否存在

### 3.3 判断当前文件不存在

如果工作区内不存在 `HelloWorld.java`：

- 走创建文件路径

### 3.4 生成 `HelloWorld.java` 预览改动

生成固定内容的 Java 文件，例如：

```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

然后通过 `WriteFileTool` 生成 `PendingChange`。

### 3.5 返回 diff 与确认请求

系统返回给用户：

- `HelloWorld.java` 的创建 diff
- 确认提示
- 可点击确认按钮
- 也可通过文本输入确认

### 3.6 用户确认

支持两种确认路径：

- 按钮确认
- 文本确认，例如：`确认应用` / `apply`

### 3.7 后端正式落盘

后端根据 `change_id` 调用 `ApplyChangeTool` 或等价正式 apply 链路：

- 文件真正写入工作区

### 3.8 返回成功结果

系统返回：

- 应用成功
- 文件路径
- 可选地返回最终摘要

---

## 4. 后端方案

### 4.1 读取当前工作区文件状态

runtime 必须使用 session 绑定的 workspace：

- 列目录或检查目标文件是否存在

不允许：

- 跳过 workspace 直接写默认路径

### 4.2 固定目标文件名策略

本任务固定：

- 文件名为 `HelloWorld.java`
- 落在当前工作区根目录

不在本任务中做动态命名。

### 4.3 `PendingChange` / diff 预览链路

写文件不直接落盘，而是：

- 调用 `WriteFileTool`
- 返回 `PendingChange`
- 其中包含 `change_id`
- 其中包含 `unified_diff`

### 4.4 `ApplyChangeTool` 与确认落盘链路

确认落盘必须通过正式 apply 链路：

- 前端按钮确认时，传回 `change_id`
- 文本确认时，后端从当前会话上下文识别待确认 change
- 后端调用 `ApplyChangeTool`

### 4.5 文本确认协议

文本确认最小支持：

- `确认应用`
- `apply`

后端需要能把这类输入映射到当前待确认 change。

### 4.6 按钮确认协议

按钮确认建议最小请求体包含：

- `session_id`
- `change_id`
- `action=confirm_apply`

按钮是主路径，文本确认是兜底路径。

### 4.7 落盘后的消息返回

落盘成功后，系统至少返回：

- 已应用成功
- 文件名
- 文件路径

如 apply 失败，要返回：

- 失败原因
- 文件未落盘结论

---

## 5. 前端方案

### 5.1 diff 预览展示

前端在收到创建文件预览后，至少要能展示：

- 文件名 `HelloWorld.java`
- diff 文本
- 当前状态为“待确认”

### 5.2 确认按钮展示

前端在 diff 消息区域提供确认按钮，例如：

- `确认写入`

该按钮点击后调用后端确认接口。

### 5.3 文本确认指令支持

除了按钮，前端不需要额外特殊 UI，只要允许用户继续输入：

- `确认应用`
- `apply`

### 5.4 落盘成功后的反馈展示

前端在收到 apply 成功后，至少要展示：

- 已写入成功
- 文件路径

同时更新该条 diff/确认消息状态，避免重复确认。

---

## 6. 实现步骤

### Step 1：读取工作区并判断文件存在性

- 在 runtime 中读取当前 workspace
- 检查 `HelloWorld.java` 是否存在

### Step 2：生成 `HelloWorld.java` 预览改动

- 生成固定 Java HelloWorld 代码
- 通过 `WriteFileTool` 创建 `PendingChange`

### Step 3：返回结构化 diff

- 把 `PendingChange.unified_diff`
- `change_id`
- 待确认状态

一起返回给前端

### Step 4：接入确认按钮与文本确认

- 前端渲染按钮
- 后端提供确认 apply 接口或 WS action
- 文本确认作为兜底协议支持

### Step 5：落盘执行与结果回写

- 用户确认后调用 `ApplyChangeTool`
- 成功后返回成功消息
- 失败后返回失败原因

### Step 6：端到端回归验证

- 从新建会话到生成 diff 再到确认落盘完整回归

---

## 7. 测试方案

### 7.1 工作区空目录读取测试

至少覆盖：

- 空目录下能检查文件不存在

### 7.2 创建文件预览测试

至少覆盖：

- 输入 HelloWorld 需求后能生成 `PendingChange`
- `PendingChange.operation=create`

### 7.3 diff 生成测试

至少覆盖：

- 返回 diff 中包含 `HelloWorld.java`
- 返回 diff 中包含预期 Java 内容

### 7.4 确认前不落盘测试

至少覆盖：

- 生成 preview 后，磁盘上仍不存在 `HelloWorld.java`

### 7.5 按钮确认落盘测试

至少覆盖：

- 点击确认按钮后文件真正写入

### 7.6 文本确认落盘测试

至少覆盖：

- 输入 `确认应用` 或 `apply` 后文件真正写入

### 7.7 成功结果回写测试

至少覆盖：

- apply 成功后前端能看到成功结果
- 不能重复确认同一个 change

---

## 8. 验收条件

### 8.1 能生成 `HelloWorld.java` 预览

- 用户输入指定需求后能生成该文件的预览改动

### 8.2 能返回 diff 与确认

- 用户能看到 diff
- 用户能点击按钮确认或输入文本确认

### 8.3 未确认前文件不落盘

- preview 生成后磁盘上还没有真实文件

### 8.4 确认后文件真正写入工作区

- 用户确认后，`HelloWorld.java` 在当前 workspace 中真实存在

---

## 9. 风险与回滚

### 9.1 风险点

- runtime 生成了 preview，但前端拿不到 `change_id`
- 前端有按钮，但后端没有稳定确认接口
- 文本确认命中错误的 pending change
- apply 成功后状态未同步，导致重复确认

### 9.2 回滚策略

- 按钮确认不可用时，保留文本确认兜底
- 若确认链路不稳定，可暂时回退为 preview-only 模式
- 若 apply 状态同步有问题，先禁止重复确认入口

---

## 10. 与原 Task C 的关系

本文完成后，原先总文档中的 `Task C` 不需要再以原粒度完整重复执行。

更准确地说：

- 本文已经覆盖了原 `Task C` 中你当前最关心、也最需要先落地的最小闭环部分
- 后续如果继续扩展 `Task C`，只需要做更通用的多文件、多命令、多轮确认能力
- 不需要再重复做一次“工作区 + 单文件 diff + 确认落盘”的同一条链路

也就是说：

- **原 Task C 不会消失**
- 但它会被本文“前置消化掉一大半”
- 后续剩余 Task C 只保留通用化与扩展部分

