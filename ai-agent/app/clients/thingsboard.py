from typing import Any

import httpx

from app.auth.thingsboard import auth_headers
from app.common.errors import AgentError, AgentUnavailable


class ThingsBoardClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self._client = client
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    async def list_tenants(self, token: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/tenants",
            token,
            params={"pageSize": 100, "page": 0, "sortProperty": "title", "sortOrder": "ASC"},
        )

    async def create_tenant(
        self,
        token: str,
        title: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if description:
            payload["description"] = description
        return await self._request("POST", "/api/tenant", token, json=payload)

    async def create_user(
        self,
        token: str,
        tenant_id: str,
        email: str,
        authority: str,
        first_name: str | None = None,
        last_name: str | None = None,
        send_activation_mail: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "tenantId": {"entityType": "TENANT", "id": tenant_id},
            "email": email,
            "authority": authority,
            "firstName": first_name or "",
            "lastName": last_name or "",
        }
        return await self._request(
            "POST",
            "/api/user",
            token,
            params={"sendActivationMail": str(send_activation_mail).lower()},
            json=payload,
        )

    async def list_tenant_devices(
        self,
        token: str,
        page_size: int = 100,
        page: int = 0,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/tenant/devices",
            token,
            params={
                "pageSize": page_size,
                "page": page,
                "sortProperty": "name",
                "sortOrder": "ASC",
            },
        )

    async def create_device(
        self,
        token: str,
        name: str,
        device_profile_id: str,
        label: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "label": label or name,
            "deviceProfileId": {
                "entityType": "DEVICE_PROFILE",
                "id": device_profile_id,
            },
        }
        return await self._request("POST", "/api/device", token, json=payload)

    async def save_device_attributes(
        self,
        token: str,
        device_id: str,
        attributes: dict[str, Any],
    ) -> None:
        await self._request(
            "POST",
            f"/api/plugins/telemetry/DEVICE/{device_id}/attributes/SERVER_SCOPE",
            token,
            json=attributes,
        )

    async def delete_tenant(self, token: str, tenant_id: str) -> None:
        await self._request("DELETE", f"/api/tenant/{tenant_id}", token)

    async def delete_device(self, token: str, device_id: str) -> None:
        await self._request("DELETE", f"/api/device/{device_id}", token)

    async def delete_user(self, token: str, user_id: str) -> None:
        await self._request("DELETE", f"/api/user/{user_id}", token)

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                f"{self._base_url}{path}",
                headers=auth_headers(token),
                params=params,
                json=json,
            )
        except httpx.HTTPError as exc:
            raise AgentUnavailable("无法连接 ThingsBoard") from exc

        if response.status_code >= 400:
            body = response.text[:500]
            raise AgentError(
                f"ThingsBoard API 调用失败: HTTP {response.status_code} {body}",
                status_code=502,
                code="THINGSBOARD_API_ERROR",
            )
        if not response.content:
            return {}
        return response.json()
