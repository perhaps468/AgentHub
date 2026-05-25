"""P1-2-2: 流式编排服务测试（已废弃）。

本测试文件覆盖的 AgentStreamService 已被 P1-3 FixedAgentResponder 替代。
所有测试现标记为 skip，保留作为历史参考。
"""

import pytest

pytestmark = pytest.mark.skip(reason="P1-3: AgentStreamService replaced by FixedAgentResponder")
