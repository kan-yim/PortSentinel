"""
检查 Azure OpenAI 资源中可用的 deployments
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# 移除 endpoint 中的 deployment 部分
if endpoint and "/gpt-4" in endpoint:
    base_endpoint = endpoint.split("/gpt-4")[0]
else:
    base_endpoint = endpoint

print("检查 Azure OpenAI Deployments")
print("=" * 80)
print(f"Endpoint: {base_endpoint}")
print()

# 尝试列出 deployments
url = f"{base_endpoint}/openai/deployments?api-version={api_version}"

headers = {
    "api-key": api_key
}

try:
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        deployments = data.get("data", [])

        print(f"找到 {len(deployments)} 个 deployments:")
        print()

        for dep in deployments:
            model = dep.get("model", "Unknown")
            dep_id = dep.get("id", "Unknown")
            status = dep.get("status", "Unknown")

            print(f"  - {dep_id}")
            print(f"    模型: {model}")
            print(f"    状态: {status}")
            print()

        # 检查是否有 embedding model
        embedding_deployments = [
            d for d in deployments
            if "embedding" in d.get("model", "").lower()
        ]

        if embedding_deployments:
            print("✅ 找到 embedding deployments:")
            for d in embedding_deployments:
                print(f"   - {d.get('id')}")
            print()
            print(f"建议在 .env 中设置:")
            print(f"AZURE_OPENAI_EMBEDDING_DEPLOYMENT={embedding_deployments[0].get('id')}")
        else:
            print("❌ 没有找到 embedding deployment")
            print()
            print("你需要:")
            print("1. 在 Azure Portal 创建一个 embedding deployment")
            print("2. 或者使用 OpenAI 的 embedding API (需要 OpenAI API key)")
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"响应: {response.text}")

except Exception as e:
    print(f"❌ 错误: {e}")
    print()
    print("可能的原因:")
    print("1. Endpoint URL 格式不正确")
    print("2. API Key 无效")
    print("3. 网络连接问题")
