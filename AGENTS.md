# AGENTS.md — 深度研搜实战仓库（手写练习田）

## 目录定位

- 本目录是跟随教程《ai-agents-from-zero》实战项目「深度研搜」第 9~14 章**自己动手写代码**的初始项目。

## 项目布局

```shell
shopkeeper-agent/
├─ app/
│  ├─ agent/
│  │  ├─ graph.py # 负责定义langgraph图
│  │  ├─ state.py # 负责定义langgraph状态
│  │  ├─ context.py # 负责定义langgraph运行上下文
│  │  ├─ llm.py # 负责定义llm
│  │  └─ nodes/
│  │     ├─ extract_keywords.py # 负责定义关键词抽取的节点
│  │     ├─ recall_column.py # 负责定义召回字段信息的节点
│  │     ├─ recall_metric.py # 负责定义召回指标信息的节点
│  │     ├─ recall_value.py  # 负责定义召回字段取值的节点
│  │     ├─ merge_retrieved_info.py # 负责定义合并召回信息的节点
│  │     ├─ filter_metric.py # 负责定义过滤指标信息的节点
│  │     ├─ filter_table.py # 负责定义过滤表格信息的节点
│  │     ├─ add_extra_context.py # 负责定义添加额外上下文信息的节点
│  │     ├─ generate_sql.py # 负责定义生成SQL的节点
│  │     ├─ validate_sql.py # 负责定义校验SQL的节点
│  │     ├─ correct_sql.py # 负责定义校正SQL的节点
│  │     └─ execute_sql.py # 负责定义执行SQL的节点
│  │
│  └─ repositories/
│     ├─ mysql/
│     │  ├─ meta/
│     │  │  ├─ meta_mysql_repository.py
│     │  │  └─ mappers/
│     │  │     ├─ table_info_mapper.py
│     │  │     ├─ column_info_mapper.py
│     │  │     ├─ metric_info_mapper.py
│     │  │     └─ column_metric_mapper.py
│     │  └─ dw/
│     │     └─ dw_mysql_repository.py
│     │
│     ├─ qdrant/
│     │  ├─ column_qdrant_repository.py
│     │  └─ metric_qdrant_repository.py
│     │
│     └─ es/
│        └─ value_qdrant_repository.py
│
├─ prompts/
│  ├─ extend_keywords_for_column_recall.prompt # 为召回字段信息扩展关键词 的提示词
│  ├─ extend_keywords_for_metric_recall.prompt # 为召回指标信息扩展关键词 的提示词
│  ├─ extend_keywords_for_value_recall.prompt # 为召回字段取值扩展关键词 的提示词
│  ├─ filter_metric_info.prompt # 过滤指标信息 的提示词
│  ├─ filter_table_info.prompt # 过滤表格信息 的提示词
│  ├─ generate_sql.prompt # 生成SQL 的提示词
│  └─ correct_sql.prompt # 校正SQL 的提示词
│
└─ prompt/
   └─ prompt_loader.py
```

## 目录分工（很重要，AI 助手必须遵守）

| 目录                                                     | 用途                                                                     |
| -------------------------------------------------------- | ------------------------------------------------------------------------ |
| `/Users/duoyun/work/test/deepsearch-agents`（本目录）    | 练习田：跟着教程自己写                                                   |
| `/Users/duoyun/work/test/deepsearch-agents-examples`     | 官方**完整成品**仓库：只作对照参考，**严禁把里面的代码直接复制过来交差** |
| `/Users/duoyun/work/study/study-agent/deepsearch-agents` | 更早的 examples 学习目录（手写示例 1~14 号，对应教程第 1~7 章）          |

- 推荐节奏：学教程某章 → 在本目录 `app/` 下自己实现 → 写完运行验证 → 再与 `deepsearch-agents-examples` 里对应文件对照，检查理解偏差并修正。
- 教程提到「项目对应文件路径 `examples/xx-...`」时，两个目录的 examples 编号一致，可直接对照。

## 注释规范

### 必须写

- 函数、方法、类、接口、结构体、组件：定义上方一行，简短概述功能。
- 形参、关键实参、构造字段：参数后写简短概述。

### 标记

使用的 Better Comments 插件

- `>` 和 `!`。
- `>`：非常重要、易误改、需高亮。
- `!`：禁止、危险、不可违反约束。

### 禁止

- 多行注释块。
- 解释实现过程。
- 复述函数名。
- 滥用 `>` 或 `!`。

### better-comments 提醒

Python 的 `#` 同时是注释符。若配置中存在 `"tag": "#"`，所有 Python 注释会被当成文件级高亮。使用本规范时，从配置中移除 `#` 标签。

### 示例

```python
# 计算订单总价（含税）
def calc_total(items: list[Item], rate: float) -> float: ...

# > 全局单例，禁止在业务代码中重新实例化
settings = Settings()

# ! 必须在事件循环启动前调用
def load_config(path: str) -> None: ...

def calc_total(
    items: list[Item],  # 商品列表
    rate: float,        # 税率，0~1
) -> float: ...

cfg = {
    "addr": "0.0.0.0:8080",  # 监听地址
    "timeout": 5,            # 超时秒数
}
```

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
