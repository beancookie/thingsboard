class AgentError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "AGENT_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class AgentUnauthorized(AgentError):
    def __init__(self, message: str = "登录状态无效或已过期"):
        super().__init__(message, status_code=401, code="UNAUTHORIZED")


class AgentForbidden(AgentError):
    def __init__(self, message: str = "没有访问该操作的权限"):
        super().__init__(message, status_code=403, code="FORBIDDEN")


class AgentUnavailable(AgentError):
    def __init__(self, message: str = "Agent 服务暂不可用"):
        super().__init__(message, status_code=502, code="AGENT_UNAVAILABLE")
