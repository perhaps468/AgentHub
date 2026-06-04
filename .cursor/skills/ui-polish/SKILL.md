# -*- coding: utf-8 -*-
---
name: ui-polish
description: 提供让页面变得更加高级、精致的建议和最佳实践。当用户想让界面看起来更专业、更有质感、提升视觉品质、让UI更高级时使用此技能。
---

# 页面高级感设计指南

## 核心理念

高级感不是堆砌特效，而是**克制与精致**。核心原则：

1. **一致性** - 所有元素遵循统一的设计语言
2. **呼吸感** - 留白是奢侈品，适当留白提升格调
3. **精致感** - 细节处理体现品质
4. **层次感** - 通过微妙的明暗对比建立视觉层级

---

## 配色方案

### 推荐高级配色

| 风格 | 主色 | 辅助色 | 背景色 |
|------|------|--------|--------|
| 极简奢华 | #1a1a2e 深紫黑 | #16213e 藏青 | #0f0f1a 墨黑 |
| 优雅米白 | #2d2d2d 深灰 | #f5f5f0 米白 | #fafaf8 暖白 |
| 科技感 | #0a0a0a 纯黑 | #1e3a5f 靛蓝 | #050510 深空 |
| 莫兰迪 | #8b8589 灰粉 | #c9b1bd 淡紫 | #f5f3f4 暖灰 |
| 极光 | #667eea 渐变蓝 | #764ba2 渐变紫 | #1a1a2e 深色 |

