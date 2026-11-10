# MQTT推送数据到设备使用手册

> 中国中铁物联网平台文档集
>
> 适用对象：设备接入人员、设备固件开发人员、平台运维人员、第三方接入方

## 1. 文档说明

### 1.1 目的

本手册说明如何通过 MQTT 向设备推送下行数据，包括：

- 推送共享属性，用于下发配置、阈值和期望状态；
- 下发 RPC 命令，用于控制设备或读取设备状态；
- 设备端订阅主题、解析报文和返回响应；
- 设备断线、超时和常见问题的排查。

### 1.2 适用范围

本手册适用于：

- 直连平台的 MQTT 设备；
- 通过网关接入的子设备；
- 设备固件、边缘程序和模拟客户端开发；
- 平台页面下发共享属性和 RPC 的操作。

### 1.3 重要说明

平台只支持通过 MQTT 向设备推送下行数据，不开放 HTTP 下行接口。

平台不能通过 MQTT 直接向设备写遥测。遥测是设备向平台上报的数据；平台向设备下发数据时，应使用共享属性或 RPC。

### 1.4 前置条件

- 设备已在平台创建，并取得设备访问令牌；
- 设备已连接到平台 MQTT 服务；
- 设备已订阅共享属性主题或 RPC 主题；
- 设备在线，或设备支持重连后重新订阅；
- 平台账号具备设备操作权限。

### 1.5 相关文档

- [设备管理使用手册](设备管理使用手册.md)
- [网关功能使用手册](网关功能使用手册.md)
- [规则引擎使用手册](规则引擎使用手册.md)
- [多设备场景联动使用手册](多设备场景联动使用手册.md)
- [物模型定义规范使用手册](物模型定义规范使用手册.md)
- [设备下行接收示例](../examples/device-downlink-client/README.md)

---

## 2. 下行方式

平台向设备推送数据主要有两种方式：

| 方式 | 用途 | 设备是否必须响应 |
| --- | --- | --- |
| 共享属性 | 下发配置、阈值、期望状态 | 否 |
| RPC | 下发命令、读取状态 | 单向否，双向是 |

### 2.1 共享属性

共享属性适合：

- 配置下发；
- 采集周期、上报周期；
- 告警阈值；
- 设备期望状态；
- 需要设备重连后再次获取的配置。

共享属性保存在平台。设备订阅共享属性主题后：

- 首次订阅时会收到当前共享属性快照；
- 平台修改共享属性后，设备会收到增量更新；
- 设备离线期间修改的共享属性，在设备重新订阅后可以再次获取。

### 2.2 RPC

RPC 适合：

- 立即执行的命令；
- 控制开关、模式、参数；
- 读取设备当前状态；
- 需要设备返回执行结果的场景。

RPC 分为：

| 类型 | 说明 |
| --- | --- |
| 单向 RPC | 平台只下发请求，不等待设备响应 |
| 双向 RPC | 平台等待设备响应，超时则失败 |

### 2.3 不使用的下行方式

以下方式不是平台主动推送：

- 服务端属性：设备主动请求后由平台返回；
- 客户端属性：设备主动上报，平台保存；
- 遥测：设备向平台上报告，不是平台向设备下发。

---

## 3. MQTT 连接参数

设备使用访问令牌连接平台 MQTT 服务。

| 参数 | 说明 |
| --- | --- |
| Host | 平台 MQTT 地址 |
| Port | `1883` 或 TLS `8883` |
| 客户端标识 | 建议使用设备名称或设备唯一标识 |
| 用户名 | 设备访问令牌 |
| 密码 | 空 |
| 心跳间隔 | 60 秒 |
| 清理会话 | 按设备能力配置 |
| QoS | 建议 `1` |

### 3.1 下行主题

| 主题 | 方向 | 用途 |
| --- | --- | --- |
| `v1/devices/me/attributes` | 下行 | 接收共享属性 |
| `v1/devices/me/rpc/request/+` | 下行 | 接收 RPC 请求 |
| `v1/devices/me/rpc/response/{requestId}` | 上行 | 返回 RPC 响应 |

