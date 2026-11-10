# ThingsBoard 数据模拟与设备工具

用于向 ThingsBoard 模拟上报物模型数据，验证 Device Profile、规则链和 Kafka 出口。

## 环境要求

- Python 3.9+
- thing-model 已启动
- ThingsBoard 已启动
- 产品已同步；规则链由产品发布/同步自动生成
- 产品 Asset 上存在 `tsl_schema`（模拟脚本会复制到测试设备，便于兼容旧行为）
- ThingsBoard 账号具备 `TENANT_ADMIN` 权限

安装依赖：

```bash
python -m pip install -r tools/src/main/python/simulators/requirements.txt
```

## 基本用法

```bash
python tools/src/main/python/simulators/simulate_telemetry.py
```

默认行为：

- 登录 ThingsBoard
- 读取产品 `9HYN9PJNOY` 的物模型目录
- 创建临时测试设备并绑定产品 Device Profile
- 写入 `tsl_schema`、`tsl_version`、`tenant_id`、`device_uuid`、`site_code`、`product_id`
- 按 `mixed` 模式循环发送：
  - 属性遥测
  - 事件
- 退出时删除临时设备

### 按本地 TSL 生成 4DZDCQUA2D 数据

```powershell
python tools/src/main/python/simulators/simulate_telemetry.py `
  --product-id 4DZDCQUA2D `
  --tsl thing-model/migrate/4DZDCQUA2D.tsl.json `
  --mode mixed --count 2 --seed 1
```

属性/事件定义来源：

- 不传 `--tsl` 时，脚本会调用 `GET /api/products/{id}/thing-model` 获取产品最新完整 TSL，因此 `deviceInfo`、`locationInfo`、`realStateInfo` 等 struct 会生成完整字段；接口不可用时回退到 catalog。
- 指定 `--tsl` 后，属性/事件定义以本地 TSL 为准：
  - struct 属性按 `define.specs` 生成扁平 JSON 对象。
  - 事件 payload 默认放在 `events` 数组中，仅包含事件 params 以及 `event_id/event_type/event_ts`，也兼容用 `id` 表示事件标识（`event_id` 优先），不包含属性数据。
  - 发送真实遥测要求产品已同步（`tbProfileId`、`tbAssetId`、`tsl_schema`）。
  - actions 不模拟，因为行为是平台到设备的 RPC，不是遥测上报。

## 导入产品与物模型

`import_products.py` 把本地物模型 JSON 批量导入 thing-model，并自动发布为产品。产品发布会创建 Device Profile、产品资产和同名规则链。

`thing-model/migrate/integrated` 下的 8 个物模型默认使用：

- 文件名作为产品名称，例如 `CoAP姿态监测仪.json` → `CoAP姿态监测仪`
- `profile.ProductId` 作为产品 ID 和型号
- `profile.CategoryId` 作为分类
- 文件 `version` 作为 TSL 版本

先 dry-run 检查映射：

```powershell
python tools/src/main/python/simulators/import_products.py `
  --products-dir thing-model/migrate/integrated `
  --output-dir . `
  --dry-run
```

导入到本地环境：

```powershell
python tools/src/main/python/simulators/import_products.py `
  --tb-url http://localhost:18080 `
  --thingmodel-url http://localhost:8090 `
  --products-dir thing-model/migrate/integrated `
  --output-dir . `
  --password tenant
```

导入到线上网关：

```powershell
python tools/src/main/python/simulators/import_products.py `
  --tb-url https://thingsboard.zhgcloud.com `
  --thingmodel-url https://thingsboard.zhgcloud.com/api/thing-model `
  --products-dir thing-model/migrate/integrated `
  --output-dir .\import-output
```

使用 ThingsBoard API Key：

