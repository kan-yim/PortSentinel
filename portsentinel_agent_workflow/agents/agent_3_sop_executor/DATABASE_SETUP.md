# Agent 3 数据库设置说明

## 概述

Agent 3 的"数据库不可用"不是错误，而是**设计上的占位符**。这份文档解释了数据库连接的完整设置。

## 🎯 涉及的数据库

**数据库名称**: `appdb` (不是 portnet)

**位置**: MySQL 在 localhost:3306

**表结构**:
- `vessel_advice` - 船舶建议表
- `berth_application` - 泊位申请表
- `edi_message` - EDI消息表
- `container` - 集装箱表
- `vessel` - 船舶表
- 等等...

这是您之前用以下脚本导入的数据库：
```bash
/Users/kanyim/portsentinel/Database/import_database.sh
```

## 📊 当前实现状态

### ✅ 已完成

1. **Agent 3 核心代码** (`agent.py`)
   - LangChain agent 执行逻辑
   - 工具集成
   - 结果处理

2. **工具定义** (`tools.py`)
   - `check_log` - 检查日志
   - `execute_sql_query` - 执行SELECT查询（骨架）
   - `generate_sql_update_statement` - 生成SQL语句

3. **数据库接口** (`database_interface.py`) ⭐ **新增**
   - MySQL连接管理
   - 参数化查询
   - 结果JSON序列化
   - 错误处理

### ⏳ 当前状态

**没有数据库连接时**:
```python
agent = SopExecutorAgent(db_interface=None)
```

工具 `execute_sql_query` 返回：
```json
{
  "error": "Database interface not available",
  "note": "This is a mock response. In production, provide a DatabaseInterface instance."
}
```

这导致：
- `status`: "Failure"
- `final_status`: "Failed"

**这是预期行为！**

## 🔧 如何连接真实数据库

### 步骤1: 测试数据库连接

```bash
cd /Users/kanyim/portsentinel/portsentinel_agent_workflow/agents/agent_3_sop_executor

# 设置密码（可选）
export MYSQL_ROOT_PASSWORD='your_password'

# 测试数据库接口
python database_interface.py
```

**期望输出**:
```
================================================================================
Database Interface Test
================================================================================

Connecting to database...
✓ Connected successfully

Testing connection...
✓ Database: appdb
✓ Server time: 2025-10-18 14:30:00

Listing tables...
✓ Found 15 tables:
  - berth_application
  - container
  - edi_message
  - vessel
  - vessel_advice
  ...

✓ All tests passed! Database interface is ready.
```

### 步骤2: 使用Agent 3连接数据库

#### 方法A: 仅测试数据库（不运行Agent）

```bash
python example_with_database.py --db-only
```

这会：
- 连接到appdb数据库
- 列出所有表
- 查询vessel_advice表
- 测试参数化查询

#### 方法B: 运行完整Agent（连接数据库）

```bash
python example_with_database.py
```

这会：
1. 连接数据库
2. 初始化Agent 3
3. 执行SOP（使用真实数据库查询）
4. 显示执行结果
5. 保存到 `database_test_result.json`

### 步骤3: 在代码中使用

```python
from agents.agent_3_sop_executor.agent import SopExecutorAgent
from agents.agent_3_sop_executor.database_interface import DatabaseInterface

# 创建数据库接口
db = DatabaseInterface(
    host="localhost",
    port=3306,
    database="appdb",
    user="root",
    password="your_password"
)

# 创建Agent（连接数据库）
agent = SopExecutorAgent(db_interface=db)

# 执行SOP
result = agent.execute_sop(enriched_context)

# 现在 execute_sql_query 会返回真实数据！
```

## 📝 代码变化说明

### agent.py 的变化

**之前** (第94-101行):
```python
# Execute query using database interface
# This would call something like: db_interface.execute_query(query, params_dict)
# For now, return a placeholder
return json.dumps({
    "status": "success",
    "note": "Database interface connected but implementation pending",
    "query": query,
    "params": params_dict
})
```

**现在** (第94行):
```python
# Execute query using database interface
return self.db_interface.execute_select_json(query, params_dict)
```

现在会调用真实的数据库查询！

## 🔍 工作原理

### 不连接数据库时（db_interface=None）

