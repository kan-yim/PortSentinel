"""
Agent 3 示例：连接真实数据库

这个示例展示如何将Agent 3连接到MySQL appdb数据库并执行真实的查询。
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "rag_module" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "parsing_module" / "src"))

from agents.agent_3_sop_executor.agent import SopExecutorAgent
from agents.agent_3_sop_executor.database_interface import DatabaseInterface
from rag_agent.models import EnrichedContext, SopSnippet
from parsing_agent.models import IncidentReport, Entity


def main():
    print("=" * 80)
    print("Agent 3: SOP Executor - 数据库连接示例")
    print("=" * 80)

    # 步骤1: 获取MySQL密码
    password = os.getenv("MYSQL_ROOT_PASSWORD")
    if not password:
        print("\n请输入MySQL root密码（或设置MYSQL_ROOT_PASSWORD环境变量）:")
        password = input("Password: ")

    # 步骤2: 初始化数据库接口
    print("\n[1] 连接到MySQL appdb数据库...")
    try:
        db = DatabaseInterface(
            host="localhost",
            port=3306,
            database="appdb",
            user="root",
            password=password
        )
        print("    ✓ 数据库连接成功")

        # 测试连接
        test_result = db.test_query()
        print(f"    ✓ 当前数据库: {test_result.get('database')}")
        print(f"    ✓ 服务器时间: {test_result.get('server_time')}")

        # 列出表
        tables = db.list_tables()
        print(f"    ✓ 找到 {len(tables)} 个表")

    except Exception as e:
        print(f"    ✗ 数据库连接失败: {str(e)}")
        print("\n请确保:")
        print("  1. MySQL 正在运行")
        print("  2. appdb 数据库已导入")
        print("  3. 密码正确")
        return

    # 步骤3: 创建示例incident
    print("\n[2] 创建测试事件...")
    incident = IncidentReport(
        incident_id="TEST-DB-001",
        source_type="Email",
        received_timestamp_utc=datetime.utcnow().isoformat(),
        problem_summary="Testing database connectivity with vessel advice query",
        affected_module="Vessel",
        error_code="VESSEL_ERR_4",
        raw_text="Test incident for database connectivity",
        urgency="Low",
        entities=[
            Entity(type="ERROR_CODE", value="VESSEL_ERR_4")
        ]
    )
    print(f"    ✓ 事件ID: {incident.incident_id}")

    # 步骤4: 创建SOP
    print("\n[3] 准备SOP...")
    sop = SopSnippet(
        content="""Title: Database Connectivity Test

Resolution Steps:
1. Query the vessel_advice table to verify database access
2. List first 5 vessel advice records
3. Verify query results are returned correctly

This is a test SOP to verify database connectivity.""",
        metadata={
            "sop_title": "Database Connectivity Test",
            "module": "Vessel",
            "test": True
        },
        score=1.0
    )
    print(f"    ✓ SOP: {sop.metadata['sop_title']}")

    # 步骤5: 创建enriched context
    context = EnrichedContext(
        original_report=incident,
        retrieved_sops=[sop],
        retrieval_summary="Test SOP for database connectivity"
    )

    # 步骤6: 创建Agent 3并连接数据库
    print("\n[4] 初始化Agent 3（连接数据库）...")
    agent = SopExecutorAgent(db_interface=db)
    print("    ✓ Agent 3 已初始化，数据库已连接")

    # 步骤7: 测试数据库查询（不通过agent）
    print("\n[5] 测试直接数据库查询...")
    try:
        test_query = "SELECT vessel_advice_no, system_vessel_name FROM vessel_advice LIMIT 3"
        results = db.execute_select(test_query)
        print(f"    ✓ 成功查询到 {len(results)} 条记录:")
        for row in results:
            print(f"      - Vessel {row['vessel_advice_no']}: {row.get('system_vessel_name', 'N/A')}")
    except Exception as e:
        print(f"    ✗ 查询失败: {str(e)}")

    # 步骤8: 通过Agent执行SOP（这次有真实数据库）
    print("\n[6] 通过Agent 3执行SOP（使用真实数据库）...")
    print("-" * 80)

    try:
        result = agent.execute_sop(context)

        print("\n" + "=" * 80)
        print("执行结果")
        print("=" * 80)

        print(f"\n✓ 选择的SOP: {result.selected_sop_title}")
        print(f"✓ 执行步骤数: {len(result.executed_steps)}")
        print(f"✓ 最终状态: {result.final_status}")

        if result.executed_steps:
            print("\n执行步骤详情:")
            for i, step in enumerate(result.executed_steps, 1):
                print(f"\n  步骤 {i}:")
                print(f"    工具: {step.tool_called}")
                print(f"    状态: {step.status}")
                print(f"    摘要: {step.summary}")

                if step.tool_output:
                    output_preview = str(step.tool_output)[:200]
                    print(f"    输出: {output_preview}...")

        if result.proposed_sql_action:
            print("\n生成的SQL:")
            print("  " + result.proposed_sql_action)

        print(f"\n下一步建议:")
        print(f"  {result.next_action_description}")

        # 保存结果
        output_file = "database_test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"\n✓ 完整结果已保存到: {output_file}")

    except Exception as e:
        print(f"\n✗ 执行出错: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def test_database_only():
    """仅测试数据库连接，不运行Agent"""
    print("=" * 80)
    print("数据库连接测试")
    print("=" * 80)

    password = os.getenv("MYSQL_ROOT_PASSWORD")
    if not password:
        password = input("\nMySQL root密码: ")

    try:
        print("\n连接数据库...")
        db = DatabaseInterface(
            host="localhost",
            port=3306,
            database="appdb",
            user="root",
            password=password
        )

        print("✓ 连接成功\n")

        # 测试1: 基本查询
        print("测试1: 列出表...")
        tables = db.list_tables()
        print(f"✓ 找到 {len(tables)} 个表:")
        for table in tables[:10]:  # 只显示前10个
            print(f"  - {table}")
        if len(tables) > 10:
            print(f"  ... 还有 {len(tables) - 10} 个表")

        # 测试2: vessel_advice查询
        print("\n测试2: 查询vessel_advice表...")
        results = db.execute_select(
            "SELECT vessel_advice_no, system_vessel_name, effective_end_datetime FROM vessel_advice LIMIT 5"
        )
        print(f"✓ 查询成功，返回 {len(results)} 条记录:")
        for row in results:
            status = "Active" if row.get('effective_end_datetime') is None else "Expired"
            print(f"  - ID {row['vessel_advice_no']}: {row.get('system_vessel_name', 'N/A')} [{status}]")

        # 测试3: 带参数的查询
        if results:
            print("\n测试3: 带参数的查询...")
            test_vessel = results[0]['system_vessel_name']
            param_results = db.execute_select(
                "SELECT * FROM vessel_advice WHERE system_vessel_name = :name",
                {"name": test_vessel}
            )
            print(f"✓ 查询 system_vessel_name='{test_vessel}': 找到 {len(param_results)} 条记录")

        print("\n" + "=" * 80)
        print("✓ 所有测试通过！数据库工作正常。")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--db-only":
        # 只测试数据库
        test_database_only()
    else:
        # 完整测试（包括Agent）
        main()
