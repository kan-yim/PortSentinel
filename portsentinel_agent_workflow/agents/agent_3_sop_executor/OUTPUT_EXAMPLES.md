# Agent 3 输出示例

## 输出数据结构

Agent 3 的输出是一个 **ExecutionResult** 对象，包含以下字段：

```json
{
  "original_context": {
    "original_report": { ... },      // 原始事件报告（来自Agent 1）
    "retrieved_sops": [ ... ],       // 检索到的SOP列表（来自Agent 2）
    "retrieval_summary": "..."       // 检索摘要
  },
  "selected_sop_title": "选择的SOP标题",
  "executed_steps": [ ... ],         // 执行步骤列表
  "proposed_sql_action": "SQL语句",  // 生成的SQL（如果有）
  "next_action_description": "下一步建议",
  "final_status": "最终状态"
}
```

## 完整输出示例

### 场景1: VESSEL_ERR_4 - 需要生成SQL（无活跃泊位申请）

```json
{
  "original_context": {
    "original_report": {
      "incident_id": "ALR-861631",
      "source_type": "Email",
      "received_timestamp_utc": "2025-10-18T10:30:00.000000",
      "urgency": "High",
      "affected_module": "Vessel",
      "error_code": "VESSEL_ERR_4",
      "problem_summary": "Customer unable to create vessel advice for LIONCITY07. Error code VESSEL_ERR_4: 'Vessel Name has been used by other vessel advice'.",
      "entities": [
        {
          "type": "VESSEL_NAME",
          "value": "LIONCITY07"
        },
        {
          "type": "ERROR_CODE",
          "value": "VESSEL_ERR_4"
        }
      ],
      "raw_text": "Customer reported unable to create vessel advice for LIONCITY07..."
    },
    "retrieved_sops": [
      {
        "content": "Title: VAS: VESSEL_ERR_4...\n\nResolution Steps:\n1. Query database...",
        "metadata": {
          "sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",
          "module": "VAS",
          "error_code": "VESSEL_ERR_4"
        },
        "score": 0.92
      }
    ],
    "retrieval_summary": "Retrieved 1 relevant SOP(s) for incident ALR-861631. Top match: VAS: VESSEL_ERR_4 (similarity score: 0.92)"
  },

  "selected_sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",

  "executed_steps": [
    {
      "step_description": "Step 1: Querying for active vessel advice with system_vessel_name=LIONCITY07",
      "tool_called": "execute_sql_query",
      "tool_input": {
        "query": "SELECT vessel_advice_no, system_vessel_name FROM vessel_advice WHERE system_vessel_name = :system_vessel_name AND effective_end_datetime IS NULL",
        "params": "{\"system_vessel_name\": \"LIONCITY07\"}"
      },
      "tool_output": "[{\"vessel_advice_no\": 123, \"system_vessel_name\": \"LIONCITY07\", \"effective_end_datetime\": null}]",
      "status": "Success",
      "summary": "Step 1: Used execute_sql_query"
    },
    {
      "step_description": "Step 2: Checking for active berth applications linked to vessel advice 123",
      "tool_called": "execute_sql_query",
      "tool_input": {
        "query": "SELECT * FROM berth_application WHERE vessel_advice_no = :vessel_advice_no AND status = 'Active'",
        "params": "{\"vessel_advice_no\": 123}"
      },
      "tool_output": "[]",
      "status": "Success",
      "summary": "Step 2: Used execute_sql_query"
    },
    {
      "step_description": "Step 3: Generating SQL to expire vessel advice 123",
      "tool_called": "generate_sql_update_statement",
      "tool_input": {
        "sql_template": "UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :vessel_advice_no",
        "params": "{\"timestamp\": \"2025-10-18 00:00:00\", \"vessel_advice_no\": 123}"
      },
      "tool_output": "UPDATE vessel_advice SET effective_end_datetime = '2025-10-18 00:00:00' WHERE vessel_advice_no = 123;",
      "status": "Pending Manual Action",
      "summary": "Step 3: Generated SQL for manual execution"
    }
  ],

  "proposed_sql_action": "UPDATE vessel_advice SET effective_end_datetime = '2025-10-18 00:00:00' WHERE vessel_advice_no = 123;",

  "next_action_description": "Execute the proposed SQL statement after manual review and approval.",

  "final_status": "Requires Manual Confirmation"
}
```