设备连接成功后应立即订阅：

```text
v1/devices/me/attributes
v1/devices/me/rpc/request/+
```

---

## 4. 推送共享属性

### 4.1 平台页面操作

1. 进入「设备」页面。
2. 打开目标设备详情。
3. 进入「属性」页签。
4. 选择「共享属性」或 `SHARED_SCOPE`。
5. 新增或修改属性键值。
6. 保存。

示例共享属性：

```json
{
  "reportInterval": 30,
  "alarmThreshold": 85,
  "mode": 1,
  "relay": false
}
```

### 4.2 设备收到的报文

设备订阅 `v1/devices/me/attributes` 后，会收到类似报文：

```json
{
  "reportInterval": 30,
  "alarmThreshold": 85,
  "mode": 1,
  "relay": false
}
```

平台只推送发生变化的键时，设备应按增量方式更新本地配置，不要假设每次报文都包含全部属性。

### 4.3 首次订阅

设备首次订阅共享属性主题时，平台会返回当前共享属性快照。设备应：

- 将快照合并到本地配置；
- 保存最新配置；
- 在重连后重新订阅并重新合并。

### 4.4 设备应用配置

设备收到共享属性后，建议：

1. 校验键名和类型；
2. 应用配置；
3. 记录当前配置版本或更新时间；
4. 关键配置应用后，通过遥测或客户端属性上报执行结果；
5. 不要只依赖 MQTT QoS 确认，QoS 只表示消息到达，不表示业务执行成功。

---

## 5. 下发 RPC

### 5.1 平台页面操作

1. 进入「设备」页面。
2. 打开目标设备详情。
3. 打开 RPC 或命令下发入口。
4. 选择单向或双向 RPC。
5. 填写方法名和参数。
6. 发送。

示例方法：

```json
{
  "method": "setMode",
  "params": {
    "mode": 1
  }
}
```

设置继电器：

```json
{
  "method": "setRelay",
  "params": {
    "on": true
  }
}
```

应用配置：

```json
{
  "method": "applyConfig",
  "params": {
    "reportInterval": 30
  }
}
```

### 5.2 设备收到的 RPC 请求

设备订阅：

```text
v1/devices/me/rpc/request/+
```

平台下发后，设备收到类似报文：

```json
{
  "method": "setMode",
  "params": {
    "mode": 1
  }
}
```

主题末尾是本次请求的 `requestId`，例如：

```text
v1/devices/me/rpc/request/15
```

其中 `15` 是设备回复时使用的请求 ID。

### 5.3 设备返回 RPC 响应

双向 RPC 必须回复：

```text
v1/devices/me/rpc/response/{requestId}
```

响应内容可以是任意合法 JSON：

```json
{
  "result": "ok",
  "mode": 1
}
```

失败示例：

```json
{
  "error": "invalid mode"
}
```

单向 RPC 不要求回复，但设备仍可以回复；平台不会等待该响应。

### 5.4 RPC 超时

- 双向 RPC 有超时限制；
- 设备离线、未订阅主题或未及时回复时，平台会判定超时；
- 设备应在超时前完成处理并发送响应；
- 执行时间较长的操作，建议先返回“已接受”，再通过遥测上报最终结果。

### 5.5 方法与物模型行为

物模型中的行为 `id` 可作为 RPC 方法名。例如：

```json
{
  "id": "setMode",
  "name": "设置运行模式"
}
```

设备收到：

```json
{
  "method": "setMode",
  "params": {
    "mode": 1
  }
}
```

标准示例物模型还包含：

- `setRelay`：参数 `on`，布尔值；
- `applyConfig`：参数 `reportInterval`，整数，单位秒。

平台也可以使用通用方法 `set` 下发共享属性类配置：

```json
{
  "method": "set",
  "params": {
    "reportInterval": 30
  }
}
```

---

## 6. 示例代码

以下示例只使用 MQTT，不依赖 HTTP 接口。

示例中的属性、事件和行为来自标准示例物模型：

[standard-thing-model.tsl.json](examples/standard-thing-model.tsl.json)

