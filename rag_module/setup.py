"""
Setup configuration for rag_agent module.
"""

from setuptools import setup, find_packages

setup(
    name="rag_agent",
    version="1.0.0",
    description="RAG-based SOP retrieval for PORTNET incident management",
    author="PORTNET Team",
    python_requires=">=3.8",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "langchain>=0.1.0",
        "langchain-openai>=0.0.5",
        "langchain-core>=0.1.0",
        "langchain-community>=0.0.20",
        "chromadb>=0.4.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
        ],
    },
)
