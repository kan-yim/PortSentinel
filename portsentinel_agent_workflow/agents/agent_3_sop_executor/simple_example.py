"""
简单示例：展示Agent 3的输出格式
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "rag_module" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "parsing_module" / "src"))

from agents.agent_3_sop_executor.agent import SopExecutorAgent
from rag_agent.models import EnrichedContext, SopSnippet
from parsing_agent.models import IncidentReport, Entity

# 创建示例incident
incident = IncidentReport(
    incident_id="ALR-861631",
    source_type="Email",
    received_timestamp_utc=datetime.utcnow().isoformat(),
    problem_summary="Customer unable to create vessel advice for LIONCITY07. Error code VESSEL_ERR_4: 'Vessel Name has been used by other vessel advice'.",
    affected_module="Vessel",
    error_code="VESSEL_ERR_4",
    raw_text="Customer reported unable to create vessel advice for LIONCITY07 in VAS. Error code VESSEL_ERR_4.",
    urgency="High",
    entities=[
        Entity(type="VESSEL_NAME", value="LIONCITY07"),
        Entity(type="ERROR_CODE", value="VESSEL_ERR_4")
    ]
)

# 创建示例SOP
sop = SopSnippet(
    content="""Title: VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice

Overview:
Error Code: VESSEL_ERR_4
Module: Vessel Advice Service (VAS)
Description: This error occurs when attempting to create a new vessel advice with a vessel name that is already in use by another active vessel advice record.

Resolution Steps:
1. Query the database to check for active vessel advice with the given system_vessel_name:
   SELECT vessel_advice_no, system_vessel_name, effective_start_datetime, effective_end_datetime
   FROM vessel_advice
   WHERE system_vessel_name = :system_vessel_name
   AND effective_end_datetime IS NULL;

2. Decision Logic:
   - If no active vessel advice found: Escalate to L3 (unusual case)
   - If active vessel advice found:
     a. Check if there are active berth applications linked to this vessel advice:
        SELECT * FROM berth_application
        WHERE vessel_advice_no = :active_vessel_advice_no
        AND status = 'Active';

     b. Decision Logic:
        - If no active berth applications: Safe to expire the vessel advice
          Generate SQL: UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :vessel_advice_no;
        - If active berth applications exist: Cannot expire automatically, escalate to L3

Verification Steps:
- After executing the UPDATE, verify effective_end_datetime is set
- Retry creating the new vessel advice
- Confirm customer can now create vessel advice successfully""",
    metadata={
        "sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",
        "module": "VAS",
        "error_code": "VESSEL_ERR_4",
        "chunk_type": "resolution"
    },
    score=0.92
)

# 创建enriched context
context = EnrichedContext(
    original_report=incident,
    retrieved_sops=[sop],
    retrieval_summary="Retrieved 1 relevant SOP(s) for incident ALR-861631. Top match: VAS: VESSEL_ERR_4 (similarity score: 0.92)"
)

print("=" * 80)
print("Agent 3: SOP Executor - 输出示例")
print("=" * 80)

# 创建agent并执行
print("\n初始化Agent 3...")
agent = SopExecutorAgent(db_interface=None)

print("\n执行SOP...")
print("-" * 80)

try:
    result = agent.execute_sop(context)

    print("\n" + "=" * 80)
    print("执行结果 (ExecutionResult)")
    print("=" * 80)

    # 转换为字典以便查看
    result_dict = result.model_dump()

    # 打印关键信息
    print(f"\n1. 选择的SOP标题:")
    print(f"   {result.selected_sop_title}")

    print(f"\n2. 执行步骤数量: {len(result.executed_steps)}")

    if result.executed_steps:
        print("\n3. 执行步骤详情:")
        for i, step in enumerate(result.executed_steps, 1):
            print(f"\n   步骤 {i}:")
            print(f"   - 描述: {step.step_description[:100]}...")
            print(f"   - 调用的工具: {step.tool_called}")
            print(f"   - 状态: {step.status}")
            print(f"   - 摘要: {step.summary}")
            if step.tool_input:
                print(f"   - 输入参数: {json.dumps(step.tool_input, indent=6, ensure_ascii=False)[:200]}...")
            if step.tool_output:
                output_str = str(step.tool_output)[:200]
                print(f"   - 输出结果: {output_str}...")

    if result.proposed_sql_action:
        print("\n4. 生成的SQL语句 (需要人工审核):")
        print("   " + "-" * 76)
        print("   " + result.proposed_sql_action.replace("\n", "\n   "))
        print("   " + "-" * 76)
    else:
        print("\n4. 生成的SQL语句: 无")

    print(f"\n5. 最终状态: {result.final_status}")

    print(f"\n6. 下一步建议:")
    print(f"   {result.next_action_description}")

    # 保存完整JSON输出
    output_file = "agent_3_output_example.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)

    print(f"\n完整JSON输出已保存到: {output_file}")

    print("\n" + "=" * 80)
    print("JSON输出结构:")
    print("=" * 80)
    print(json.dumps({
        "original_context": {
            "original_report": "...(IncidentReport对象)",
            "retrieved_sops": ["...(SopSnippet对象列表)"],
            "retrieval_summary": "检索摘要文本"
        },
        "selected_sop_title": "选择的SOP标题",
        "executed_steps": [
            {
                "step_description": "步骤描述",
                "tool_called": "工具名称",
                "tool_input": {"参数": "值"},
                "tool_output": "工具输出结果",
                "status": "Success/Failure/Pending Manual Action",
                "summary": "步骤摘要"
            }
        ],
        "proposed_sql_action": "生成的SQL语句(如果有)",
        "next_action_description": "下一步建议",
        "final_status": "Requires Manual Confirmation/Completed Successfully/Failed/Escalation Required"
    }, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"\n执行出错: {str(e)}")
    import traceback
    traceback.print_exc()

    print("\n注意: 如果出现连接错误，请检查Azure OpenAI配置")

print("\n" + "=" * 80)