```powershell
$env:TB_API_KEY = "tb_xxx"
python tools/src/main/python/simulators/import_products.py `
  --tb-url https://thingsboard.zhgcloud.com `
  --thingmodel-url https://thingsboard.zhgcloud.com/api/thing-model `
  --products-dir thing-model/migrate/integrated `
  --output-dir .\import-output
```

也可以直接传 `--api-key tb_xxx`。脚本会把密钥作为 `X-Authorization: ApiKey tb_xxx` 发送，不再登录获取 JWT。

说明：

- `--thingmodel-url` 可填 thing-model 服务根地址（如 `http://localhost:8090`），也可填网关前缀（如 `https://thingsboard.zhgcloud.com/api/thing-model`）。
- 未设置 `--password` 或 `TB_PASSWORD` 时交互式提示输入密码，账号需为 `TENANT_ADMIN`。
- `--api-key` / `TB_API_KEY` 优先于账号密码；使用前需确认 thing-model 服务端为支持 API Key 的版本，且密钥对应用户具备 `TENANT_ADMIN` 权限。
- 默认先调用 validate 接口校验物模型，校验失败不会落库。
- 默认跳过线上已存在的 ProductId；使用 `--update-existing` 重新提交。
- ProductId 全系统唯一，被其他租户占用时返回 `conflict`。
- 租户未配置厂商服务账号时会提示 `TENANT_ACCOUNT_MISSING`，需系统管理员先执行 `provision-auto`。
- 每次执行生成 `product-import-report.csv`，包含产品状态、Device Profile、资产和规则链 ID。

## 导出产品与物模型

`export_products.py` 从运行中的平台导出产品列表和完整 TSL，适合备份或迁移。

```powershell
$env:TB_API_KEY = "tb_xxx"

python tools/src/main/python/simulators/export_products.py `
  --tb-url https://thingsboard.zhgcloud.com `
  --thingmodel-url https://thingsboard.zhgcloud.com/api/thing-model `
  --output-dir .\product-export
```

默认导出全部产品；只导出指定产品时重复传 `--product-id`：

```powershell
python tools/src/main/python/simulators/export_products.py `
  --product-id YUMRMRPOGPA `
  --product-id SCENE_LIGHT `
  --output-dir .\product-export
```

输出：

```text
product-export/
├── products.csv              # 产品元数据汇总（utf-8-sig）
├── products.json             # 产品列表与详情
└── tsl/
    └── <productId>.tsl.json  # 每个产品的完整 TSL
```

说明：

- 未传 `--api-key`/`TB_API_KEY` 时回退到用户名密码，可用 `--username` / `--password` / `TB_PASSWORD`。
- API Key 会先换取 JWT；产品接口不接受裸 ApiKey 头。
- `--no-detail` 可跳过每个产品的详情请求，只导出列表与 TSL。
- 单个产品失败会记录到 CSV 的 `error` 列并继续，最终以非 0 退出码结束。

## 场景联动演示

`thing-model/migrate/scenes` 提供多设备场景联动演示物模型：

```text
场景人体感应器.json    SCENE_MOTION
场景光照传感器.json    SCENE_LIGHT_SENSOR
场景灯.json            SCENE_LIGHT
场景温度传感器.json    SCENE_TEMPERATURE
场景空调.json          SCENE_AIR_CONDITIONER
```

### 1. 导入演示产品

```powershell
$env:TB_API_KEY = "tb_xxx"

python tools/src/main/python/simulators/import_products.py `
  --tb-url https://thingsboard.zhgcloud.com `
  --thingmodel-url https://thingsboard.zhgcloud.com/api/thing-model `
  --products-dir thing-model/migrate/scenes `
  --output-dir .\import-output\scene-demo
```

### 2. 创建设备和关系

```powershell
python tools/src/main/python/simulators/create_scene_demo.py `
  --tb-url https://thingsboard.zhgcloud.com `
  --thingmodel-url https://thingsboard.zhgcloud.com/api/thing-model `
  --output-dir .\import-output\scene-demo
