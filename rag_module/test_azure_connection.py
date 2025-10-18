"""
测试 Azure OpenAI 连接和 embedding deployment
"""

import os
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings

load_dotenv()

def test_connection():
    print("=" * 80)
    print("测试 Azure OpenAI Embedding 连接")
    print("=" * 80)

    # 读取配置
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    print("\n当前配置:")
    print(f"  API Key: {api_key[:20]}..." if api_key else "  API Key: 未设置")
    print(f"  Endpoint: {endpoint}")
    print(f"  Deployment: {deployment}")
    print(f"  API Version: {api_version}")

    if not all([api_key, endpoint, deployment]):
        print("\n❌ 错误: 缺少必要的环境变量")
        print("请确保 .env 文件中配置了:")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        return

    print("\n正在测试连接...")

    try:
        # 创建 embeddings 实例
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=deployment,
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key
        )

        print("  ✓ Embeddings 实例创建成功")

        # 测试 embedding 一个简单的文本
        print("\n正在测试 embedding 功能...")
        test_text = "This is a test sentence."

        embedding_vector = embeddings.embed_query(test_text)

        print(f"  ✓ Embedding 成功!")
        print(f"  - 输入文本: '{test_text}'")
        print(f"  - 向量维度: {len(embedding_vector)}")
        print(f"  - 向量前5个值: {embedding_vector[:5]}")

        print("\n✅ 连接测试成功! Azure OpenAI embedding 配置正确。")

    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("\n可能的原因:")
        print("  1. API Key 不正确")
        print("  2. Endpoint URL 格式错误")
        print("  3. Embedding deployment 名称不存在")
        print("  4. API version 不支持")
        print("\n建议:")
        print("  - 检查 Azure Portal 中的 deployment 名称")
        print("  - 确认 endpoint 格式: https://<resource-name>.openai.azure.com/")
        print("  - 验证 API key 是否有效")


if __name__ == "__main__":
    try:
        test_connection()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
