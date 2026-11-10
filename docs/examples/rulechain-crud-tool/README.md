# 规则链增删改查工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`rulechain_crud_tool.py` 通过 ThingsBoard REST API 管理规则链：查询、创建、更新、删除、
设为根规则链、读写节点元数据，以及导出/导入规则链 JSON。

- 协议：**REST**
- 覆盖手册：规则引擎
- 默认地址：`http://localhost:8080`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard 服务
- 租户管理员账号或有效 API Key

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

查询规则链：

```powershell
python rulechain_crud_tool.py --action list
```

查询详情：

```powershell
python rulechain_crud_tool.py --action get --rule-chain-id <RULE_CHAIN_ID>
```

创建规则链：

```powershell
python rulechain_crud_tool.py `
  --action create `
  --name "环境监测规则链" `
  --description "温度超限告警"
```

更新规则链：

```powershell
python rulechain_crud_tool.py `
  --action update `
  --rule-chain-id <RULE_CHAIN_ID> `
  --name "环境监测规则链 v2" `
  --debug-mode
```

设为根规则链：

```powershell
python rulechain_crud_tool.py --action set-root --rule-chain-id <RULE_CHAIN_ID>
```

导出规则链：

```powershell
python rulechain_crud_tool.py `
  --action export `
  --rule-chain-id <RULE_CHAIN_ID> `
  --output .\environment.rule-chain.json
```

导入规则链：

```powershell
python rulechain_crud_tool.py `
  --action import `
  --input .\environment.rule-chain.json `
  --name "环境监测规则链（副本）"
```

删除规则链：

```powershell
python rulechain_crud_tool.py --action delete --rule-chain-id <RULE_CHAIN_ID>
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--timeout` | `30` | 否 | HTTP 超时秒数 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号登录用户名 |
| `--password` | 无 | 二选一 | 账号登录密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list` / `get` / `create` / `update` / `delete` / `set-root` / `metadata` / `export` / `import` |
| `--rule-chain-id` | 无 | 视操作 | 规则链 ID |
| `--name` | 无 | 创建时 | 规则链名称 |
| `--description` | 无 | 否 | 规则链描述 |
| `--debug-mode` | 关闭 | 否 | 开启调试模式 |
| `--rule-chain-type` | `CORE` | 否 | `CORE` 或 `EDGE` |
| `--input` | 无 | 导入时 | 导入或元数据 JSON 文件 |
| `--output` | `<id>.rule-chain.json` | 否 | 导出文件路径 |
| `--page-size` | `100` | 否 | 分页大小 |
| `--page` | `0` | 否 | 页码 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/ruleChains` | 查询规则链列表 |
| GET | `/api/ruleChain/{ruleChainId}` | 查询规则链详情 |
| POST | `/api/ruleChain` | 创建或更新规则链 |
| DELETE | `/api/ruleChain/{ruleChainId}` | 删除规则链 |
| POST | `/api/ruleChain/{ruleChainId}/root` | 设为根规则链 |
| GET | `/api/ruleChain/{ruleChainId}/metadata` | 查询节点和连接 |
| POST | `/api/ruleChain/metadata` | 保存节点和连接 |

导出文件格式：

```json
{
  "ruleChain": {
    "name": "环境监测规则链",
    "type": "CORE",
    "debugMode": false,
    "additionalInfo": {
      "description": "温度超限告警"
    }
  },
  "metadata": {
    "nodes": [],
    "connections": [],
    "ruleChainConnections": null
  }
}
```

导入说明：

- 导入时会移除原规则链的 `id`、`tenantId`、`createdTime` 等字段；
- 元数据中的 `ruleChainId` 会替换为新规则链；
- 节点内的实体 ID、外部系统地址等引用需要按目标环境检查。

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | API Key 或账号密码无效 |
| 不能删除根规则链 | 先把其他规则链设为根 |
| 导入后节点缺失 | 检查元数据是否完整，实体引用是否存在 |
| 设置根规则链失败 | 同一时间只能有一个根规则链 |
| 调试模式产生大量事件 | 生产环境使用后请关闭 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 规则链可能包含设备、客户或外部系统引用，导入前请先审查。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--help"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
