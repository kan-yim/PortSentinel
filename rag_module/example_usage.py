"""
RAG Agent 使用示例 - 修复版本
"""

import json
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "parsing_module" / "src"))

from data_sources.vector_store_interface import VectorStoreInterface
from rag_agent.validator import HybridRagAgent
from parsing_agent.models import IncidentReport, Entity


def example_1_basic_usage():
    """示例 1: 基本使用"""
    print("\n" + "=" * 80)
    print("示例 1: 基本使用 - VESSEL_ERR_4 场景")
    print("=" * 80)

    # 初始化 RAG Agent
    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = HybridRagAgent(
        vector_store_interface=vector_store,
        use_llm=False
    )

    # 创建测试报告
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
        raw_text="Subject: Unable to create vessel advice\n\nError VESSEL_ERR_4..."
    )

    # 检索相关 SOPs
    enriched = rag_agent.retrieve(report, final_top_k=3)

    # ✅ 安全处理可能为 None 的字段
    print(f"\n检索到 {len(enriched.retrieved_sops)} 个相关 SOP:")
    for i, sop in enumerate(enriched.retrieved_sops, 1):
        print(f"\n{'=' * 80}")
        print(f"SOP #{i}")
        print(f"{'=' * 80}")
        print(f"标题: {sop.get('Title', '未知')}")
        print(f"模块: {sop.get('Module', '未知')}")
        
        # 安全获取字段，处理 None 值
        overview = sop.get('Overview') or '无'
        resolution = sop.get('Resolution') or '无'
        verification = sop.get('Verification') or '无'
        preconditions = sop.get('Preconditions') or '无'
        
        print(f"\n概述:")
        print(f"{overview[:300]}...")
        
        print(f"\n前置条件:")
        print(f"{preconditions[:200]}...")
        
        print(f"\n解决方案:")
        print(f"{resolution[:300]}...")
        
        print(f"\n验证步骤:")
        print(f"{verification[:200]}...")

    print(f"\n{'=' * 80}")
    print(f"检索摘要")
    print(f"{'=' * 80}")
    print(enriched.retrieval_summary)
    
    # 显示查询变体
    print(f"\n{'=' * 80}")
    print(f"生成的查询变体")
    print(f"{'=' * 80}")
    for i, query in enumerate(enriched.expanded_queries, 1):
        print(f"{i}. {query}")
    
    # 显示检索指标
    if enriched.retrieval_metrics:
        print(f"\n{'=' * 80}")
        print(f"检索指标")
        print(f"{'=' * 80}")
        metrics = enriched.retrieval_metrics
        print(f"查询变体数量: {metrics.num_expanded_queries}")
        print(f"BM25 候选数量: {metrics.num_bm25_candidates}")
        print(f"向量候选数量: {metrics.num_vector_candidates}")
        print(f"合并后候选数: {metrics.num_merged_candidates}")
        print(f"RRF 后保留数: {metrics.num_after_rrf}")
        print(f"最终结果数量: {metrics.num_final_results}")
        print(f"BM25 权重: {metrics.bm25_weight}")
        print(f"向量权重: {metrics.vector_weight}")
        print(f"RRF 参数 k: {metrics.rrf_k}")

    return enriched


def example_2_container_issue():
    """示例 2: 容器范围错误"""
    print("\n" + "=" * 80)
    print("示例 2: 容器范围错误")
    print("=" * 80)

    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = HybridRagAgent(
        vector_store_interface=vector_store,
        use_llm=False
    )

    report = IncidentReport(
        incident_id="CONT-001",
        source_type="Email",
        received_timestamp_utc="2025-10-18T11:00:00Z",
        urgency="Medium",
        reported_by="Jane Smith",
        reported_at="2025-10-18T11:00:00",
        problem_summary="Trying to create Container Range but hit with overlapping error",
        affected_module="Container",
        error_code=None,
        entities=[
            Entity(type="container_number", value="BSIU323099")
        ],
        steps_already_taken=[],
        additional_notes="",
        raw_text="Error: Overlapping container range(s) found..."
    )

    enriched = rag_agent.retrieve(report, final_top_k=3)

    print(f"\n检索到 {len(enriched.retrieved_sops)} 个相关 SOP:")
    for i, sop in enumerate(enriched.retrieved_sops, 1):
        print(f"\n{i}. {sop.get('Title', '未知')[:70]}...")
        print(f"   模块: {sop.get('Module', '未知')}")

    print(f"\n摘要:\n{enriched.retrieval_summary}")

    return enriched


