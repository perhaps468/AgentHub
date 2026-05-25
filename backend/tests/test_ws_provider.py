"""P1-1 WebSocket Provider 链路业务逻辑测试（已废弃）。

本测试文件覆盖的旧 WebSocket Provider 链路已被 P1-3 FixedAgentResponder 替代。
所有测试现标记为 skip，保留作为历史参考。

原覆盖范围：
- valid_send_message 验证规则
- Provider 成功时 human + agent message 均落库，sender_role=PM
- Provider 错误码映射
- agent_typing / ws_send_chunk / send_error 事件格式
- delivery_status 字段行为
"""

import pytest

pytestmark = pytest.mark.skip(reason="P1-3: Old provider streaming replaced by FixedAgentResponder")
