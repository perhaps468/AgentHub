-- P5-1 Agent 表迁移脚本
-- 创建统一 Agent 表，并预置内置 PM Agent

CREATE TABLE IF NOT EXISTS agents (
  id VARCHAR(50) PRIMARY KEY COMMENT 'Agent ID，内置 Agent 使用稳定字符串 ID',
  owner_id VARCHAR(100) DEFAULT NULL COMMENT '所属用户 ID；内置 Agent 为 NULL',
  name VARCHAR(100) NOT NULL COMMENT 'Agent 展示名称',
  role VARCHAR(50) NOT NULL COMMENT 'Agent 角色，如 PM / Coder',
  provider VARCHAR(50) NOT NULL DEFAULT 'qwen_openai_compatible' COMMENT 'Provider 标识，如 qwen_openai_compatible / doubao',
  model VARCHAR(100) NOT NULL COMMENT '模型标识',
  system_prompt TEXT NOT NULL COMMENT 'System Prompt',
  platform VARCHAR(20) NOT NULL DEFAULT 'custom' COMMENT 'claude-code / codex / opencode / custom',
  description VARCHAR(500) DEFAULT NULL COMMENT 'Agent 简介',
  avatar_url VARCHAR(500) DEFAULT NULL COMMENT '头像地址',
  capability_tags JSON NOT NULL COMMENT '能力标签数组',
  tool_permissions JSON NOT NULL COMMENT '工具权限占位字段',
  is_builtin BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否内置 Agent',
  is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否可用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_agents_owner_id (owner_id),
  INDEX idx_agents_is_builtin (is_builtin),
  INDEX idx_agents_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统一 Agent 表';

-- 预置内置 PM Agent（使用稳定 ID，避免重复插入）
INSERT INTO agents (
  id, owner_id, name, role, provider, model, system_prompt, platform,
  description, avatar_url, capability_tags, tool_permissions,
  is_builtin, is_active, created_at, updated_at
) VALUES (
  'pm_agent',
  NULL,
  'PM Agent',
  'PM',
  'qwen_openai_compatible',
  'qwen-plus',
  '你是 AgentHub 的 PM Agent（Product Manager Agent）。\n\n你的职责是：\n- 理解用户真实需求\n- 拆解功能与阶段目标\n- 控制 MVP 范围\n- 输出结构化任务\n- 为 Architect / Coder / Reviewer Agent 提供清晰上下文\n\n你始终需要从：\n- 产品目标\n- 用户体验\n- 系统演进\n- 可实现性\n几个角度思考问题。\n\n【行为规则】\n\n1. 不直接写代码\n除非用户明确要求，否则不要输出实现代码。\n\n2. 优先做需求收敛\n先明确：\n- 用户真正要解决什么问题\n- 哪些是核心功能\n- 哪些属于后续增强\n\n3. 严格控制 MVP\n避免：\n- 过度设计\n- 提前复杂化\n- 把 P2/P3 能力塞进 MVP\n\n4. 强调闭环\n优先保证：\n- 可运行\n- 可演示\n- 可验证\n\n5. 输出结构化结果\n默认按以下格式输出：\n\n# 需求理解\n# 功能拆解\n# 推荐实现顺序\n# Agent 分工\n# 风险与注意事项\n\n【AgentHub 特殊要求】\n\nAgentHub 的核心是：\n- IM 聊天\n- Agent Runtime\n- 多 Agent 协作\n- ���下文连续\n- 产物与 Diff 状态\n\n重点关注：\n- Session / Message 抽象\n- Streaming\n- Orchestrator 边界\n- Workspace / VFS\n- 多 Agent 流程\n\n警惕：\n- 只有 UI 没有 Runtime\n- 临时方案导致后期重构\n- 阶段边界混乱\n\n你的目标不是"回答问题"，而是：\n帮助系统形成清晰、可持续演进的产品结构。',
  'custom',
  '内置产品经理 Agent，负责需求理解、功能拆解与任务规划',
  NULL,
  JSON_ARRAY('需求分析', '方案设计', '任务拆解', '产品规划'),
  JSON_ARRAY(),
  TRUE,
  TRUE,
  NOW(),
  NOW()
) ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  description = VALUES(description),
  updated_at = NOW();

-- 预置 GLM Coder Agent
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
  updated_at = NOW();

-- 预置 GLM Reviewer Agent
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
  updated_at = NOW();
