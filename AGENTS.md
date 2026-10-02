# AGENTS.md — 深度研搜实战仓库（手写练习田）

## 目录定位

- 本目录是跟随教程《ai-agents-from-zero》实战项目「深度研搜」第 9~14 章**自己动手写代码**的初始项目。

## 项目布局

```shell
deepsearch-agents/
├── app/                    # 后端业务代码主目录
│   ├── agent/              # 模型初始化、提示词加载、主智能体和子智能体组装逻辑
│   │   ├── llm.py          # 统一创建大模型对象
│   │   ├── prompts.py      # 读取 app/prompt/prompts.yml
│   │   ├── main_agent.py   # 后续章节补充：主智能体组装入口
│   │   └── sub_agents/     # 后续章节补充：网络、数据库、RAGFlow 子智能体
│   ├── api/                # FastAPI、WebSocket、上下文隔离和执行过程监控相关代码
│   │   ├── context.py      # 保存 thread_id 和 session_dir 上下文
│   │   ├── monitor.py      # 推送工具调用、助手调用和任务结果
│   │   └── server.py       # 后续章节补充：FastAPI 服务入口
│   ├── prompt/             # YAML 提示词配置，让提示词和 Python 逻辑分开维护
│   │   └── prompts.yml     # 主智能体和子智能体提示词配置
│   ├── tools/              # 后续章节补充：Agent 可调用工具，例如搜索、查库、生成文件
│   └── utils/              # 普通 Python 工具函数，给后端代码或 Agent Tool 内部调用
│       ├── path_utils.py   # 统一解析上传文件、输出文件和会话目录路径
│       └── word_converter.py # Markdown 转 PDF 的底层转换工具
├── examples/               # 前面章节学习 DeepAgents API 时用到的示例代码
├── output/                 # 运行时生成：存放 Markdown、PDF 等任务产物
├── updated/                # 运行时生成：存放用户上传文件
├── .env.example            # 环境变量示例
├── .env                    # 本地真实配置，不提交仓库
├── .python-version         # Python 版本提示
├── pyproject.toml          # 项目依赖声明
└── uv.lock                 # 依赖锁定文件
```

## 目录分工（很重要，AI 助手必须遵守）

| 目录                                                     | 用途                                                                     |
| -------------------------------------------------------- | ------------------------------------------------------------------------ |
| `/Users/duoyun/work/test/deepsearch-agents`（本目录）    | 练习田：跟着教程自己写                                                   |
| `/Users/duoyun/work/test/deepsearch-agents-examples`     | 官方**完整成品**仓库：只作对照参考，**严禁把里面的代码直接复制过来交差** |
| `/Users/duoyun/work/study/study-agent/deepsearch-agents` | 更早的 examples 学习目录（手写示例 1~14 号，对应教程第 1~7 章）          |

- 推荐节奏：学教程某章 → 在本目录 `app/` 下自己实现 → 写完运行验证 → 再与 `deepsearch-agents-examples` 里对应文件对照，检查理解偏差并修正。
- 教程提到「项目对应文件路径 `examples/xx-...`」时，两个目录的 examples 编号一致，可直接对照。

## 教学文档

- 本地原文优先：/Users/duoyun/work/study/study-agent/ai-agents-from-zero/
- 本项目章节：实战项目-电商问数/；命名 章节号-标题.md；大纲 \_sidebar.md

### 示例

- 函数 / 方法 / 类 → 用 **docstring**（`"""..."""`），单行即可。
- 变量 / 常量 → 紧贴上方写 `#` 注释，Pylance 悬停会显示。
- 形参 / 字段 → 行内 `#` 注释，悬停不显示，只用于阅读。

```python
# 计算订单总价（含税）
def calc_total(items: list[Item], rate: float) -> float:
    """计算订单总价（含税）。"""  # ← 悬停看这条
    ...


# > 全局单例，禁止在业务代码中重新实例化
settings = Settings()  # ← 悬停看上面那行注释


class Order:
    """订单实体。"""  # ← 悬停看这条

    def pay(self, amount: float) -> bool:
        """发起支付，返回是否成功。"""
        ...


# ! 必须在事件循环启动前调用
def load_config(path: str) -> None:
    """加载配置文件。"""
    ...
```

函数多参数时：

```python
def calc_total(
    items: list[Item],  # 商品列表
    rate: float,  # 税率，0~1
) -> float:
    """计算订单总价（含税）。"""
    ...


cfg = {
    "addr": "0.0.0.0:8080",  # 监听地址
    "timeout": 5,  # 超时秒数
}
```

### better-comments 提醒

Python 的 `#` 同时是注释符。若配置中存在 `"tag": "#"`，所有 Python 注释会被当成文件级高亮。使用本规范时，从配置中移除 `#` 标签。

## 工程纪律

- 不确定时：多读代码；仍然无法解决时，提供简短的选项后提问。绝不猜测。
- 修复根因（而非表面修补）。
- 聚焦变更；避免无关重构。
- 行为或用法变更时，同步更新文档和测试。
- 绝不通过删除、跳过或注释掉测试来使其通过；修复底层代码。
- AGENTS.md 的编写规则
  1. **简单明了**：只写 Agent 猜不到的信息，不写通用编程常识。
  2. **空白优于猜测**：不确定的内容宁可留空，也不要用模糊表述填充。
  3. **具体优于宽泛**：用确切的命令、路径、规则，替代需要 Agent 猜测的描述。
