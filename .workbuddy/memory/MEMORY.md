# 项目长期记忆（Frappe Builder 中文定制分支）

- 本项目是 Frappe Builder 的**中文定制分支**：核心界面文案已中文化（工具栏/面板/设置/弹窗/仪表盘/属性分区等），AI 支持 OpenRouter 与 OpenAI 兼容两种 provider。
- AI 接入：`builder_settings` 字段 `ai_provider`(openrouter/openai_compatible) + `ai_model` + `ai_api_base`；`builder/ai_page_generator.py` 透传 `api_base` 给 litellm；新增 provider 后需 `bench migrate` 让字段生效。
- 代码约束（来自 AGENTS.md）：Python 无 `_` 前缀 helper、函数约 10 行、避免解释性注释；Vue 优先用 frappe-ui 组件。
- frappe-ui 为 vendored 副本（yarn workspace），非业务代码，勿直接改；与上游同步需谨慎。
- 大文件风险点：builder_page.py(1734 行)、frontend/src/block.ts(1097 行)。
