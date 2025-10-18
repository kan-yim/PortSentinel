"""Multi-Query 生成器：使用 LLM 从多个角度重写问题。"""

import os
from typing import List, Optional, TYPE_CHECKING

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

if TYPE_CHECKING:
    from parsing_agent.models import IncidentReport


class QueryExpander:
    """使用 Azure OpenAI LLM 生成查询变体。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
        llm: Optional[AzureChatOpenAI] = None
    ):
        """
        初始化 QueryExpander。

        Args:
            api_key: Azure OpenAI API key
            azure_endpoint: Azure endpoint
            deployment: Chat model deployment name
            api_version: API version
            llm: 可选，自定义的 AzureChatOpenAI 实例（用于测试）
        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self.api_version = api_version or os.getenv(
            "AZURE_OPENAI_API_VERSION",
            "2024-02-15-preview"
        )

        if llm is not None:
            self.llm = llm
        else:
            missing = [name for name, value in [
                ("AZURE_OPENAI_API_KEY", self.api_key),
                ("AZURE_OPENAI_ENDPOINT", self.azure_endpoint),
                ("AZURE_OPENAI_DEPLOYMENT", self.deployment)
            ] if not value]
            if missing:
                raise ValueError(
                    "Missing Azure OpenAI configuration: "
                    + ", ".join(missing)
                )

            self.llm = AzureChatOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                azure_deployment=self.deployment,
                api_version=self.api_version,
                temperature=0.3
            )

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert assistant that rewrites technical incident reports "
                "into multiple precise search queries for Standard Operating Procedure retrieval."
            ),
            (
                "human",
                "Original report summary:\n{report_context}\n\n"
                "Primary search query:\n{original_query}\n\n"
                "Generate {num_variants} alternative queries that:\n"
                "1. Rephrase key technical terms and error descriptions\n"
                "2. Introduce closely related troubleshooting vocabulary\n"
                "3. Stay concise and focused on SOP retrieval\n"
                "4. Remain highly relevant to the incident context\n\n"
                "Return queries as plain text, one per line, without bullets or numbering."
            )
        ])

    def expand_from_report(
        self,
        report: "IncidentReport",
        num_variants: int = 3
    ) -> List[str]:
        """
        使用 LLM 从 IncidentReport 生成查询变体。

        Args:
            report: 结构化事故报告
            num_variants: 希望生成的变体数量（不包含原始查询）

        Returns:
            包含原始查询和 LLM 生成变体的列表
        """
        if num_variants < 0:
            raise ValueError("num_variants must be >= 0")

        problem_summary = getattr(report, "problem_summary", "") or ""
        affected_module = getattr(report, "affected_module", "")
        error_code = getattr(report, "error_code", "")
        additional_notes = getattr(report, "additional_notes", "")

        entity_strings = []
        for entity in getattr(report, "entities", []) or []:
            entity_type = getattr(entity, "type", "") or ""
            entity_value = getattr(entity, "value", "") or ""
            if entity_type and entity_value:
                entity_strings.append(f"{entity_type}: {entity_value}")

        query_parts = []
        if error_code:
            query_parts.append(f"Error code: {error_code}")
        if problem_summary:
            query_parts.append(problem_summary)
        if affected_module:
            query_parts.append(f"Module: {affected_module}")
        if entity_strings:
            query_parts.append("Entities: " + ", ".join(entity_strings))

        original_query = " | ".join(query_parts) or problem_summary or "Technical incident report"

        report_context_lines = [
            f"Problem summary: {problem_summary or 'N/A'}",
            f"Affected module: {affected_module or 'Unknown'}",
            f"Error code: {error_code or 'None'}",
            f"Entities: {', '.join(entity_strings) if entity_strings else 'None'}",
            f"Additional notes: {additional_notes or 'None'}"
        ]
        report_context = "\n".join(report_context_lines)

        messages = self.prompt.format_messages(
            original_query=original_query,
            report_context=report_context,
            num_variants=num_variants
        )

        try:
            response = self.llm.invoke(messages)
        except Exception as exc:
            raise RuntimeError(f"LLM query expansion failed: {exc}") from exc

        content = getattr(response, "content", None)
        if content is None:
            content = str(response)

        generated_queries = [
            line.strip()
            for line in content.splitlines()
            if line.strip()
        ]

        unique_variants: List[str] = []
        seen = set()
        for variant in generated_queries:
            if variant not in seen and variant.lower() != original_query.lower():
                unique_variants.append(variant)
                seen.add(variant)
            if len(unique_variants) >= num_variants:
                break

        return [original_query] + unique_variants