### 场景2: VESSEL_ERR_4 - 需要升级（有活跃泊位申请）

```json
{
  "original_context": { ... },

  "selected_sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",

  "executed_steps": [
    {
      "step_description": "Step 1: Querying for active vessel advice",
      "tool_called": "execute_sql_query",
      "tool_input": {
        "query": "SELECT vessel_advice_no FROM vessel_advice WHERE system_vessel_name = :system_vessel_name AND effective_end_datetime IS NULL",
        "params": "{\"system_vessel_name\": \"LIONCITY07\"}"
      },
      "tool_output": "[{\"vessel_advice_no\": 123}]",
      "status": "Success",
      "summary": "Step 1: Used execute_sql_query"
    },
    {
      "step_description": "Step 2: Checking for active berth applications",
      "tool_called": "execute_sql_query",
      "tool_input": {
        "query": "SELECT * FROM berth_application WHERE vessel_advice_no = :vessel_advice_no AND status = 'Active'",
        "params": "{\"vessel_advice_no\": 123}"
      },
      "tool_output": "[{\"berth_application_id\": 456, \"vessel_advice_no\": 123, \"status\": \"Active\"}]",
      "status": "Success",
      "summary": "Step 2: Used execute_sql_query"
    }
  ],

  "proposed_sql_action": null,

  "next_action_description": "Escalate to L3 support for further investigation.",

  "final_status": "Escalation Required"
}
```

### 场景3: EDI超时 - 调查完成

```json
{
  "original_context": {
    "original_report": {
      "incident_id": "EDI-001",
      "error_code": "EDI_TIMEOUT",
      "problem_summary": "EDI message processing timeout. EDIFACT message from TP-MAERSK failed to process within 30 seconds.",
      "affected_module": "EDI/API",
      "entities": [
        {
          "type": "PARTNER_ID",
          "value": "TP-MAERSK"
        },
        {
          "type": "ERROR_CODE",
          "value": "EDI_TIMEOUT"
        }
      ]
    },
    "retrieved_sops": [
      {
        "content": "Title: EDI: EDI Message Processing Timeout...",
        "metadata": {
          "sop_title": "EDI: EDI Message Processing Timeout",
          "error_code": "EDI_TIMEOUT"
        }
      }
    ]
  },

  "selected_sop_title": "EDI: EDI Message Processing Timeout",

  "executed_steps": [
    {
      "step_description": "Step 1: Checking EDI service logs for timeout errors",
      "tool_called": "check_log",
      "tool_input": {
        "log_file": "edi_integration_service.log",
        "pattern": "EDI_TIMEOUT"
      },
      "tool_output": "Searched edi_integration_service.log for pattern 'EDI_TIMEOUT'. Found 5 matches in last hour. [Database connection pool exhausted]",
      "status": "Success",
      "summary": "Step 1: Used check_log"
    },
    {
      "step_description": "Step 2: Querying for timeout messages from TP-MAERSK",
      "tool_called": "execute_sql_query",
      "tool_input": {
        "query": "SELECT message_id, partner_id, status, received_at FROM edi_message WHERE partner_id = :partner_id AND status = 'TIMEOUT' ORDER BY received_at DESC LIMIT 5",
        "params": "{\"partner_id\": \"TP-MAERSK\"}"
      },
      "tool_output": "[{\"message_id\": \"MSG001\", \"partner_id\": \"TP-MAERSK\", \"status\": \"TIMEOUT\"}, ...]",
      "status": "Success",
      "summary": "Step 2: Used execute_sql_query"
    }
  ],

  "proposed_sql_action": null,

  "next_action_description": "SOP execution completed successfully. Verify the resolution with the customer.",

  "final_status": "Completed Successfully"
}
```

