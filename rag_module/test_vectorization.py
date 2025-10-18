"""
测试向量化后的知识库检索

验证 Chroma 向量数据库是否正确创建，并测试检索功能。
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_sources.vector_store_interface import VectorStoreInterface

load_dotenv()


def test_basic_search():
    """测试基本检索功能"""
    print("=" * 80)
    print("测试 1: 基本语义搜索")
    print("=" * 80)

    try:
        # 初始化向量存储
        vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
        print("✓ 向量存储初始化成功")

        # 测试查询
        test_queries = [
            "VESSEL_ERR_4",
            "duplicate container",
            "EDI message timeout",
            "container range error"
        ]

        for query in test_queries:
            print(f"\n查询: '{query}'")
            print("-" * 40)

            results = vector_store.search_knowledge_base(query, k=3)

            for i, doc in enumerate(results, 1):
                print(f"\n  结果 {i}:")
                print(f"    标题: {doc.metadata.get('sop_title', 'Unknown')}")
                print(f"    模块: {doc.metadata.get('module', 'Unknown')}")
                print(f"    类型: {doc.metadata.get('chunk_type', 'Unknown')}")
                print(f"    内容预览: {doc.page_content[:100]}...")

    except FileNotFoundError:
        print("✗ 错误: db_chroma_kb 目录不存在")
        print("  请先运行: python vectorize_knowledge_base.py")
    except Exception as e:
        print(f"✗ 错误: {e}")


def test_search_with_scores():
    """测试带相似度分数的检索"""
    print("\n" + "=" * 80)
    print("测试 2: 带相似度分数的检索")
    print("=" * 80)

    try:
        vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")

        query = "customer portal shows wrong container status"
        print(f"\n查询: '{query}'")
        print("-" * 40)

        docs_and_scores = vector_store.search_with_scores(query, k=5)

        for i, (doc, score) in enumerate(docs_and_scores, 1):
            print(f"\n  结果 {i} (相似度: {score:.4f}):")
            print(f"    标题: {doc.metadata.get('sop_title', 'Unknown')[:60]}...")
            print(f"    模块: {doc.metadata.get('module', 'Unknown')}")

    except Exception as e:
        print(f"✗ 错误: {e}")


def test_metadata_filtering():
    """测试元数据过滤"""
    print("\n" + "=" * 80)
    print("测试 3: 元数据过滤 (按模块)")
    print("=" * 80)

    try:
        vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")

        modules = ["Container", "Vessel", "EDI/API"]

        for module in modules:
            print(f"\n模块: {module}")
            print("-" * 40)

            # 使用元数据过滤
            results = vector_store.search_by_metadata(
                query="error handling",
                metadata_filter={"module": module},
                k=2
            )

            print(f"  找到 {len(results)} 个结果:")
            for i, doc in enumerate(results, 1):
                print(f"    {i}. {doc.metadata.get('sop_title', 'Unknown')[:50]}...")

    except Exception as e:
        print(f"✗ 错误: {e}")


def test_collection_stats():
    """测试数据库统计信息"""
    print("\n" + "=" * 80)
    print("测试 4: 数据库统计")
    print("=" * 80)

    try:
        vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")

        stats = vector_store.get_collection_stats()

        print("\n向量数据库统计:")
        print(f"  - 集合名称: {stats.get('name', 'Unknown')}")
        print(f"  - 向量数量: {stats.get('count', 0)}")
        print(f"  - 持久化目录: {stats.get('persist_directory', 'Unknown')}")

    except Exception as e:
        print(f"✗ 错误: {e}")


def test_scenario_detection():
    """测试场景检测能力"""
    print("\n" + "=" * 80)
    print("测试 5: 场景检测")
    print("=" * 80)

    try:
        vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")

        scenarios = [
            {
                "name": "Duplicate Container",
                "query": "customer seeing duplicate container CMAU0000020",
                "expected_keywords": ["duplicate", "container"]
            },
            {
                "name": "Vessel Error",
                "query": "VESSEL_ERR_4 system vessel name already used",
                "expected_keywords": ["VESSEL_ERR_4", "vessel"]
            },
            {
                "name": "EDI Timeout",
                "query": "EDI message stuck in ERROR status no acknowledgment",
                "expected_keywords": ["EDI", "ERROR", "acknowledgment"]
            }
        ]

        for scenario in scenarios:
            print(f"\n场景: {scenario['name']}")
            print(f"查询: {scenario['query']}")
            print("-" * 40)

            results = vector_store.search_knowledge_base(scenario['query'], k=1)

            if results:
                top_result = results[0]
                print(f"  ✓ 匹配到: {top_result.metadata.get('sop_title', 'Unknown')[:60]}...")
                print(f"    模块: {top_result.metadata.get('module', 'Unknown')}")
                print(f"    类型: {top_result.metadata.get('chunk_type', 'Unknown')}")

                # 检查关键词
                content = top_result.page_content.lower()
                matched_keywords = [
                    kw for kw in scenario['expected_keywords']
                    if kw.lower() in content
                ]
                print(f"    匹配关键词: {matched_keywords}")
            else:
                print("  ✗ 未找到匹配结果")

    except Exception as e:
        print(f"✗ 错误: {e}")


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 22 + "向量数据库检索测试" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # 检查向量数据库是否存在
    if not os.path.exists("db_chroma_kb"):
        print("❌ 错误: 向量数据库 'db_chroma_kb' 不存在")
        print()
        print("请先运行向量化脚本:")
        print("  python vectorize_knowledge_base.py")
        print()
        return

    # 运行测试
    test_basic_search()
    test_search_with_scores()
    test_metadata_filtering()
    test_collection_stats()
    test_scenario_detection()

    print("\n" + "=" * 80)
    print("所有测试完成!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
