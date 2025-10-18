"""
Vector store interface for querying knowledge base using RAG.

This module provides methods to search the Chroma vector database
containing embedded SOP documents from the Knowledge Base.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document

# Load environment variables
load_dotenv()


class VectorStoreInterface:
    """
    Interface for interacting with Chroma vector database.

    Provides semantic search capabilities over the knowledge base
    using Azure OpenAI embeddings.
    """

    def __init__(
        self,
        persist_directory: str = "db_chroma_kb",
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        embedding_deployment: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        """
        Initialize vector store with Azure OpenAI embeddings.

        Args:
            persist_directory: Path to Chroma database directory
            api_key: Azure OpenAI API key (defaults to AZURE_OPENAI_API_KEY env var)
            azure_endpoint: Azure endpoint (defaults to AZURE_OPENAI_ENDPOINT env var)
            embedding_deployment: Embedding model deployment name
                (defaults to AZURE_OPENAI_EMBEDDING_DEPLOYMENT env var)
            api_version: API version (defaults to AZURE_OPENAI_API_VERSION env var)

        Raises:
            ValueError: If required Azure credentials are missing
            FileNotFoundError: If persist_directory doesn't exist
        """
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
                "Azure OpenAI credentials must be provided either via constructor "
                "arguments or environment variables (AZURE_OPENAI_API_KEY, "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_EMBEDDING_DEPLOYMENT)"
            )

        # Check if persist directory exists
        if not os.path.exists(persist_directory):
            raise FileNotFoundError(
                f"Chroma persist directory not found: {persist_directory}. "
                "Please ensure the knowledge base has been vectorized first."
            )

        self.persist_directory = persist_directory

        # Initialize Azure OpenAI Embeddings
        try:
            self.embeddings = AzureOpenAIEmbeddings(
                azure_deployment=self.embedding_deployment,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to initialize Azure OpenAI embeddings: {e}"
            )

        # Load Chroma vector store
        try:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to load Chroma vector store from {persist_directory}: {e}"
            )

    def search_knowledge_base(
        self,
        query: str,
        k: int = 3,
        score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Perform semantic similarity search on the knowledge base.

        Args:
            query: Search query text
            k: Number of top results to return (default: 3)
            score_threshold: Optional minimum similarity score threshold (0-1)

        Returns:
            List of LangChain Document objects with metadata

        Raises:
            ValueError: If query is empty
            Exception: If search fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        try:
            if score_threshold is not None:
                # Similarity search with score filtering
                docs_and_scores = self.vector_store.similarity_search_with_score(
                    query=query,
                    k=k
                )
                # Filter by threshold and extract documents
                documents = [
                    doc for doc, score in docs_and_scores
                    if score >= score_threshold
                ]
            else:
                # Standard similarity search
                documents = self.vector_store.similarity_search(
                    query=query,
                    k=k
                )

            return documents

        except Exception as e:
            raise Exception(f"Knowledge base search failed: {e}")

    def search_with_scores(
        self,
        query: str,
        k: int = 5
    ) -> List[tuple[Document, float]]:
        """
        执行相似度搜索并返回余弦相似度分数
        
        ✅ 只搜索 header，使用 metadata 过滤
        ✅ 返回余弦相似度（0-1，越大越相似）
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        try:
            # ✅ 使用 filter 只搜索 header
            # 搜索更多文档以确保有足够的 header
            search_k = 5
            
            docs_and_distances = self.vector_store.similarity_search_with_score(
                query=query,
                k=search_k,
                filter={"chunk_type": "header"}  # ✅ 只搜索 header
            )
            
            # ✅ 余弦相似度转换
            # Chroma 返回的 distance = 1 - cosine_similarity
            # 所以 similarity = 1 - distance
            docs_and_similarities = []
            for doc, distance in docs_and_distances:
                similarity = 1 - distance  # 转换为余弦相似度
                docs_and_similarities.append((doc, similarity))
            
            # 只返回前 k 个
            return docs_and_similarities[:k]

        except Exception as e:
            raise Exception(f"Knowledge base search with scores failed: {e}")

    def search_by_metadata(
        self,
        query: str,
        metadata_filter: dict,
        k: int = 3
    ) -> List[Document]:
        """
        Search with metadata filtering.

        Args:
            query: Search query text
            metadata_filter: Dictionary of metadata filters
                Example: {"module": "Vessel", "sop_title": "VAS: VESSEL_ERR_4"}
            k: Number of results to return

        Returns:
            List of filtered Document objects

        Raises:
            Exception: If search fails
        """
        try:
            documents = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=metadata_filter
            )
            return documents

        except Exception as e:
            raise Exception(f"Metadata-filtered search failed: {e}")

    def get_collection_stats(self) -> dict:
        """
        Get statistics about the vector store collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.vector_store._collection
            return {
                "name": collection.name,
                "count": collection.count(),
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {
                "error": f"Failed to get collection stats: {e}"
            }
