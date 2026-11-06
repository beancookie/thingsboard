# 7 API 参考

> 中国中铁物联网平台文档集｜[总目录](../README.md)｜上一篇 [前端与权限](06-前端与权限.md)｜下一篇 [部署与运维](08-部署与运维.md)

## 7.1 访问方式

`thing-model` 直接地址：

```text
http://<thing-model-host>:8090
```

浏览器通过 Nginx 或开发代理访问时：

```text
/api/thing-model/*  ->  thing-model /api/*
```

所有接口使用中国中铁物联网平台 JWT：

```http
X-Authorization: Bearer <TB_JWT>
```

也兼容：

```http
Authorization: Bearer <TB_JWT>
```

## 7.2 权限

| 接口组 | 允许角色 |
| --- | --- |
| `/api/auth/me` | 任意已登录中国中铁物联网平台用户 |
| `/api/products/**` | 租户管理员 |
| `/api/admin/**` | 系统管理员 |

产品租户始终来自 JWT。跨租户产品访问返回 `404`；请求体指定其他 tenantId 返回 `403`。

## 7.3 当前用户

```http
GET /api/auth/me
```

返回：

```json
{
  "userId": "...",
  "tenantId": "...",
  "email": "tenant@example.com"
}
```

authority 字段返回租户管理员权限。

## 7.4 产品接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/products?keyword=` | 当前租户产品列表 |
| GET | `/api/products/{productId}` | 产品详情、版本列表、物模型目录 |
| GET | `/api/products/{productId}/thing-model` | 最新 TSL 原文 |
| POST | `/api/products` | 创建产品 |
| PUT | `/api/products/{productId}/thing-model` | 提交新 TSL 版本 |
| POST | `/api/products/{productId}/thing-model/validate` | 只校验 TSL，不落库 |
| GET | `/api/products/{productId}/catalog` | 最新 TSL 的属性/事件/行为目录 |
| DELETE | `/api/products/{productId}` | 删除产品及其物模型和平台资源 |

### 创建产品

```http
POST /api/products
Content-Type: application/json

{
  "productId": "9HYN9PJNOY",
  "name": "WiFi诊断终端",
  "model": "9HYN9PJNOY",
  "categoryId": "1",
  "tslVersion": "1.0",
  "strictUnknown": false,
  "tsl": {
    "version": "1.0",
    "profile": {
      "ProductId": "9HYN9PJNOY",
      "CategoryId": "1"
    },
    "properties": [
      {
        "id": "rssi",
        "name": "信号强度",
        "mode": "r",
        "define": {
          "type": "int",
          "min": -120,
          "max": 0,
          "unit": "dBm"
        }
      }
    ]
  }
}
```

`tenantId` 可省略；如果提供，必须等于 JWT 租户。

返回：

```json
{
  "productId": "9HYN9PJNOY",
  "tslVersion": "1.0",
  "tbProfileId": "...",
  "tbAssetId": "...",
  "tbRuleChainId": "...",
  "propertyCount": 1,
  "eventCount": 0,
  "actionCount": 0,
  "schemaBytes": 220,
  "status": "PUBLISHED",
  "warnings": []
}
```

### 更新物模型

```http
PUT /api/products/{productId}/thing-model
Content-Type: application/json

{
  "tslVersion": "1.1",
  "strictUnknown": false,
  "tsl": {
    "version": "1.1",
    "profile": {
      "ProductId": "9HYN9PJNOY"
    },
    "properties": []
  }
}
```

### 校验物模型

```http
POST /api/products/{productId}/thing-model/validate
Content-Type: application/json

{
  "tsl": {
    "version": "1.0",
    "profile": {
      "ProductId": "9HYN9PJNOY"
    },
    "properties": []
  }
}
```

返回：

```json
{
  "valid": false,
  "errors": [
    {
      "code": "ID_DUP",
      "path": "/properties/1/id",
      "message": "属性标识重复: rssi"
    }
  ],
  "warnings": []
}
```

### 产品详情

返回结构：

```json
{
  "product": {
    "tenantId": "...",
    "productId": "9HYN9PJNOY",
    "name": "WiFi诊断终端",
    "model": "9HYN9PJNOY",
    "categoryId": "1",
    "tslVersion": "1.0",
    "status": "PUBLISHED",
    "propertyCount": 1,
    "eventCount": 0,
    "actionCount": 0,
    "tbProfileId": "...",
    "tbAssetId": "...",
    "tbRuleChainId": "...",
    "updatedAt": "2026-01-01T00:00:00Z"
  },
  "versions": [
    {
      "version": "1.0",
      "status": "PUBLISHED",
      "checksum": "...",
      "publishedAt": "2026-01-01T00:00:00Z",
      "createdAt": "2026-01-01T00:00:00Z"
    }
  ],
  "catalog": {
    "productId": "9HYN9PJNOY",
    "version": "1.0",
    "properties": [],
    "events": [],
    "actions": []
  }
}
```