def example_3_export_to_json():
    """示例 3: 导出完整 JSON"""
    print("\n" + "=" * 80)
    print("示例 3: 导出为完整 JSON 格式")
    print("=" * 80)

    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    rag_agent = HybridRagAgent(
        vector_store_interface=vector_store,
        use_llm=False
    )

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
        raw_text="Alert: EDI message EDI-MSG-789456 stuck in ERROR..."
    )

    enriched = rag_agent.retrieve(report, final_top_k=3)

    # 导出为 JSON
    output_file = "hybrid_rag_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enriched.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"\n✓ 结果已保存到: {output_file}")
    print(f"  - 事故 ID: {enriched.original_report.incident_id}")
    print(f"  - 检索到的 SOP 数量: {len(enriched.retrieved_sops)}")
    
    # 显示第一个 SOP 的完整 JSON
    if enriched.retrieved_sops:
        print(f"\n第一个 SOP 的完整 JSON 结构:")
        print(json.dumps(enriched.retrieved_sops[0], indent=2, ensure_ascii=False))

    return enriched


def example_4_compare_methods():
    """示例 4: 对比不同权重配置"""
    print("\n" + "=" * 80)
    print("示例 4: 对比不同权重配置的检索效果")
    print("=" * 80)

    vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
    
    report = IncidentReport(
        incident_id="TEST-001",
        source_type="Email",
        received_timestamp_utc="2025-10-18T13:00:00Z",
        urgency="Medium",
        reported_by="Test User",
        reported_at="2025-10-18T13:00:00",
        problem_summary="Duplicate container CMAU0000020 in system",
        affected_module="Container",
        error_code=None,
        entities=[
            Entity(type="container_number", value="CMAU0000020")
        ],
        steps_already_taken=[],
        additional_notes="",
        raw_text="Customer seeing duplicate container..."
    )

    # 配置 1: 偏重 BM25
    print("\n[配置 1] BM25 权重: 0.7, 向量权重: 0.3")
    agent1 = HybridRagAgent(
        vector_store_interface=vector_store,
        bm25_weight=0.7,
        vector_weight=0.3,
        use_llm=False
    )
    enriched1 = agent1.retrieve(report, final_top_k=3)
    print(f"Top 1: {enriched1.retrieved_sops[0].get('Title', 'N/A')[:60]}...")

    # 配置 2: 偏重向量
    print("\n[配置 2] BM25 权重: 0.3, 向量权重: 0.7")
    agent2 = HybridRagAgent(
        vector_store_interface=vector_store,
        bm25_weight=0.3,
        vector_weight=0.7,
        use_llm=False
    )
    enriched2 = agent2.retrieve(report, final_top_k=3)
    print(f"Top 1: {enriched2.retrieved_sops[0].get('Title', 'N/A')[:60]}...")

    # 配置 3: 平衡
    print("\n[配置 3] BM25 权重: 0.5, 向量权重: 0.5")
    agent3 = HybridRagAgent(
        vector_store_interface=vector_store,
        bm25_weight=0.5,
        vector_weight=0.5,
        use_llm=False
    )
    enriched3 = agent3.retrieve(report, final_top_k=3)
    print(f"Top 1: {enriched3.retrieved_sops[0].get('Title', 'N/A')[:60]}...")


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "混合检索 RAG Agent 示例" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # 示例 1: 基本使用
        enriched_1 = example_1_basic_usage()

        # 示例 2: 容器问题
        enriched_2 = example_2_container_issue()

        # 示例 3: 导出 JSON
        enriched_3 = example_3_export_to_json()

        # 示例 4: 对比配置
        example_4_compare_methods()

        # 导出所有结果
        all_results = [enriched_1, enriched_2, enriched_3]
        
        with open("all_hybrid_results.json", "w", encoding="utf-8") as f:
            json.dump(
                [r.model_dump() for r in all_results],
                f,
                indent=2,
                ensure_ascii=False
            )

        print("\n" + "=" * 80)
        print("✓ 所有示例运行完成！")
        print("=" * 80)
        print(f"\n输出文件:")
        print(f"  - hybrid_rag_output.json (单个示例)")
        print(f"  - all_hybrid_results.json (所有结果)")
        print()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()