### 6.1 Python 设备端示例

依赖：

```bash
python -m pip install paho-mqtt
```

示例代码：

```python
import json
import os
import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOKEN = os.getenv("ACCESS_TOKEN")
CLIENT_ID = os.getenv("DEVICE_NAME", "device-01")

if not TOKEN:
    raise SystemExit("ACCESS_TOKEN is required")

config = {
    "reportInterval": 60,
    "alarmThreshold": 80,
    "mode": 0,
    "relay": False,
}


def create_client():
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=CLIENT_ID,
            protocol=mqtt.MQTTv311,
        )
    return mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)


def on_connect(client, userdata, flags, reason_code, properties=None):
    client.subscribe("v1/devices/me/attributes", qos=1)
    client.subscribe("v1/devices/me/rpc/request/+", qos=1)
    print("connected")


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except Exception as exc:
        print(f"invalid payload: {exc}")
        return

    if not isinstance(payload, dict):
        print("payload must be a JSON object")
        return

    if message.topic == "v1/devices/me/attributes":
        config.update(payload)
        print(f"shared attributes: {config}")
        return

    if message.topic.startswith("v1/devices/me/rpc/request/"):
        request_id = message.topic.rsplit("/", 1)[-1]
        method = payload.get("method")
        params = payload.get("params") or {}

        if method == "set":
            config.update(params)
            result = {"result": "ok", "config": config}

        elif method == "setMode":
            mode = params.get("mode")
            if mode not in (0, 1, 2):
                result = {"error": "invalid mode"}
            else:
                config["mode"] = mode
                result = {"result": "ok", "mode": mode}

        elif method == "setRelay":
            on = params.get("on")
            if not isinstance(on, bool):
                result = {"error": "invalid relay state"}
            else:
                config["relay"] = on
                result = {"result": "ok", "relay": on}

        elif method == "applyConfig":
            report_interval = params.get("reportInterval")
            if not isinstance(report_interval, int) or not 5 <= report_interval <= 3600:
                result = {"error": "invalid reportInterval"}
            else:
                config["reportInterval"] = report_interval
                result = {"result": "ok", "reportInterval": report_interval}

        else:
            result = {"error": f"unsupported method: {method}"}

        client.publish(
            f"v1/devices/me/rpc/response/{request_id}",
            json.dumps(result, ensure_ascii=False),
            qos=1,
        )
        print(f"rpc response: {result}")


client = create_client()
client.username_pw_set(TOKEN, "")
client.on_connect = on_connect
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=30)
client.connect(HOST, PORT, keepalive=60)
client.loop_forever()
```

### 6.2 TLS 连接示例

使用 `8883` 端口时增加 TLS 配置：

```python
client.tls_set()
client.connect(HOST, 8883, keepalive=60)
```

生产环境应正确配置 CA 证书和服务端主机名校验。

### 6.3 使用 MQTT 客户端订阅验证

使用测试设备，或先停止真实设备，避免同一 Token 多客户端互相影响。

订阅共享属性：

```bash
mosquitto_sub \
  -h "$MQTT_HOST" -p 1883 \
  -i "$DEVICE_NAME" \
  -u "$ACCESS_TOKEN" \
  -t "v1/devices/me/attributes" -v
```

订阅 RPC：

```bash
mosquitto_sub \
  -h "$MQTT_HOST" -p 1883 \
  -i "$DEVICE_NAME" \
  -u "$ACCESS_TOKEN" \
  -t "v1/devices/me/rpc/request/+" -v
```

回复双向 RPC：

```bash
mosquitto_pub \
  -h "$MQTT_HOST" -p 1883 \
  -i "$DEVICE_NAME" \
  -u "$ACCESS_TOKEN" \
  -t "v1/devices/me/rpc/response/<requestId>" \
  -m '{"result":"ok"}'
```

### 6.4 设备端处理建议

- 连接成功后立即订阅共享属性和 RPC 主题；
- 断线重连后重新订阅；
- 处理重复 RPC 时使用 `requestId` 做幂等；
- `params` 必须是 JSON 对象；
- 双向 RPC 必须回复，且主题中的 `requestId` 必须与请求一致；
- 不要忽略 `set` 方法和物模型行为方法；
- 不要在代码中硬编码真实 Access Token。