```

脚本会创建：

```text
motion-01
light-sensor-01
light-01
temperature-01
air-conditioner-01
```

并创建关系：

```text
motion-01        --Controls-->     light-01
motion-01        --ConnectedTo-->  light-sensor-01
temperature-01   --Controls-->     air-conditioner-01
```

生成 `import-output/scene-demo/scene-devices.csv`，包含设备 Access Token。

### 3. 运行场景模拟器

```powershell
python tools/src/main/python/simulators/simulate_scene_demo.py `
  --devices-csv .\import-output\scene-demo\scene-devices.csv `
  --mqtt-host 129.211.241.31 --mqtt-port 1883 `
  --interval 3
```

- 传感器设备持续上报遥测；
- `light-01` 订阅 RPC，支持 `setState`；
- `air-conditioner-01` 订阅 RPC，支持 `setMode`；
- 收到 RPC 后更新状态、上报遥测并回复响应。

## 电表设备 MQTT Mock

电表模拟器已迁移为文档示例：[DLT645 电表 MQTT 模拟器](../../../../docs/examples/dlt645-meter-simulator/README.md)。

示例代码位于 `docs/examples/dlt645-meter-simulator/`，并同时提供 HTTP / CoAP 版本。

## 注册设备

`register_devices.py` 按产品 Device Profile 注册设备，写入设备 server 属性，并把 Access Token 导出到 CSV。

单个设备：

```powershell
python tools/src/main/python/simulators/register_devices.py `
  --product-id 4DZDCQUA2D `
  --name 4DZDCQUA2D-0001 `
  --output device-credentials.csv `
  --password tenant
```

批量生成：

```powershell
python tools/src/main/python/simulators/register_devices.py `
  --product-id 4DZDCQUA2D `
  --prefix 4DZDCQUA2D --count 10 `
  --site-code SIM `
  --output device-credentials.csv `
  --password tenant
```

说明：

- 设备名通过 `--name` 指定（可重复），或通过 `--prefix` + `--count` 批量生成，两种方式二选一。
- 已存在的同名设备默认跳过，并在 CSV 中标记 `skipped`，脚本可重复执行。
- 产品必须已同步，缺少 `tbProfileId`、`tbAssetId`、`tenantId` 时脚本直接报错。
- 每个新设备会写入 `tsl_schema`、`tsl_version`、`tenant_id`、`device_uuid`、`site_code`、`product_id`。

CSV 列：

```text
product_id, device_name, device_id, access_token, tsl_version,
profile_id, profile_name, site_code, relation_type, relation_status,
status, error, created_at
```

> CSV 包含完整 Access Token，请妥善保管，不要提交到代码仓库。

### 向注册设备批量发送

使用注册脚本生成的 CSV，按本地 TSL 生成数据并批量发送：

```powershell
python tools/src/main/python/simulators/simulate_telemetry.py `
  --product-id 4DZDCQUA2D `
  --tsl thing-model/migrate/4DZDCQUA2D.tsl.json `
  --devices-csv device-credentials-4DZDCQUA2D.csv `
  --mode mixed --count 2 --workers 10 --interval 0 `
  --password tenant
```

说明：

- 只处理 CSV 中 `access_token` 非空的设备。
- `--count` 是每台设备发送的消息数；`mixed` 按 telemetry/event 循环。
- `--workers` 控制并发设备数。
- 批量模式不会创建或删除设备，也不要求 `tbProfileId/tbAssetId/tsl_schema`。

## Gateway 推送

Gateway 方式使用网关设备 Token 连接 MQTT，由网关代多台预创建子设备上报。

前置条件：

- 网关设备已注册，并导出 `gateway-credentials.csv`。
- 网关设备必须开启 Gateway 模式：`additionalInfo.gateway = true`。ThingsBoard UI 中勾选 “Is gateway”，或 REST 请求体带 `"additionalInfo":{"gateway":true}`；否则发布 `v1/gateway/*` 会报 `gatewaySessionHandler is null`。
- 子设备已通过 `register_devices.py` 预创建在产品 Device Profile 下。

