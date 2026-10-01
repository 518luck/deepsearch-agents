# AGENTS.md — 深度研搜实战仓库（手写练习田）

## 目录定位

- 本目录是跟随教程《ai-agents-from-zero》实战项目「深度研搜」第 9~14 章**自己动手写代码**的初始项目。
- 当前状态 = 官方仓库教程第 8 章「项目总览与工程初始化」时点（commit `d6ddfb5`）：只有根配置文件（pyproject.toml / requirements.txt / uv.lock / .env.example 等）+ `examples/`（17 个官方学习示例）。
- **没有 `app/` 目录**——教程 5.2 的目录图是规划图，`app/` 下的代码（llm.py、prompts.py、context.py、monitor.py、子智能体、主智能体、server 等）需要按教程第 9 章开始逐章自己创建。

## 目录分工（很重要，AI 助手必须遵守）

| 目录 | 用途 |
|---|---|
| `/Users/duoyun/work/test/deepsearch-agents`（本目录） | 练习田：跟着教程自己写 |
| `/Users/duoyun/work/test/deepsearch-agents-examples` | 官方**完整成品**仓库：只作对照参考，**严禁把里面的代码直接复制过来交差** |
| `/Users/duoyun/work/study/study-agent/deepsearch-agents` | 更早的 examples 学习目录（手写示例 1~14 号，对应教程第 1~7 章） |

- 推荐节奏：学教程某章 → 在本目录 `app/` 下自己实现 → 写完运行验证 → 再与 `deepsearch-agents-examples` 里对应文件对照，检查理解偏差并修正。
- 教程提到「项目对应文件路径 `examples/xx-...`」时，两个目录的 examples 编号一致，可直接对照。

## 环境备忘

- Python 3.12，uv 管理依赖（.venv 已按第 8 章时点的 pyproject.toml 同步）。
- 后续章节需要新依赖（如 fastapi、ragflow-sdk、mysql-connector-python 等）时，按教程用 `uv add xxx` 或 `uv add -r requirements.txt` 安装，**不要用 pip install**。
- `.env` 尚未创建：按教程第 9 章 `cp .env.example .env` 后填真实值。变量名为 `OPENAI_BASE_URL` / `LLM_QWEN_MAX` / `TAVILY_API_KEY` / `RAGFLOW_API_URL` / `RAGFLOW_API_KEY` / `MYSQL_*` 这套，**与 study 学习目录的变量名（LLM_MODEL 等）不同，不要直接拷贝**。

## 代码交付规范

- 写完或修改任何代码后必须运行验证（在本目录用 `uv run ...`），报错修复后再交付，不夸大"已验证"。
- 文件路径与命名严格跟教程（如 `app/agent/llm.py`、`app/prompt/prompts.yml`），保持与教程、参考答案三方可比对。
- 每完成一章，在下方「练习进度」追加一行记录。

## 练习进度

- 未开始。下一章：教程第 9 章「基础模块与模型配置」（.env、context.py、monitor.py、path_utils.py、word_converter.py、llm.py、prompts.yml）。
