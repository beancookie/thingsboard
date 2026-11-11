from fastapi import Request

from app.common.errors import AgentUnauthorized


def extract_token(request: Request) -> str:
    value = request.headers.get("X-Authorization") or request.headers.get("Authorization")
    if not value or not value.strip():
        raise AgentUnauthorized("缺少访问令牌")
    token = value.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise AgentUnauthorized("缺少访问令牌")
    return token
