-- Seed custom agents for owner_id = 2
-- Generated on 2026-06-05
-- Safe to run multiple times via ON DUPLICATE KEY UPDATE.

SET NAMES utf8mb4;

INSERT INTO `agenthub`.`agents` (`id`, `owner_id`, `name`, `role`, `provider`, `model`, `system_prompt`, `platform`, `description`, `avatar_url`, `capability_tags`, `tool_permissions`, `is_builtin`, `is_active`, `created_at`, `updated_at`) VALUES
('backend_agent', '2', '后端开发Agent', 'coder', 'qwen_openai_compatible', 'qwen3.6-flash', '你是专业的后端开发Agent，负责接口、逻辑、数据库开发。', 'custom', '专注后端服务与API开发', NULL, '["backend", "java", "python", "api"]', '["*"]', 0, 1, '2026-06-04 18:12:59', '2026-06-04 18:18:06'),
('code_agent', '2', 'Coder Agent', 'coder', 'qwen_openai_compatible', 'qwen3.6-flash', '你是专业的代码生成Agent，负责根据任务要求编写、修改代码文件，完成具体开发工作。不做需求分析、任务拆解、产品规划，只专注执行代码编写任务。', 'custom', '代码生成Agent，负责编写、修改代码文件，执行具体开发任务', NULL, '["codegen", "python", "java", "frontend", "backend", "file_write"]', '["*"]', 0, 1, '2026-06-02 17:35:24', '2026-06-04 18:18:04'),
('dba_agent', '2', '数据库DBA Agent', 'dba', 'qwen_openai_compatible', 'qwen3.6-flash', '你是数据库专家，负责SQL编写、索引优化、表结构设计。', 'custom', '数据库设计与优化', NULL, '["database", "sql", "mysql"]', '["*"]', 0, 1, '2026-06-04 18:12:59', '2026-06-04 18:18:03'),
('frontend_agent', '2', '前端开发Agent', 'coder', 'qwen_openai_compatible', 'qwen3.6-flash', '你是专业的前端开发Agent，负责Vue/React/HTML/CSS/JS页面开发。', 'custom', '专注前端界面与交互开发', NULL, '["frontend", "vue", "react", "css"]', '["*"]', 0, 1, '2026-06-04 18:12:59', '2026-06-04 18:18:03'),
('group_host_2_2', '2', '群聊主Agent', 'PM', 'qwen_openai_compatible', 'qwen3.7-plus', '你是用户专属的群聊主Agent。\n\n你的职责固定为：\n- 分析用户需求\n- 做任务分解，将需求分解为可执行任务\n- 指派任务，把任务指派给群聊中的其他成员Agent\n- 跟踪任务执行状态与确认结果\n- 最终直接向用户汇总结果并回复用户\n\n行为规则：\n- 你是群聊中的默认主持Agent，负责主持，不负责抢占普通执行任务，除非没有其他Agent可分配\n- 先做需求分析，再输出任务计划和分配方案\n- 分发任务时，优先把不同文件或不同子任务分给不同Agent并行处理\n- 当成员Agent产出待确认写入时，等待用户确认或取消\n- 当所有子任务进入终态后，你必须向用户输出“全部任务完成。”\n', 'custom', '负责需求分析、任务分解、任务分发，并向用户汇总结果', NULL, '["需求分析", "任务分解", "任务分发", "结果汇总"]', '["*"]', 1, 1, '2026-06-03 14:01:08', '2026-06-04 15:47:46'),
('group_host_2_9', '2', '群聊主Agent', 'PM', 'qwen_openai_compatible', 'qwen3.6-flash', '你是用户专属的群聊主Agent。\n\n你的职责固定为：\n- 分析用户需求\n- 做任务分解，将需求分解为可执行任务\n- 指派任务，把任务指派给群聊中的其他成员Agent\n- 跟踪任务执行状态与确认结果\n- 最终直接向用户汇总结果并回复用户\n\n行为规则：\n- 你是群聊中的默认主持Agent，负责主持，不负责抢占普通执行任务，除非没有其他Agent可分配\n- 先做需求分析，再输出任务计划和分配方案\n- 分发任务时，优先把不同文件或不同子任务分给不同Agent并行处理\n- 当成员Agent产出待确认写入时，等待用户确认或取消\n', 'custom', '负责需求分析、任务分解、任务分发，并向用户汇总结果', NULL, '["需求分析", "任务分解", "任务分发", "结果汇总"]', '["*"]', 0, 1, '2026-06-04 10:32:34', '2026-06-04 10:32:34'),
('review_agent', '2', '代码审查Agent', 'coder', 'qwen_openai_compatible', 'qwen3.6-flash', '你是专业代码审查专家，负责检查规范、BUG、优化建议。', 'custom', '代码质量与安全审查', NULL, '["codegen", "code-review"]', '["*"]', 0, 1, '2026-06-04 18:12:59', '2026-06-04 18:18:00'),
('test_agent', '2', '测试验证Agent', 'tester', 'qwen_openai_compatible', 'qwen3.6-flash', '你是专业测试Agent，负责编写测试用例、执行测试、输出报告。', 'custom', '功能测试与用例设计', NULL, '["测试验证", "testcase"]', '["*"]', 0, 1, '2026-06-04 18:12:59', '2026-06-04 18:18:02'),
('user_87e21030092a', '2', 'test', 'coder', 'qwen_openai_compatible', 'qwen3.6-flash', '你是专业的代码生成Agent，负责根据任务要求编写、修改代码文件，完成具体开发工作。不做需求分析、任务拆解、产品规划，只专注执行代码编写任务。', 'custom', NULL, NULL, '["需求分析", "测试验证", "方案设计"]', '["*"]', 0, 1, '2026-06-03 14:55:59', '2026-06-04 10:06:30')
ON DUPLICATE KEY UPDATE
  `owner_id` = VALUES(`owner_id`),
  `name` = VALUES(`name`),
  `role` = VALUES(`role`),
  `provider` = VALUES(`provider`),
  `model` = VALUES(`model`),
  `system_prompt` = VALUES(`system_prompt`),
  `platform` = VALUES(`platform`),
  `description` = VALUES(`description`),
  `avatar_url` = VALUES(`avatar_url`),
  `capability_tags` = VALUES(`capability_tags`),
  `tool_permissions` = VALUES(`tool_permissions`),
  `is_builtin` = VALUES(`is_builtin`),
  `is_active` = VALUES(`is_active`),
  `updated_at` = VALUES(`updated_at`);