---

## 7. 网关子设备下行

如果设备通过网关接入，平台通常将下行数据发送给网关，由网关转发给子设备。

注意事项：

- 网关必须在线；
- 网关需要正确处理子设备 RPC 和属性更新；
- 子设备不要直接使用平台设备 Token 连接 MQTT；
- 网关模式下的 RPC 主题和转发方式见 [网关功能使用手册](网关功能使用手册.md)；
- 如果子设备支持直连，优先使用直连 MQTT 方式，链路更简单。

---

## 8. 验证和排查

### 8.1 验证共享属性

1. 确认设备在线；
2. 使用 `mosquitto_sub` 订阅 `v1/devices/me/attributes`；
3. 在平台设备详情修改共享属性；
4. 确认设备收到新属性；
5. 确认设备应用配置并上报结果。

### 8.2 验证 RPC

1. 确认设备已订阅 `v1/devices/me/rpc/request/+`；
2. 在平台设备详情发送 RPC；
3. 确认设备收到方法名和参数；
4. 确认设备回复 `v1/devices/me/rpc/response/{requestId}`；
5. 双向 RPC 确认平台收到响应。

### 8.3 常见问题

| 问题 | 排查 |
| --- | --- |
| 设备收不到共享属性 | 检查是否订阅 `v1/devices/me/attributes`，是否使用正确设备 Token |
| 设备收不到 RPC | 检查是否订阅 `v1/devices/me/rpc/request/+`，设备是否在线 |
| 双向 RPC 超时 | 检查设备是否回复、`requestId` 是否正确、处理是否超过超时时间 |
| RPC 回复后被判定失败 | 检查响应主题、响应 JSON 格式和 QoS |
| 设备重连后收不到配置 | 检查重连后是否重新订阅共享属性主题 |
| 共享属性没有变化 | 检查是否修改了 `SHARED_SCOPE`，而不是服务端属性或客户端属性 |
| 同一个 Token 多客户端互相影响 | 使用不同设备或测试设备，不要重复使用同一设备身份 |
| TLS 连接失败 | 检查端口、CA 证书、主机名和服务器时间 |

---

## 9. 安全建议

- Access Token 等同于设备密码，不要写入公开代码或文档；
- 示例代码从环境变量读取 Token；
- 生产环境优先使用 TLS `8883`；
- 不要在客户端日志中打印完整 Token；
- 定期轮换设备 Token；
- 不同设备使用不同 Token；
- 对关键 RPC 做权限校验、参数校验和幂等处理；
- 对配置下发和命令执行记录审计日志。

---

## 10. 常见问题

### 10.1 平台能否直接给设备推送遥测？

不能。遥测是设备上报的数据。平台向设备下发数据应使用共享属性或 RPC。

### 10.2 共享属性和服务端属性有什么区别？

共享属性可由平台主动推送给设备；服务端属性通常由设备主动请求后读取。

### 10.3 单向 RPC 需要回复吗？

不需要。但设备可以回复，平台不会等待该回复。

### 10.4 双向 RPC 没有回复会怎样？

平台会在超时后判定失败；设备离线时也可能直接返回超时或不可达。

### 10.5 设备重连后需要重新订阅吗？

需要。建议设备每次连接成功后重新订阅共享属性和 RPC 主题。

### 10.6 可以使用同一个 Token 启动多个客户端吗？

不建议。多个客户端共用同一设备身份可能导致连接互相影响。测试时请使用测试设备或独立 Token。

### 10.7 为什么修改了属性但设备没收到？

确认修改的是共享属性 `SHARED_SCOPE`，并且设备已订阅 `v1/devices/me/attributes`。修改服务端属性不会自动推送到设备。

### 10.8 为什么 RPC 方法找不到？

确认方法名与物模型行为 `id` 一致，且设备端实现了对应方法；平台不会替设备执行未实现的方法。

---

## 11. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-11-06 | 初版 |