### 最新 TSL

```http
GET /api/products/{productId}/thing-model
```

返回：

```json
{
  "productId": "9HYN9PJNOY",
  "version": "1.0",
  "status": "PUBLISHED",
  "strictUnknown": false,
  "tsl": {}
}
```

### 删除产品

```http
DELETE /api/products/{productId}
```

成功返回 `204`。删除范围：

- `plat_product`、全部 TSL 版本、属性/事件/行为目录、绑定记录；
- 产品独占的产品配置、产品资产、产品规则链。

产品下仍有设备时返回：

```json
{
  "message": "产品下存在 2 台设备，无法删除",
  "code": "PRODUCT_HAS_DEVICES"
}
```

中国中铁物联网平台资源删除失败返回 `502 TB_DELETE_FAILED`，平台数据保留，可重试。已被删除的资源在重试时按 404 忽略。

## 7.5 租户服务账号接口

仅系统管理员可调用。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/admin/tenants/{tenantId}/account` | 注册或更新已有中国中铁物联网平台账号 |
| POST | `/api/admin/tenants/{tenantId}/provision` | 幂等注册已有租户管理员 |
| POST | `/api/admin/tenants/{tenantId}/provision-auto?force=false` | 自动创建、激活并注册专用租户管理员 |
| GET | `/api/admin/tenants/{tenantId}/account` | 查询已注册的 脱敏账号 |

### 自动初始化

```http
POST /api/admin/tenants/{tenantId}/provision-auto?force=false
X-Authorization: Bearer <系统管理员_JWT>
```

返回：

```json
{
  "tenantId": "...",
  "username": "thing-model-svc-<tenantId>@thing-model.local",
  "enabled": true
}
```

行为：

- 账号已存在且 `force=false`：直接返回已有 脱敏账号。
- 账号已存在且 `force=true`：删除旧服务账号用户后重建。
- 创建或激活失败时尽力删除刚创建的用户。
- 密码不返回，不写日志。

### 手动注册

```http
POST /api/admin/tenants/{tenantId}/provision
X-Authorization: Bearer <系统管理员_JWT>
Content-Type: application/json

{
  "username": "tenant@example.com",
  "password": "<password>",
  "force": false
}
```

### 查询账号

```http
GET /api/admin/tenants/{tenantId}/account
```

未配置时返回：

```json
{
  "message": "厂商租户未配置服务账号",
  "code": "ITEM_NOT_FOUND"
}
```

## 7.6 错误响应

统一结构：

```json
{
  "message": "物模型校验失败",
  "code": "TSL_INVALID",
  "issues": [
    {
      "code": "ID_DUP",
      "path": "/properties/1/id",
      "message": "属性标识重复: rssi"
    }
  ],
}
```

字段按需省略，`issues` 为空时可能不返回。

常见错误码：

| 错误码 | 典型状态 | 说明 |
| --- | --- | --- |
| `UNAUTHORIZED` | 401 | 缺少或无效 JWT |
| `FORBIDDEN` | 403 | 角色不符或跨租户 |
| `TENANT_REQUIRED` | 403 | 当前用户不属于租户 |
| `TENANT_ACCOUNT_MISSING` | 400 | 租户未配置服务账号 |
| `TENANT_ACCOUNT_DISABLED` | 403 | 服务账号已停用 |
| `TENANT_ACCOUNT_CONFLICT` | 409 | 服务账号用户已存在但账号表缺失 |
| `PRODUCT_NOT_FOUND` | 404 | 产品不存在或不属于当前租户 |
| `PRODUCT_CONFLICT` | 409 | 产品创建并发冲突 |
| `PRODUCT_HAS_DEVICES` | 409 | 产品下仍有设备，禁止删除 |
| `PRODUCT_ID_MISSING` | 400 | 缺少 产品 ID |
| `PRODUCT_ID_MISMATCH` | 400 | 请求 产品 ID 与 TSL 不一致 |
| `TSL_REQUIRED` | 400 | 缺少 TSL |
| `TSL_INVALID` | 400 | TSL 校验失败 |
| `TSL_VERSION_EXISTS` | 409 | 同一版本内容不同 |
| `VERSION_MISSING` | 400 | 缺少 TSL 版本 |
| `VERSION_MISMATCH` | 400 | 请求版本与 TSL 内容不一致 |
| `TB_DELETE_FAILED` | 502 | 平台资源删除失败，可重试 |
| `TB_UNAVAILABLE` | 502 | 平台资源不可达 |
| `ITEM_NOT_FOUND` | 404 | 查询对象不存在 |

## 7.7 接口边界

本文未列出的产品、设备、台账、事件、开放接口均未在当前代码中实现。不要根据历史文档调用已删除的路径。