> 当前 `register_devices.py` 只注册产品子设备；网关设备需通过 ThingsBoard UI 或 REST 创建。

一键创建网关与子设备（按物模型目录批量）：

```powershell
python tools/src/main/python/simulators/setup_gateway.py `
  --tb-url http://localhost:18080 `
  --thingmodel-url http://localhost:8090 `
  --username tenant@thingsboard.org `
  --password tenant `
  --gateway-name gateway-01 `
  --products-dir thing-model/migrate/integrated `
  --count 1 `
  --site-code SIM `
  --output-dir .
```

- 每个物模型创建 1 台子设备，命名 `<ProductId>-01`。
- 默认关系类型为 `Contains`，与平台标准关系及网关 Dashboard 保持一致。
- 脚本幂等，可重复执行；生成的 CSV 含 Access Token。
- 脚本不负责导入/同步产品，需先用 `import_products.py` 导入物模型。
- 可使用 `--api-key` 或 `TB_API_KEY` 代替 `--username` / `--password`。

注册子设备：

```powershell
python tools/src/main/python/simulators/register_devices.py `
  --product-id 4DZDCQUA2D `
  --prefix 4DZDCQUA2D-gw --count 2 `
  --site-code SIM `
  --output sub-devices.csv `
  --password tenant
```

运行 Gateway 推送：

```powershell
python tools/src/main/python/simulators/simulate_gateway.py `
  --gateway-csv gateway-credentials.csv `
  --gateway-name gateway-01 `
  --sub-devices-csv sub-devices.csv `
  --product-id 4DZDCQUA2D `
  --mode mixed --count 2 --interval 1
```

两个网关分担多台设备，并按每 10 台合并发送：

```powershell
python tools/src/main/python/simulators/simulate_gateway.py `
  --gateway-csv gateway-credentials.csv `
  --gateway-names gateway-01,gateway-02 `
  --sub-devices-csv sub-devices-50.csv `
  --product-id 4DZDCQUA2D `
  --mode mixed --count 2 --interval 1 `
  --batch-size 10 --quiet
```

说明：

- 脚本发送 `v1/gateway/connect`、`v1/gateway/telemetry`、`v1/gateway/disconnect`。
- 不传 `--tsl` 时自动从平台获取产品最新 TSL。
- 每个子设备使用自己的 Device Profile 规则链。
- `sub-devices.csv` 中的 `access_token` 不会被 Gateway 脚本使用。
- `--gateway-names` 支持多个网关，子设备按轮询平均分配。
- `--batch-size` 控制每条 gateway telemetry 合并多少台子设备，默认 10。
- `--quiet` 只输出批次进度和汇总，不打印完整 payload。
- `--dry-run` 只打印报文，不连接 MQTT。
- `--events-per-packet` 控制每包事件数量，默认 4。
- 如果本机 Python 受 `HTTP_PROXY`/`HTTPS_PROXY` 影响导致平台 TSL 获取超时，增加 `--tsl thing-model/migrate/4DZDCQUA2D.tsl.json`。

多产品持续 mock（一个网关、多个产品）：

```powershell
python tools/src/main/python/simulators/simulate_gateway_all.py `
  --gateway-csv gateway-credentials.csv `
  --gateway-name gateway-01 `
  --sub-devices-csv sub-devices.csv `
  --tsl-dir thing-model/migrate/integrated `
  --mqtt-host localhost --mqtt-port 1883 `
  --mode auto --interval 1 --quiet
