"""
向量化知识库脚本

将 knowledge_base_structured.json 转换为 Chroma 向量数据库，
用于 RAG 检索。
"""

import json
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Load environment variables
load_dotenv()


class KnowledgeBaseVectorizer:
    """将结构化知识库转换为向量数据库"""

    def __init__(
        self,
        kb_json_path: str = "../knowledge_base_structured.json",
        output_dir: str = "db_chroma_kb",
        api_key: str = None,
        azure_endpoint: str = None,
        embedding_deployment: str = None,
        api_version: str = None
    ):
        """
        初始化向量化器

        Args:
            kb_json_path: knowledge_base_structured.json 文件路径
            output_dir: Chroma 数据库输出目录
            api_key: Azure OpenAI API key
            azure_endpoint: Azure endpoint URL
            embedding_deployment: Embedding model deployment name
            api_version: API version
        """
        self.kb_json_path = kb_json_path
        self.output_dir = output_dir

        # Get Azure credentials
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.embedding_deployment = (
            embedding_deployment or
            os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        )
        self.api_version = (
            api_version or
            os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        )

        if not all([self.api_key, self.azure_endpoint, self.embedding_deployment]):
            raise ValueError(
                "请在 .env 文件中配置 Azure OpenAI 凭据:\n"
                "AZURE_OPENAI_API_KEY\n"
                "AZURE_OPENAI_ENDPOINT\n"
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
            )

        print(f"配置信息:")
        print(f"  - 知识库文件: {self.kb_json_path}")
        print(f"  - 输出目录: {self.output_dir}")
        print(f"  - Azure Endpoint: {self.azure_endpoint}")
        print(f"  - Embedding Deployment: {self.embedding_deployment}")

    def load_knowledge_base(self) -> List[dict]:
        """加载 JSON 知识库"""
        print(f"\n正在加载知识库...")

        if not os.path.exists(self.kb_json_path):
            raise FileNotFoundError(f"知识库文件不存在: {self.kb_json_path}")

        with open(self.kb_json_path, 'r', encoding='utf-8') as f:
            sops = json.load(f)

        print(f"  ✓ 成功加载 {len(sops)} 个 SOP")
        return sops

    def create_documents(self, sops: List[dict]) -> List[Document]:
        """
        将 SOP 转换为 LangChain Document 对象

        每个 SOP 创建多个文档块以提高检索精度:
        1. 标题 + Overview
        2. 标题 + Resolution
        3. 标题 + Preconditions (如果存在)
        """
        documents = []

        print(f"\n正在创建文档块...")

        for idx, sop in enumerate(sops, 1):
            title = sop.get("标题", "未命名 SOP")
            overview = sop.get("overview", "")
            resolution = sop.get("resolution", "")
            verification = sop.get("verification", "")
            preconditions = sop.get("preconditions")
            module = sop.get("module", "Unknown")

            # 文档 1: 标题 + Overview (问题描述)
            if overview:
                doc1 = Document(
                    page_content=f"Title: {title}\n\nOverview:\n{overview}",
                    metadata={
                        "sop_title": title,
                        "module": module,
                        "chunk_type": "overview",
                        "sop_index": idx,
                        "source": "knowledge_base_structured.json"
                    }
                )
                documents.append(doc1)

            # 文档 2: 标题 + Resolution (解决步骤)
            if resolution:
                doc2 = Document(
                    page_content=f"Title: {title}\n\nResolution Steps:\n{resolution}",
                    metadata={
                        "sop_title": title,
                        "module": module,
                        "chunk_type": "resolution",
                        "sop_index": idx,
                        "source": "knowledge_base_structured.json"
                    }
                )
                documents.append(doc2)

            # 文档 3: 标题 + Preconditions (如果存在)
            if preconditions:
                doc3 = Document(
                    page_content=f"Title: {title}\n\nPreconditions:\n{preconditions}",
                    metadata={
                        "sop_title": title,
                        "module": module,
                        "chunk_type": "preconditions",
                        "sop_index": idx,
                        "source": "knowledge_base_structured.json"
                    }
                )
                documents.append(doc3)

            # 文档 4: 标题 + Verification (验证步骤)
            if verification:
                doc4 = Document(
                    page_content=f"Title: {title}\n\nVerification Steps:\n{verification}",
                    metadata={
                        "sop_title": title,
                        "module": module,
                        "chunk_type": "verification",
                        "sop_index": idx,
                        "source": "knowledge_base_structured.json"
                    }
                )
                documents.append(doc4)

        print(f"  ✓ 创建了 {len(documents)} 个文档块 (来自 {len(sops)} 个 SOP)")
        return documents

    def create_embeddings(self) -> AzureOpenAIEmbeddings:
        """初始化 Azure OpenAI Embeddings"""
        print(f"\n正在初始化嵌入模型...")

        try:
            embeddings = AzureOpenAIEmbeddings(
                azure_deployment=self.embedding_deployment,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key
            )
            print(f"  ✓ 嵌入模型初始化成功")
            return embeddings
        except Exception as e:
            raise ConnectionError(f"嵌入模型初始化失败: {e}")

    def create_vector_store(
        self,
        documents: List[Document],
        embeddings: AzureOpenAIEmbeddings
    ) -> Chroma:
        """
        创建 Chroma 向量数据库

        Args:
            documents: 文档列表
            embeddings: 嵌入模型

        Returns:
            Chroma 向量数据库实例
        """
        print(f"\n正在创建向量数据库...")
        print(f"  - 将向量化 {len(documents)} 个文档")
        print(f"  - 这可能需要几分钟时间...")

        # 如果输出目录已存在，先删除
        if os.path.exists(self.output_dir):
            import shutil
            print(f"  - 删除现有数据库: {self.output_dir}")
            shutil.rmtree(self.output_dir)

        try:
            # 分批处理以避免 API 限流
            batch_size = 100
            total_batches = (len(documents) + batch_size - 1) // batch_size

            vector_store = None

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = i // batch_size + 1

                print(f"  - 处理批次 {batch_num}/{total_batches} ({len(batch)} 个文档)...")

                if vector_store is None:
                    # 第一批: 创建新的向量数据库
                    vector_store = Chroma.from_documents(
                        documents=batch,
                        embedding=embeddings,
                        persist_directory=self.output_dir
                    )
                else:
                    # 后续批次: 添加到现有数据库
                    vector_store.add_documents(batch)

            print(f"  ✓ 向量数据库创建成功!")
            print(f"  ✓ 保存位置: {self.output_dir}")

            return vector_store

        except Exception as e:
            raise Exception(f"向量数据库创建失败: {e}")

    def vectorize(self):
        """执行完整的向量化流程"""
        print("\n" + "=" * 80)
        print("知识库向量化开始")
        print("=" * 80)

        try:
            # 1. 加载知识库
            sops = self.load_knowledge_base()

            # 2. 创建文档
            documents = self.create_documents(sops)

            # 3. 初始化嵌入模型
            embeddings = self.create_embeddings()

            # 4. 创建向量数据库
            vector_store = self.create_vector_store(documents, embeddings)

            # 5. 验证
            print(f"\n正在验证向量数据库...")
            collection_count = vector_store._collection.count()
            print(f"  ✓ 数据库中共有 {collection_count} 个向量")

            # 6. 测试检索
            print(f"\n正在测试检索功能...")
            test_query = "VESSEL_ERR_4"
            results = vector_store.similarity_search(test_query, k=3)
            print(f"  ✓ 测试查询 '{test_query}' 返回 {len(results)} 个结果")

            if results:
                print(f"\n  示例结果:")
                for i, doc in enumerate(results[:2], 1):
                    print(f"    {i}. {doc.metadata.get('sop_title', 'Unknown')[:60]}...")

            print("\n" + "=" * 80)
            print("✓ 知识库向量化完成!")
            print("=" * 80)
            print(f"\n使用方法:")
            print(f"  from langchain_community.vectorstores import Chroma")
            print(f"  vector_store = Chroma(")
            print(f"      persist_directory='{self.output_dir}',")
            print(f"      embedding_function=embeddings")
            print(f"  )")
            print()

        except Exception as e:
            print(f"\n✗ 向量化失败: {e}")
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="向量化知识库")
    parser.add_argument(
        "--input",
        default="../knowledge_base_structured.json",
        help="知识库 JSON 文件路径"
    )
    parser.add_argument(
        "--output",
        default="db_chroma_kb",
        help="Chroma 数据库输出目录"
    )

    args = parser.parse_args()

    try:
        vectorizer = KnowledgeBaseVectorizer(
            kb_json_path=args.input,
            output_dir=args.output
        )
        vectorizer.vectorize()

    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