```
Agent 3
  │
  ├─> execute_sql_query 工具
  │     │
  │     └─> 检查: self.db_interface is None?
  │           │
  │           └─> 是 → 返回 "Database interface not available"
  │
  └─> 步骤状态: Failure
      最终状态: Failed
```

### 连接数据库时（db_interface=DatabaseInterface(...)）

```
Agent 3
  │
  ├─> execute_sql_query 工具
  │     │
  │     └─> 检查: self.db_interface is None?
  │           │
  │           └─> 否 → 调用 db.execute_select_json(query, params)
  │                      │
  │                      ├─> 连接MySQL
  │                      ├─> 执行查询
  │                      └─> 返回JSON结果
  │
  └─> 步骤状态: Success
      最终状态: Requires Manual Confirmation / Completed Successfully
```

## 🧪 测试场景

### 场景1: 查询vessel_advice表

```python
# Agent会执行这样的查询
query = """
SELECT vessel_advice_no, system_vessel_name, effective_end_datetime
FROM vessel_advice
WHERE system_vessel_name = :name
AND effective_end_datetime IS NULL
"""
params = {"name": "LIONCITY07"}
```

**返回示例**:
```json
[
  {
    "vessel_advice_no": 123,
    "system_vessel_name": "LIONCITY07",
    "effective_end_datetime": null
  }
]
```

### 场景2: 检查berth_application

```python
query = """
SELECT *
FROM berth_application
WHERE vessel_advice_no = :id
AND status = 'Active'
"""
params = {"id": 123}
```

## ⚠️ 重要提示

### 安全性

1. **只读查询**: `execute_sql_query` 只能执行 SELECT 查询
2. **参数化查询**: 使用命名参数防止SQL注入
3. **UPDATE/DELETE**: 通过 `generate_sql_update_statement` 生成，**不会执行**

### DatabaseInterface 的限制

```python
def execute_select(self, query: str, params: dict):
    # 验证是SELECT查询
    if not query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    ...
```

### 连接管理

- 使用上下文管理器自动关闭连接
- 每次查询创建新连接（无连接池）
- 可以扩展为使用连接池

## 📂 相关文件

```
agents/agent_3_sop_executor/
├── agent.py                      # 主Agent类（使用db_interface）
├── tools.py                      # 工具定义
├── database_interface.py         # 数据库接口 ⭐ 新增
├── example_with_database.py      # 数据库示例 ⭐ 新增
├── simple_example.py             # 简单示例（无数据库）
└── DATABASE_SETUP.md             # 本文档 ⭐ 新增
```

## 🚀 快速开始

```bash
# 1. 确保MySQL运行中
brew services list | grep mysql

# 2. 测试数据库连接
export MYSQL_ROOT_PASSWORD='your_password'
cd agents/agent_3_sop_executor
python database_interface.py

# 3. 运行Agent 3（连接数据库）
python example_with_database.py

# 4. 查看结果
cat database_test_result.json
```

## ❓ 常见问题

### Q1: 为什么之前显示"Database interface not available"？

**A**: 因为我们传入了 `db_interface=None`。这是占位符行为，不是错误。

### Q2: 现在还会显示这个错误吗？

**A**: 如果您传入真实的 DatabaseInterface 实例，就不会了。工具会执行真实查询。

### Q3: 我必须连接数据库才能测试Agent 3吗？

**A**: 不必须。测试用例（`test_agent_3_simple.py`）可以在没有数据库的情况下运行。但要看到完整功能，需要连接数据库。

### Q4: 数据库密码存放在哪里？

**A**:
- 方法1: 环境变量 `export MYSQL_ROOT_PASSWORD='password'`
- 方法2: 代码中传入（不推荐提交到git）
- 方法3: 从 .env 文件加载

### Q5: 如何在生产环境使用？

**A**:
```python
# 生产环境
from agents.agent_3_sop_executor.agent import SopExecutorAgent
from agents.agent_3_sop_executor.database_interface import DatabaseInterface
import os

db = DatabaseInterface(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    database=os.getenv("DB_NAME", "appdb"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD")
)

agent = SopExecutorAgent(db_interface=db)
```

## 📈 下一步

1. ✅ 测试数据库连接
2. ✅ 运行 `example_with_database.py`
3. ⏳ 根据实际数据调整SOP查询
4. ⏳ 添加更多测试用例
5. ⏳ 实现日志查询（check_log工具）
6. ⏳ 集成到完整工作流（Agent 1 → 2 → 3）
