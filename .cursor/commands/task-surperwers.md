# 测试驱动开发（TDD）

## 概览

先写测试。看它失败。再写最少代码让它通过。

**核心原则：**  
如果你没亲眼看到测试先失败，就无法确认它真的能测出问题。

```text
没有先失败的测试，就不允许写生产代码
```

## Task 铁律

```
没有已批准的 task 边界，就不允许开始实现 
```

开始任何一个 TDD 循环前，先确认：

- 当前实现对应哪个 task
- task 的验收标准是什么
- 本轮测试验证的是 task 内哪一个行为

**必须遵守：**

- 一个 task 一个行为地推进，不要一口气跨多个 task 写代码
- 测试名、实现范围、验证结果都要能回指到当前 task
- 如果写测试时发现需要新行为，但它不在当前 task 里，停下并补充/调整 task，而不是直接实现
- 不允许借“顺手优化”“顺便补全”“一起做了”扩 scope

## 何时使用

**始终适用：**

- 新功能
- Bug 修复
- 重构
- 行为变更

**例外（先问团队）：**

- 一次性原型
- 生成代码
- 配置文件

如果你开始想“这次先跳过 TDD”，通常是在自我合理化。

---

# 红-绿-重构

## RED - 写失败测试

先写一个最小测试，只描述“应该发生什么”。

```typescript
test('失败操作会重试 3 次', async () => {
  let attempts = 0;

  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);

  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```

### 要求

- 一次只测一个行为
- 测试名清晰
- 优先测真实行为，不是 mock

反例：

```typescript
test('retry works', async () => {
  const mock = jest.fn();
  await retryOperation(mock);
  expect(mock).toHaveBeenCalledTimes(3);
});
```

名字模糊，而且测的是 mock。

---

## Verify RED - 确认它真的失败

**绝不能跳过。**

```bash
npm test
```

确认：

- 测试失败，而不是报错
- 失败原因正确
- 是因为功能未实现，而不是拼写错误

### 如果测试直接通过？

说明你测的是已有行为，重新写测试。

### 如果测试报错？

先修测试，直到它以正确方式失败。

---

## GREEN - 最小实现

只写刚好能通过测试的代码。

```typescript
async function retryOperation(fn) {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
}
```

不要顺手：

- 加功能
- 做优化
- 重构别的代码

反例：

```typescript
async function retryOperation(fn, options) {
  // 过度设计
}
```

---

## Verify GREEN - 确认全部通过

再次运行测试。

```bash
npm test
```

确认：

- 当前测试通过
- 其他测试也通过
- 没有 warning 或报错

如果失败：

- 修代码，不改测试

---

## REFACTOR - 重构整理

只有变绿后才能重构：

- 去重复
- 改命名
- 抽公共逻辑

始终保持测试为绿，不引入新行为。

---

# 为什么顺序不能反

## “先写代码，再补测试”

事后测试回答的是：

```text
“代码现在做了什么？”
```

测试先行回答的是：

```text
“它本来应该做什么？”
```

直接通过的测试无法证明：

- 测试真的有效
- 边界情况被覆盖
- bug 能被抓住

---

## “我已经手动测过了”

手动测试的问题：

- 不可重复
- 没记录
- 容易漏边界
- 改代码后无法自动验证

自动化测试才能稳定防回归。

---

## “删掉已经写好的代码太浪费”

这是沉没成本。

你只有两个选择：

- 删掉，用 TDD 重写（信心高）
- 保留未验证代码（技术债）

真正浪费的是保留自己都不信任的代码。

---

# 常见借口

| 借口             | 现实                           |
| ---------------- | ------------------------------ |
| “这太简单了”     | 简单代码一样会坏               |
| “之后再测”       | 一上来通过的测试证明不了任何事 |
| “手动测过了”     | 临时测试不等于系统测试         |
| “事后测试也一样” | 事后测试会被实现细节影响       |
| “TDD 太慢”       | 调 bug 更慢                    |
| “先留代码参考”   | 本质还是事后补测试             |

---

# 红旗信号：立刻停下

出现以下任意情况，都说明你偏离了 TDD：

- 先写代码后写测试
- 测试第一次运行就通过
- 测试被放到“后面再补”
- “这次特殊”
- “我已经手动测了”
- “先留着参考”
- “删掉太浪费”

处理方式只有一个：

```text
删掉代码，从失败测试重新开始
```

---

# Bug 修复示例

## RED

```typescript
test('拒绝空邮箱', async () => {
  const result = await submitForm({ email: '' });

  expect(result.error).toBe('Email required');
});
```

## Verify RED

```bash
FAIL: expected 'Email required', got undefined
```

## GREEN

```typescript
function submitForm(data) {
  if (!data.email?.trim()) {
    return { error: 'Email required' };
  }
}
```

## Verify GREEN

```bash
PASS
```

## REFACTOR

如果多个字段有类似逻辑，再抽公共校验。

---

# 好测试标准

| 好测试           | 坏测试             |
| ---------------- | ------------------ |
| 一次只测一个行为 | 一个测试测很多东西 |
| 名字清晰         | `test1`            |
| 测真实行为       | 测 mock            |
| 展示 API 意图    | 看不出代码该干什么 |

---

# 验证清单

完成前确认：

- [ ] 每个新增功能都有测试
- [ ] 每个测试都先失败过
- [ ] 失败原因正确
- [ ] 实现是最小通过代码
- [ ] 所有测试通过
- [ ] 没有 warning
- [ ] 覆盖边界情况

有任何一项做不到，说明你跳过了 TDD。

---

# 卡住时怎么办

| 问题         | 解决办法                 |
| ------------ | ------------------------ |
| 不知道怎么测 | 先写期望 API             |
| 测试太复杂   | 说明设计太复杂           |
| 全靠 mock    | 说明耦合太高             |
| 初始化太重   | 抽辅助函数，继续简化设计 |

---

# 最终规则

```text
生产代码 -> 必须先有失败测试
否则 -> 就不是 TDD
```