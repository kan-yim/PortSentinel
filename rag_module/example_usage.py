"""
RAG Agent 使用示例
"""

import json
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "parsing_module" / "src"))

from data_sources.vector_store_interface import VectorStoreInterface
from rag_agent.validator import RagAgent
from parsing_agent.models import IncidentReport, Entity


def example_1_basic_usage():
    """示例 1: 基本使用"""
    print("\n" + "=" * 80)
    print("示例 1: 基本使用 - VESSEL_ERR_4 场景")
    print("=" * 80)

    # 初始化 RAG Agent
    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = RagAgent(vector_store_interface=vector_store)

    # 创建测试报告 - VESSEL_ERR_4 场景
    report = IncidentReport(
        incident_id="ALR-861631",
        source_type="Email",
        received_timestamp_utc="2025-10-18T10:00:00Z",
        urgency="High",
        reported_by="John Doe",
        reported_at="2025-10-18T10:00:00",
        problem_summary="Unable to create vessel advice due to duplicate system vessel name",
        affected_module="Vessel",
        error_code="VESSEL_ERR_4",
        entities=[
            Entity(type="vessel_name", value="LIONCITY07"),
            Entity(type="error_code", value="VESSEL_ERR_4")
        ],
        steps_already_taken=["Checked vessel advice table"],
        additional_notes="Customer needs urgent resolution",
        raw_text="Subject: Unable to create vessel advice\n\nHi support,\n\nI'm getting error VESSEL_ERR_4 when trying to create vessel advice for LIONCITY07. The error says 'System Vessel Name has been used by other vessel advice'. Customer needs urgent resolution.\n\nRegards,\nJohn Doe"
    )

    # 检索相关 SOPs
    enriched = rag_agent.retrieve(report, k=3)

    # 显示结果
    print(f"\n检索到 {len(enriched.retrieved_sops)} 个相关 SOP:")
    for i, sop in enumerate(enriched.retrieved_sops, 1):
        print(f"\n{i}. {sop.metadata.get('sop_title', '未知')}")
        print(f"   模块: {sop.metadata.get('module', '未知')}")
        print(f"   相似度分数: {sop.score:.2f}")
        print(f"   内容预览: {sop.content[:150]}...")

    print(f"\n摘要:\n{enriched.retrieval_summary}")

    return enriched


def example_2_container_issue():
    """示例 2: 容器重复问题"""
    print("\n" + "=" * 80)
    print("示例 2: 容器重复问题")
    print("=" * 80)

    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = RagAgent(vector_store_interface=vector_store)

    report = IncidentReport(
        incident_id="CONT-12345",
        source_type="Email",
        received_timestamp_utc="2025-10-18T11:00:00Z",
        urgency="Medium",
        reported_by="Jane Smith",
        reported_at="2025-10-18T11:00:00",
        problem_summary="Customer seeing duplicate container CMAU0000020 in the system",
        affected_module="Container",
        error_code=None,
        entities=[
            Entity(type="container_number", value="CMAU0000020")
        ],
        steps_already_taken=["Checked container table"],
        additional_notes="",
        raw_text="Subject: Duplicate container issue\n\nCustomer reports seeing container CMAU0000020 appearing twice in the system. Please investigate."
    )

    enriched = rag_agent.retrieve(report, k=3)

    print(f"\n检索到 {len(enriched.retrieved_sops)} 个相关 SOP:")
    for i, sop in enumerate(enriched.retrieved_sops, 1):
        print(f"\n{i}. {sop.metadata.get('sop_title', '未知')} (分数: {sop.score:.2f})")

    print(f"\n摘要:\n{enriched.retrieval_summary}")

    return enriched


def example_3_export_to_json():
    """示例 3: 导出为 JSON"""
    print("\n" + "=" * 80)
    print("示例 3: 导出检索结果为 JSON")
    print("=" * 80)

    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = RagAgent(vector_store_interface=vector_store)

    report = IncidentReport(
        incident_id="EDI-001",
        source_type="SMS",
        received_timestamp_utc="2025-10-18T12:00:00Z",
        urgency="High",
        reported_by="System Monitor",
        reported_at="2025-10-18T12:00:00",
        problem_summary="EDI message stuck in ERROR status, no acknowledgment received",
        affected_module="EDI/API",
        error_code=None,
        entities=[
            Entity(type="correlation_id", value="EDI-MSG-789456")
        ],
        steps_already_taken=[],
        additional_notes="",
        raw_text="Alert: EDI message EDI-MSG-789456 stuck in ERROR status for 2 hours. No acknowledgment received from partner system."
    )

    enriched = rag_agent.retrieve(report, k=2)

    # 导出为 JSON
    output_file = "example_enriched_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enriched.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"\n✓ 检索结果已保存到: {output_file}")
    print(f"  - 原始报告: {enriched.original_report.incident_id}")
    print(f"  - 检索到的 SOP 数量: {len(enriched.retrieved_sops)}")
    print(f"  - 文件大小: {Path(output_file).stat().st_size} bytes")

    return enriched


def example_4_load_from_parsing_module():
    """示例 4: 从 parsing_module 输出加载报告"""
    print("\n" + "=" * 80)
    print("示例 4: 从 Agent 1 输出加载报告")
    print("=" * 80)

    parsed_incidents_path = Path(__file__).parent.parent / "parsing_module" / "parsed_incidents.json"

    if not parsed_incidents_path.exists():
        print(f"❌ 未找到 Agent 1 输出文件: {parsed_incidents_path}")
        print("   请先运行 parsing_module 解析事故报告")
        return None

    # 加载 Agent 1 输出
    with open(parsed_incidents_path, "r", encoding="utf-8") as f:
        parsed_data = json.load(f)

    print(f"✓ 加载了 {len(parsed_data)} 个已解析的报告")

    # 初始化 RAG Agent
    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = RagAgent(vector_store_interface=vector_store)

    # 处理第一个报告
    if parsed_data:
        report_dict = parsed_data[0]["parsed_data"]
        report = IncidentReport(**report_dict)

        print(f"\n处理报告: {report.incident_id}")
        print(f"问题摘要: {report.problem_summary}")

        enriched = rag_agent.retrieve(report, k=3)

        print(f"\n检索到 {len(enriched.retrieved_sops)} 个相关 SOP")
        print(f"摘要: {enriched.retrieval_summary}")

        return enriched


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 28 + "RAG Agent 使用示例" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # 运行示例并收集所有结果
        results = []

        enriched_1 = example_1_basic_usage()
        if enriched_1:
            results.append(enriched_1)

        enriched_2 = example_2_container_issue()
        if enriched_2:
            results.append(enriched_2)

        enriched_3 = example_3_export_to_json()
        if enriched_3:
            results.append(enriched_3)

        enriched_4 = example_4_load_from_parsing_module()
        if enriched_4:
            results.append(enriched_4)

        # 导出所有结果到一个 JSON 文件
        if results:
            print("\n" + "=" * 80)
            print("导出所有结果")
            print("=" * 80)

            all_results_file = "all_enriched_results.json"
            all_results_data = [r.model_dump() for r in results]

            with open(all_results_file, "w", encoding="utf-8") as f:
                json.dump(all_results_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ 所有结果已保存到: {all_results_file}")
            print(f"  - 总共处理了 {len(results)} 个事故报告")
            print(f"  - 文件大小: {Path(all_results_file).stat().st_size} bytes")

        print("\n" + "=" * 80)
        print("所有示例运行完成！")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