### 避免的颜色
- 纯黑 (#000000) - 过于生硬
- 纯白 (#ffffff) - 刺眼，缺层次
- 饱和度高的颜色 - 廉价感来源
- 超过3种的亮色混用
- 过多的颜色数量 - 配色不超过3种主色

### 高级渐变技巧
```css
/* 柔和渐变 - 背景 */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* 微妙的叠加渐变 */
background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 100%);

/* 极光效果 */
background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
```

---

## 字体规范

### 字体选择
```css
/* 中文推荐 */
font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;

/* 英文/数字 */
font-family: "SF Pro Display", "Inter", -apple-system, sans-serif;

/* 代码/数据 */
font-family: "SF Mono", "JetBrains Mono", "Fira Code", monospace;
```

### 字号层级
```
主标题: 24-32px, font-weight: 600-700
副标题: 18-20px, font-weight: 500-600
正文: 14-16px, font-weight: 400
辅助文字: 12-13px, font-weight: 400
```

### 高级字体技巧
```css
/* 文字描边 - 高级感装饰 */
-webkit-text-stroke: 0.5px rgba(255,255,255,0.3);

/* 文字渐变 */
background: linear-gradient(135deg, #fff 0%, #a0a0a0 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;

/* 文字阴影 - 层次感 */
text-shadow: 0 2px 4px rgba(0,0,0,0.1);
```

---

## 玻璃拟态 (Glassmorphism)

让界面轻盈现代的利器：

```css
/* 玻璃效果 */
background: rgba(255, 255, 255, 0.1);
backdrop-filter: blur(20px);
-webkit-backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.2);
border-radius: 16px;

/* 深色玻璃 */
background: rgba(0, 0, 0, 0.3);
backdrop-filter: blur(16px);
border: 1px solid rgba(255, 255, 255, 0.1);
```

### 使用场景
- 导航栏/侧边栏背景
- 模态框
- 卡片叠加层
- 半透明覆盖层

---

## 阴影与层次

### 微阴影营造深度
```css
/* 卡片阴影 - 柔和但不明显 */
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

/* 浮层阴影 - 用于弹窗 */
box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);

/* 内阴影 - 凹陷效果 */
box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);

/* 多层阴影 - 立体感 */
box-shadow: 
  0 2px 4px rgba(0, 0, 0, 0.02),
  0 4px 8px rgba(0, 0, 0, 0.04),
  0 8px 16px rgba(0, 0, 0, 0.06);
```

### 避免的错误
- ❌ 夸张的大阴影 `box-shadow: 0 10px 50px red`
- ❌ 过多的阴影层次
- ❌ 阴影颜色过于明显
- ❌ 使用纯色阴影 (应该用半透明黑)

---

## 圆角规范

| 元素 | 圆角大小 |
|------|----------|
| 按钮/输入框 | 6-8px |
| 卡片 | 12-16px |
| 模态框 | 16-24px |
| 头像/图标 | 50% (圆形) |

**原则**：功能元素小圆角，容器元素大圆角

---

## 动效设计

### 高级感动效特征
- **时长**：150-300ms 最佳，过长显得拖沓
- **缓动**：使用 `ease-out` 或 `cubic-bezier(0.16, 1, 0.3, 1)`
- **克制**：不必要的不动，能少则少
- **有目的**：每个动效都应该有功能性理由

### 推荐动效
```css
/* 淡入 */
transition: opacity 200ms ease-out;

/* 上浮 */
transition: transform 250ms cubic-bezier(0.16, 1, 0.3, 1), 
            box-shadow 250ms ease-out;

/* 点击反馈 */
transform: scale(0.98);
transition: transform 100ms ease-out;

/* 弹性效果 */
transition: transform 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
```

### 高级动效技巧
```css
/* 交错动画 - 列表项依次出现 */
animation-delay: calc(var(--index) * 50ms);

/* 视差滚动 */
transform: translateY(calc(scrollY * 0.3));

/* 渐变流动背景 */
background-size: 200% 200%;
animation: gradient 3s ease infinite;
@keyframes gradient {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
```

### 避免的动画
- ❌ 闪烁/跳动效果
- ❌ 超过500ms的简单过渡
- ❌ 闪烁的光标
- ❌ 任意元素的无限旋转（加载除外）

---

## 边框与分割线

### 高级感边框
```css
/* 细线边框 */
border: 1px solid rgba(0, 0, 0, 0.08);

/* 渐变边框 (装饰性) */
border-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%) 1;
```

### 避免
- ❌ 粗边框 (超过2px除非是强调)
- ❌ 实线黑色边框
- ❌ 过多分割线

---

## 状态设计

### Hover 状态
```css
/* 微妙的明度变化 */
background-color: rgba(0, 0, 0, 0.03);

/* 或微上浮 */
transform: translateY(-2px);
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

/* 边框高亮 */
border-color: var(--accent);
```

### Active 状态
```css
transform: scale(0.98);
opacity: 0.9;
```

### Disabled 状态
```css
opacity: 0.4;
cursor: not-allowed;
pointer-events: none;
```

### Focus 状态（无障碍友好）
```css
/* 不要移除默认 focus 样式，而是增强它 */
outline: none;
border-color: var(--accent);
box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
```

---

## 高级交互模式

### 渐变边框
```css
/* 伪元素实现 */
position: relative;
border-radius: 12px;
background: linear-gradient(#fff, #fff) padding-box,
            linear-gradient(135deg, #667eea, #764ba2) border-box;
border: 2px solid transparent;
```

### 微光效果
```css
/* 扫描线/光泽效果 */
.card {
  position: relative;
  overflow: hidden;
}
.card::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
  transition: left 0.5s;
}
.card:hover::after {
  left: 100%;
}
```

### 文字动效
```css
/* 打字机效果 */
animation: typing 3s steps(30) forwards;

/* 淡入上浮 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 发光文字 */
text-shadow: 0 0 10px currentColor;
```

---

## 图标风格

推荐使用：
- **线性图标** - Lucide, Feather, Heroicons
- **双色调图标** - 若使用
- 统一 **1.5-2px** 的线宽
- 保持一致的 **24x24** 或 **20x20** 尺寸

---

## 实用建议

### 快速提升高级感
1. **加透明度**：白色用 `rgba(255,255,255,0.8)` 替代
2. **用深色背景**：深色系天然更显质感
3. **减少主色面积**：主色占比不超过60%
4. **统一圆角**：全站使用同一套圆角规范
5. **加入微妙的边框**：`border: 1px solid rgba(0,0,0,0.06)`

### 降低廉价感
1. 避免所有元素等大等宽
2. 不要用纯黑/纯白文字
3. 不要所有东西都加 hover 效果
4. 避免闪烁、跳动等花哨动画
5. 文字不要紧贴边框

---

## 快速检查清单

在完成高级感改造后，逐项检查：

- [ ] 颜色不超过3种主色，使用透明度增加层次
- [ ] 阴影使用半透明而非纯色
- [ ] 圆角统一（全站使用同一套规范）
- [ ] 动效时长在150-300ms之间
- [ ] hover 效果微妙（轻上浮或明度变化）
- [ ] 留白充足，不要让元素太拥挤
- [ ] 边框细（1px）且使用半透明色
- [ ] 文字有层级（主/次/辅助三级）
- [ ] 图标风格统一（线性/填充二选一）

---

## 配色参考示例

```css
/* 深色主题 */
--bg-primary: #0a0a0f;
--bg-secondary: #12121a;
--bg-elevated: #1a1a24;
--border: rgba(255, 255, 255, 0.08);
--text-primary: rgba(255, 255, 255, 0.92);
--text-secondary: rgba(255, 255, 255, 0.55);
--accent: #6366f1;

/* 浅色主题 */
--bg-primary: #fafafa;
--bg-secondary: #ffffff;
--bg-elevated: #ffffff;
--border: rgba(0, 0, 0, 0.06);
--text-primary: rgba(0, 0, 0, 0.88);
--text-secondary: rgba(0, 0, 0, 0.45);
--accent: #4f46e5;
```

---

## 使用方法

当用户要求让页面"看起来更高级"、"更精致"、"更有质感"时：

1. 分析当前页面的配色、字体、间距
2. 提出具体可执行的改进建议
3. 给出代码示例或参考
4. 优先处理影响最大的元素（通常是配色和间距）