```

- 只建立一条 MQTT 连接，网关保持在线。
- 按 `sub-devices.csv` 的 `product_id` 自动分组，每个产品使用自己的 TSL。
- `--mode auto`：有事件的产品用 `mixed`，无事件的用 `telemetry`。
- `--count 0` 默认无限循环，Ctrl+C 发送 disconnect 并退出。
- `--tsl-dir` 优先使用本地物模型文件，缺失时才回退到 thing-model 获取。
- 默认同时 mock 网关自身：写入 `Status/Name/Type/Version/active_connectors/general_configuration`，发布 `serviceStats/machineStats/ALL_ERRORS_COUNT`，网关在运行期间保持在线。
- 网关 mock 需要 `TENANT_ADMIN` 账号；可用 `--password` / `TB_PASSWORD`，也可用 `--api-key` / `TB_API_KEY`。
- `--mqtt-client-id` 可覆盖 MQTT Client ID，默认使用网关名。
- `--no-gateway-mock` 可关闭网关自身 mock。
- `--gateway-version`、`--gateway-type`、`--connectors` 可自定义网关属性。
- 先用 `--dry-run --count 1` 检查报文。

线上 MQTT 持续 mock：

```powershell
$env:TB_API_KEY = "tb_xxx"

python tools/src/main/python/simulators/simulate_gateway_all.py `
  --tb-url https://thingsboard.zhgcloud.com `
  --thingmodel-url https://thingsboard.zhgcloud.com/api/thing-model `
  --gateway-csv .\import-output\gateway-credentials.csv `
  --gateway-name "中铁物联网融合终端" `
  --sub-devices-csv .\import-output\sub-devices.csv `
  --tsl-dir thing-model/migrate/integrated `
  --mqtt-host 129.211.241.31 --mqtt-port 1883 `
  --mqtt-client-id zhgcloud-gw-mock `
  --mode auto --count 0 --interval 1 --quiet
```

## Windows 协议连接器模拟

Windows 主机运行协议模拟器，Docker Desktop 运行 `tb-gateway`。每次启动只使用
`--protocol` 指定的一个协议，不混用、不自动切换。

支持：

| 协议 | Windows 模拟器 | 网关侧访问地址 |
| --- | --- | --- |
| `modbus` | Modbus TCP Slave，端口 5021 | `host.docker.internal:5021` |
| `opcua` | OPC-UA Server，端口 4840 | `opc.tcp://host.docker.internal:4840` |
| `s7` | Snap7 S7 Server，端口 1102 | `host.docker.internal:1102` |
| `can` | `python-can` `udp_multicast` | 组播 `239.255.0.1:15000` |
| `odbc` | PostgreSQL 数据表，端口 5433 | `odbc-db:5432` |

安装依赖：

```powershell
python -m pip install -r tools/src/main/python/simulators/requirements.txt
```

### 脚本运行顺序

模拟器和网关是独立进程，建议按以下顺序启动。以 Modbus 为例：

1. 创建网关和子设备，生成 `gateway-credentials.csv`、`sub-devices.csv`。
2. 生成当前协议的连接器映射和 `tb-gateway` 配置。
3. 在 Windows 终端 A 启动协议模拟器，例如 Modbus Slave。
4. 在终端 B 启动或重启 `tb-gateway`，让它加载第 2 步生成的配置。
5. 在终端 C 启动数据写入脚本，向模拟器写入数据。
6. `tb-gateway` 读取模拟器数据，通过 MQTT 上报 ThingsBoard。

数据流：

```text
simulate_gateway_all.py  ->  Modbus Client，写寄存器
run_protocol_sim.py      ->  Modbus Slave/Server，保存寄存器
tb-gateway Modbus 连接器 ->  Modbus Master/Client，轮询读取
tb-gateway               ->  MQTT Client，上报 ThingsBoard
```

注意：

- `tb-gateway` 是 Modbus 主站/客户端，不是 Modbus 从设备。
- Windows 上的 `run_protocol_sim.py` 才是 Modbus 从设备/服务器。
- 切换协议后必须重新生成配置并重启 `tb-gateway`。
- 如果 `sub-devices.csv` 已存在，可以跳过第 1 步。

