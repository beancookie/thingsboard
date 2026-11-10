# DLT645 电表 MQTT 模拟器

位于 `tools/src/main/python/meter-simulator/`，包含电表模拟脚本、物模型和单元测试，只依赖 `paho-mqtt`。

## 文件

- `simulate_meter.py`：模拟电表，上报遥测和事件，处理共享属性和 RPC。
- `meter-thing-model.tsl.json`：电表物模型。
- `test_simulate_meter.py`：单元测试。
- `requirements.txt`：Python 依赖。

## 安装

```powershell
python -m pip install -r requirements.txt
```

## 运行

先检查报文，不连接服务器：

```powershell
python simulate_meter.py --dry-run
```

短时发送 3 轮：

```powershell
python simulate_meter.py --count 3 --interval 5
```

持续运行，每 5 秒上报遥测，每 30 秒上报一个事件：

```powershell
python simulate_meter.py --interval 5 --event-interval 30
```

## 默认连接参数

| 参数 | 值 |
| --- | --- |
| MQTT Host | `129.211.241.31` |
| MQTT Port | `1883` |
| 用户名 | 设备 Access Token `<ACCESS_TOKEN>` |
| 密码 | 空 |
| Client ID | `meter-YUMRMRPOGPA` |
| QoS | `1` |
| Keepalive | `60` 秒 |

可用 `--mqtt-host`、`--mqtt-port`、`--token`、`--client-id` 覆盖，也可使用环境变量 `MQTT_HOST`、`MQTT_PORT`、`ACCESS_TOKEN`、`MQTT_CLIENT_ID`。

## 平台下发

脚本订阅：

- `v1/devices/me/attributes`
- `v1/devices/me/rpc/request/+`

支持：

- 共享属性 `reportInterval`、`relay`、`relayState`
- RPC `setRelay`
- RPC `applyConfig`
- RPC `syncTime`
- 通用 RPC `set`

RPC 响应发布到 `v1/devices/me/rpc/response/{requestId}`。

## 测试

```powershell
python -m unittest test_simulate_meter.py -v
```
