"""Agent runtime - 业务编排层，桥接 Provider 和 Agent 注册表。

提供 get_provider() 工厂函数，封装配置读取和 Provider 实例化。
"""

from app.core.config import get_settings
from app.providers.openai_compatible import QwenProvider


def get_provider() -> QwenProvider:
    settings = get_settings()
    return QwenProvider(settings)