准备网关与子设备 CSV：

```powershell
python tools/src/main/python/simulators/setup_gateway.py `
  --gateway-name gateway-01 `
  --products-dir thing-model/migrate/integrated `
  --count 1 `
  --output-dir .
```

生成单协议映射和网关配置：

```powershell
python tools/src/main/python/simulators/generate_gateway_config.py `
  --protocol modbus `
  --sub-devices-csv sub-devices.csv `
  --output-dir thing-model/docker/gateway-sim/config
```

启动 Windows 模拟器：

```powershell
python tools/src/main/python/simulators/run_protocol_sim.py `
  --protocol modbus `
  --mapping thing-model/docker/gateway-sim/config/connector-mapping-modbus.json
```

启动网关：

```powershell
Copy-Item thing-model/docker/gateway-sim/.env.example thing-model/docker/gateway-sim/.env
# 编辑 .env，填入网关 Access Token
docker compose -f thing-model/docker/gateway-sim/docker-compose.yml up -d --build
```

发送数据：

```powershell
python tools/src/main/python/simulators/simulate_gateway_all.py `
  --protocol modbus `
  --mapping thing-model/docker/gateway-sim/config/connector-mapping-modbus.json `
  --sub-devices-csv sub-devices.csv `
  --tsl-dir thing-model/migrate/integrated `
  --count 0 --interval 1 --quiet
```

说明：

- 切换协议时，重新执行 `generate_gateway_config.py --protocol <协议>`，重启
  `tb-gateway`，再用相同 `--protocol` 启动模拟器和数据脚本。
- `--protocol mqtt` 仍保持原有 `v1/gateway/*` MQTT 模拟方式。
- 协议模式只发送属性遥测；TSL 事件暂不通过协议连接器发送。
- Windows 不支持 SocketCAN，CAN 使用 `udp_multicast`；需在防火墙放行对应 UDP 端口。
- ODBC 使用 `thing-model/docker/gateway-sim/docker-compose.yml` 中的 PostgreSQL，
  Windows 侧写入 `127.0.0.1:5433`，网关侧访问 `odbc-db:5432`。
- 不要提交 `.env`、`gateway-credentials.csv`、`sub-devices.csv` 或 Access Token。


## 密码
推荐使用环境变量：

```powershell
$env:TB_PASSWORD = "tenant"
python tools/src/main/python/simulators/simulate_telemetry.py --count 10 --interval 2
```

未设置 `TB_PASSWORD` 时脚本会交互式提示输入密码。

`import_products.py` 和 `setup_gateway.py` 也支持 ThingsBoard API Key：

```powershell
$env:TB_API_KEY = "tb_xxx"
```

API Key 会以 `X-Authorization: ApiKey tb_xxx` 发送；`import_products.py` 要求 thing-model 服务端支持 API Key 认证。

## 常用示例

只发送正常遥测：

```bash
python tools/src/main/python/simulators/simulate_telemetry.py --mode telemetry --count 20
```

只发送事件：

```bash
python tools/src/main/python/simulators/simulate_telemetry.py --mode event --count 5
```

只发送非法数据：

```bash
python tools/src/main/python/simulators/simulate_telemetry.py --mode invalid --count 5
```

发送 10 条混合消息，间隔 1 秒：

```bash
python tools/src/main/python/simulators/simulate_telemetry.py --mode mixed --count 10 --interval 1
```

保留测试设备：

```bash
python tools/src/main/python/simulators/simulate_telemetry.py --keep-device
```

指定产品和设备名：

