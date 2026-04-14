import os

class DeepSeekAPI:
    def __init__(self, api_key):
        self.api_key = api_key

def init_deepseek_api():
    """初始化DeepSeek API"""
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    if DEEPSEEK_API_KEY:
        deepseek_api = DeepSeekAPI(DEEPSEEK_API_KEY)
        print("✓ DeepSeek API 已初始化")
    else:
        deepseek_api = DeepSeekAPI(None)
        print("! DeepSeek API密钥未设置，AI评语生成功能不可用")
    return deepseek_api
