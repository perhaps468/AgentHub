-- P5-2 Provider 路由迁移脚本
-- 1. 为已有 agents 表新增 provider 列
-- 2. 补全内置 Agent 的 provider 值
-- 3. 预置 GLM Agent（智谱 AI）

-- ============================================================
-- Step 1: 新增 provider 列（已有表兼容）
-- ============================================================
ALTER TABLE agents
  ADD COLUMN IF NOT EXISTS provider VARCHAR(50) NOT NULL DEFAULT 'qwen_openai_compatible'
  COMMENT 'Provider 标识，如 qwen_openai_compatible / doubao / glm'
  AFTER role;

-- ============================================================
-- Step 2: 补齐已有 PM Agent 的 provider（如果还是旧默认值）
-- ============================================================
UPDATE agents
SET provider = 'qwen_openai_compatible'
WHERE id = 'pm_agent' AND (provider = '' OR provider IS NULL);

-- ============================================================
-- Step 3: 预置 GLM Coder Agent
-- ============================================================
INSERT INTO agents (
  id, owner_id, name, role, provider, model, system_prompt, platform,
  description, avatar_url, capability_tags, tool_permissions,
  is_builtin, is_active, created_at, updated_at
) VALUES (
  'glm_coder',
  NULL,
  'GLM Coder',
  'Coder',
  'glm',
  'glm-4.7-flash',
  '你是 AgentHub 的 Coder Agent，基于智谱 GLM-4.7 模型。\n\n你的职责是：\n- 将 PM Agent 拆解的任务转化为高质量代码\n- 遵循项目现有架构与编码风格\n- 编写可运行、可测试、可维护的代码\n- 主动处理边界条件与错误路径\n\n【行为规则】\n\n1. 先理解再动手\n- 阅读相关文件后再修改\n- 不确定的设计先提出方案\n\n2. 最小变更原则\n- 只改任务要求的代码\n- 不做范围外的重构\n\n3. 完整交付\n- 确保代码可运行\n- 补充必要的测试\n\n4. 遵循现有规范\n- 文件名、变量名、函数名与项目保持一致\n- 使用项目已有的工具库和框架\n\n5. 错误处理\n- 对外部输入做校验\n- 异常路径要有清晰错误信息',
  'custom',
  '内置 Coder Agent，基于智谱 GLM-4.7-Flash，负责代码生成与调试',
  NULL,
  JSON_ARRAY('代码生成', '调试修复', '前端开发', '后端开发', '测试验证'),
  JSON_ARRAY('*'),
  TRUE,
  TRUE,
  NOW(),
  NOW()
) ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  description = VALUES(description),
  model = VALUES(model),
  provider = VALUES(provider),
  system_prompt = VALUES(system_prompt),
  capability_tags = VALUES(capability_tags),
  updated_at = NOW();

-- ============================================================
-- Step 4: 预置 GLM Reviewer Agent
-- ============================================================
INSERT INTO agents (
  id, owner_id, name, role, provider, model, system_prompt, platform,
  description, avatar_url, capability_tags, tool_permissions,
  is_builtin, is_active, created_at, updated_at
) VALUES (
  'glm_reviewer',
  NULL,
  'GLM Reviewer',
  'Reviewer',
  'glm',
  'glm-4.7-flash',
  '你是 AgentHub 的 Reviewer Agent，基于智谱 GLM-4.7 模型。\n\n你的职责是：\n- 审查代码质量与安全性\n- 检查是否满足 PM Agent 定义的需求\n- 发现潜在 bug 与性能问题\n- 给出具体、可操作的改进建议\n\n【审查维度】\n\n1. 功能正确性\n- 代码是否实现了要求的逻辑\n- 边界条件是否覆盖\n\n2. 代码质量\n- 命名是否清晰\n- 结构是否合理\n- 是否有重复代码\n\n3. 安全性\n- 有无注入风险\n- 认证授权是否正确\n\n4. 性能\n- 是否存在 N+1 查询\n- 是否有不必要的循环\n\n5. 可维护性\n- 是否有足够的注释\n- 错误处理是否完善\n\n【输出格式】\n- 用结构化列表给出审查意见\n- 问题按严重程度排序\n- 每个问题附带改进建议',
  'custom',
  '内置 Reviewer Agent，基于智谱 GLM-4.7-Flash，负责代码审查与质量保障',
  NULL,
  JSON_ARRAY('代码审查', '安全审计', '性能分析', '测试验证'),
  JSON_ARRAY(),
  TRUE,
  TRUE,
  NOW(),
  NOW()
) ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  description = VALUES(description),
  model = VALUES(model),
  provider = VALUES(provider),
  system_prompt = VALUES(system_prompt),
  capability_tags = VALUES(capability_tags),
  updated_at = NOW();
