from typing import Any

import httpx

from app.auth.thingsboard import auth_headers
from app.common.errors import AgentError, AgentUnavailable


class ThingModelClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        max_response_bytes: int | None = None,
    ):
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._max_response_bytes = max_response_bytes

    async def request(
        self,
        method: str,
        path: str,
        token: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        return await self._request(method, path, token, params=params, json=json)

    async def list_products(self, token: str, keyword: str | None = None) -> list[dict[str, Any]]:
        params = {"keyword": keyword} if keyword else None
        return await self._request("GET", "/api/products", token, params=params)

    async def get_product(self, token: str, product_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/products/{product_id}", token)

    async def create_product(self, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/products", token, json=payload)

    async def delete_product(self, token: str, product_id: str) -> None:
        await self._request("DELETE", f"/api/products/{product_id}", token)

    async def provision_auto(
        self,
        token: str,
        tenant_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/admin/tenants/{tenant_id}/provision-auto",
            token,
            params={"force": str(force).lower()},
        )

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        try:
            response = await self._client.request(
                method,
                f"{self._base_url}{path}",
                headers=auth_headers(token),
                params=params,
                json=json,
            )
        except httpx.HTTPError as exc:
            raise AgentUnavailable("无法连接 thing-model 服务") from exc

        if response.status_code >= 400:
            body = response.text[:500]
            raise AgentError(
                f"thing-model API 调用失败: HTTP {response.status_code} {body}",
                status_code=502,
                code="THING_MODEL_API_ERROR",
            )
        if not response.content:
            return {}
        if (
            self._max_response_bytes is not None
            and len(response.content) > self._max_response_bytes
        ):
            raise AgentError(
                "thing-model 响应过大，请缩小查询范围",
                status_code=502,
                code="API_RESPONSE_TOO_LARGE",
            )
        return response.json()