### 场景4: 没有相关SOP

```json
{
  "original_context": {
    "original_report": {
      "incident_id": "UNKNOWN-001",
      "problem_summary": "Unknown system error",
      "affected_module": "Container"
    },
    "retrieved_sops": [],
    "retrieval_summary": "No relevant SOPs found for incident UNKNOWN-001."
  },

  "selected_sop_title": null,

  "executed_steps": [],

  "proposed_sql_action": null,

  "next_action_description": "No SOPs available for execution. Manual investigation required.",

  "final_status": "Failed"
}
```

## 字段说明

### original_context
- **类型**: EnrichedContext对象
- **说明**: 来自Agent 2的完整上下文，包含原始报告和检索到的SOP

### selected_sop_title
- **类型**: string | null
- **说明**: 被选择执行的SOP标题（选择最高评分的SOP）

### executed_steps
- **类型**: List[StepExecutionDetail]
- **说明**: 按顺序执行的步骤列表

#### StepExecutionDetail字段：
- `step_description`: 步骤的描述
- `tool_called`: 调用的工具名称（check_log / execute_sql_query / generate_sql_update_statement）
- `tool_input`: 传递给工具的参数（字典格式）
- `tool_output`: 工具返回的结果
- `status`: 执行状态
  - "Success" - 成功
  - "Failure" - 失败
  - "Pending Manual Action" - 等待人工操作（生成SQL时）
  - "Skipped" - 跳过
- `summary`: 步骤的简短摘要

### proposed_sql_action
- **类型**: string | null
- **说明**: 为UPDATE/DELETE操作生成的SQL语句
- **重要**: 这些SQL **不会被自动执行**，需要人工审核和确认后手动执行

### next_action_description
- **类型**: string
- **说明**: 对下一步应该采取的行动的建议

### final_status
- **类型**: string
- **可能值**:
  - "Requires Manual Confirmation" - 已生成SQL，需要人工确认执行
  - "Completed Successfully" - SOP执行成功完成
  - "Failed" - 执行失败
  - "Escalation Required" - 需要升级到L3支持
  - "Ambiguous" - 结果不明确

## 如何使用输出

### 1. 检查执行状态
```python
if result.final_status == "Requires Manual Confirmation":
    print(f"请审核并执行以下SQL:\n{result.proposed_sql_action}")
elif result.final_status == "Escalation Required":
    print(f"需要升级: {result.next_action_description}")
elif result.final_status == "Completed Successfully":
    print("SOP执行成功")
```

### 2. 查看执行步骤
```python
for i, step in enumerate(result.executed_steps, 1):
    print(f"步骤 {i}: {step.summary}")
    if step.status == "Failure":
        print(f"  错误: {step.tool_output}")
```

### 3. 提取SQL语句
```python
if result.proposed_sql_action:
    # 将SQL保存到审核队列
    sql_review_queue.add({
        "incident_id": result.original_context.original_report.incident_id,
        "sql": result.proposed_sql_action,
        "reason": result.next_action_description
    })
```

### 4. 保存到文件
```python
import json

with open("execution_result.json", "w") as f:
    json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
```

## 输出文件示例

当运行example_usage.py时，会生成以下文件：

1. **example_1_vessel_err_4_result.json** - VESSEL_ERR_4场景的完整输出
2. **example_2_edi_timeout_result.json** - EDI超时场景的完整输出
3. **example_3_full_workflow_result.json** - 完整工作流（Agent 1→2→3）的输出

## Python代码中访问输出

```python
from agents.agent_3_sop_executor import SopExecutorAgent

# 执行
agent = SopExecutorAgent()
result = agent.execute_sop(enriched_context)

# 访问各个字段
print(f"SOP标题: {result.selected_sop_title}")
print(f"执行了 {len(result.executed_steps)} 个步骤")
print(f"最终状态: {result.final_status}")

# 遍历步骤
for step in result.executed_steps:
    print(f"- {step.summary}")

# 获取SQL
if result.proposed_sql_action:
    print(f"生成的SQL:\n{result.proposed_sql_action}")
```
