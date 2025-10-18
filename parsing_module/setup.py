"""
Setup configuration for the parsing_agent module.
This allows the package to be installed in development mode.
"""

from setuptools import setup, find_packages

setup(
    name="parsing_agent",
    version="1.0.0",
    description="AI-powered incident report parser for PORTNET® support system",
    author="PORTNET Team",
    python_requires=">=3.8",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "langchain>=0.1.0",
        "langchain-openai>=0.0.5",
        "langchain-core>=0.1.0",
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