```bash
python tools/src/main/python/simulators/simulate_telemetry.py \
  --product-id 9HYN9PJNOY \
  --device-name my-sim-device \
  --count 5
```

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--tb-url` | `http://localhost:18080` | ThingsBoard 地址 |
| `--thingmodel-url` | `http://localhost:8090` | thing-model 地址 |
| `--username` | `tenant@thingsboard.org` | ThingsBoard 租户管理员 |
| `--password` | `TB_PASSWORD` | ThingsBoard 密码 |
| `--product-id` | `9HYN9PJNOY` | 产品 ID |
| `--tsl` | 空 | 本地 TSL JSON 文件；不传时从平台获取最新 TSL，指定后覆盖平台 TSL |
| `--device-name` | `sim-<product>-<timestamp>-<random>` | 测试设备名 |
| `--site-code` | `SIM` | 设备 `site_code` 属性 |
| `--mode` | `mixed` | `telemetry` / `event` / `invalid` / `mixed`；`mixed` = telemetry + event |
| `--interval` | `5` | 消息间隔秒数 |
| `--count` | `0` | 消息数量；单设备模式 0 表示无限，批量模式必须 > 0 |
| `--devices-csv` | 空 | 注册脚本输出的 CSV；指定后向 CSV 中的设备批量发送 |
| `--workers` | `10` | 批量发送并发数 |
| `--seed` | 空 | 随机种子 |
| `--keep-device` | 关闭 | 退出时保留设备 |
| `--single-event` | 关闭 | 每次随机发送一个事件对象；默认发送事件数组 |
| `--events-per-packet` | `4` | 每个事件包内同一 `event_id` 的事件数量 |
| `--timeout` | `10` | HTTP 超时秒数 |

## 数据生成规则

- `int`：在 `min/max` 范围内随机
- `float`：在 `min/max` 范围内随机
- `bool`：随机布尔值
- `string`：生成 `sim-<random>`，`bssid` 生成 MAC 地址
- `enum` / `enum_string`：从 mapping 中选择键；`enum` 转为整数，`enum_string` 保留字符串
- `timestamp`：当前时间
- `struct`：按 `define.specs` 生成扁平 JSON 对象，跳过嵌套 struct
- 事件：每包只选择一个 TSL 事件定义，生成 `--events-per-packet` 个相同 `event_id` 的事件，放进 `{"events": [...]}` 一次发送；每个事件包含事件 params 以及 `event_id/event_type/event_ts`，事件 id 直接使用 TSL `events[].id`（也兼容 `id` 字段，`event_id` 优先），产品未定义事件时生成 `evt-<random>`
- `--single-event`：退化为每次随机发送一个事件对象
- 规则链收到 `msg.events` 后按数组校验，归一化为 `events` 数组；要求同一包内 `event_id` 一致，混合事件会被标记为 `events:mixed`；`events[].id` 就是 TSL `events[].id`，不生成随机 id，也不输出 `code`；消息不包含 `level`，由 ingest/event-center 按 `type` 映射
- `mixed`：属性/事件交替发送；`invalid` 为独立模式，仅发送属性类非法数据
- actions：不模拟（行为是平台到设备的 RPC，不是遥测上报）

## Kafka 验证

正常遥测：

```text
iot.telemetry.normalized
```

事件：

```text
iot.event.normalized
```

非法数据：

```text
iot.invalid
```

如果使用外部 Kafka，可在能访问 Kafka 的机器上消费：

```bash
kcat -b kafka-test1:9095 -t iot.telemetry.normalized -C -o beginning -e
```

## 规则链脚本测试

不需要启动 ThingsBoard 即可验证校验脚本逻辑：

```bash
node thing-model/scripts/test_rulechain_validation.js
```

覆盖合法遥测、类型错误、越界、int32、报文超限、未知字段、枚举、时间戳归一、合法/未知事件、事件类型不匹配等情况。

## 注意

- 默认会创建并删除测试设备；使用 `--keep-device` 可保留。
- 脚本不会打印完整 Access Token。
- 产品 Asset 上没有 `tsl_schema` 时，脚本会提示先执行产品同步。
- 规则链校验使用生成时内嵌的产品 TSL schema，不再要求设备侧存在 `tsl_schema`；脚本仍写入该属性以兼容旧行为。
