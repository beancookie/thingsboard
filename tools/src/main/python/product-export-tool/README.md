# 产品数据导出工具

`export_products.py` 从运行中的 ThingsBoard / thing-model 平台导出产品列表和完整 TSL 物模型，适合备份或迁移。

## 环境要求

- Python 3.9+
- 可访问目标平台

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 基本用法

导出全部产品（使用脚本内置密钥）：

```powershell
python export_products.py
```

导出到指定目录：

```powershell
python export_products.py --output-dir .\product-export
```

只导出指定产品（`--product-id` 可重复）：

```powershell
python export_products.py `
  --product-id YUMRMRPOGPA `
  --product-id SCENE_LIGHT `
  --output-dir .\product-export
```

## 输出

```text
product-export/
├── products.csv              # 产品元数据汇总（utf-8-sig，Excel 可直接打开）
├── products.json             # 产品列表与每个产品的详情
└── tsl/
    └── <productId>.tsl.json  # 每个产品的完整 TSL
```

`products.csv` 列：

```text
product_id, name, model, category_id, tsl_version, status,
property_count, event_count, action_count,
tb_profile_id, tb_asset_id, tb_rule_chain_id,
updated_at, tsl_file, error
```

单个产品失败会写入 `error` 列并继续导出其余产品，最终以非 0 退出码结束。

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--tb-url` | `https://thingsboard.zhgcloud.com` | ThingsBoard 地址 |
| `--thingmodel-url` | `https://thingsboard.zhgcloud.com/api/thing-model` | thing-model 网关地址 |
| `--api-key` | 见下方优先级 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 使用账号密码登录时的用户名 |
| `--password` | `TB_PASSWORD` | 使用账号密码登录时的密码，未设置则交互输入 |
| `--product-id` | 空 = 全部 | 指定要导出的产品，可重复 |
| `--output-dir` | `product-export` | 输出目录 |
| `--no-detail` | 关闭 | 跳过产品详情请求，只导出列表和 TSL |
| `--timeout` | `30` | HTTP 超时秒数 |

## 认证优先级

1. `--api-key`
2. 环境变量 `TB_API_KEY`
3. 脚本内置密钥

API Key 会先调用 `/api/auth/user` 和 `/api/user/{id}/token` 换取 JWT；产品接口不接受裸 `ApiKey` 头。

未提供 API Key 时可改用账号密码：

```powershell
$env:TB_PASSWORD = "tenant"
python export_products.py `
  --username tenant@thingsboard.org `
  --output-dir .\product-export
```

## 安全说明

- 脚本内置了密钥，因此该脚本已被 `.gitignore` 忽略，避免误提交。
- 如需提交或分享此工具，请先删除 `export_products.py` 中的内置密钥，改用 `--api-key` 或 `TB_API_KEY`。
- 导出的 TSL 属于平台业务数据，请按需妥善保管。
