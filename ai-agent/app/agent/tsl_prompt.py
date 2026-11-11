TSL_GENERATION_RULES = """物模型 TSL 生成规则：

1. 用户已经提供 TSL 时优先使用，不要要求用户重复上传或粘贴。
2. 用户没有提供 TSL 时，根据产品名称、型号和描述生成合法 TSL；无法判断属性时生成 properties 为空的最小 TSL，不要拒绝创建。
3. TSL 顶层必须是 JSON 对象，必填字段：
   - version：固定使用 "1.0"
   - profile：对象，必须包含 ProductId
   - properties：数组，可以为空
4. profile.ProductId 必须等于创建或更新产品时使用的 product_id，长度 1~64。
5. 属性对象必填：
   - id：英文标识符，匹配 ^[A-Za-z_][A-Za-z0-9_]{0,49}$
   - name：中文名称，1~128 字符
   - mode：必须是 "r" 或 "rw"
   - define：对象，必须包含 type
6. define.type 只能是：
   bool、int、float、string、enum、enum_string、timestamp、struct
7. 数值规则：
   - min 不能大于 max
   - start 必须在 min 和 max 之间
   - step 不能为负数
   - int 的 min、max、start 必须在 32 位有符号整数范围内
   - bool、string、timestamp 等非数值类型不要配置 min、max、start、step
8. enum 的 mapping 至少 2 项，键必须是数字。
9. enum_string 的 mapping 至少 2 项，键可以是字符串。
10. struct：
    - specs 或 fields 不能为空
    - 不允许嵌套 struct
    - 事件参数不允许使用 struct
    - 行为参数可以使用 struct
11. 事件对象必填：
    - id
    - name
    - type：只能是 info、alert 或 fault
    - params 可选，使用 params，不要使用 output
12. 行为对象必填：
    - id
    - name
    - input、output 可选，使用 input/output，不要使用 inputParams/outputParams
13. 属性、事件、行为各自内部 id 唯一；同一事件或行为的参数 id 在各自列表内唯一。
14. 属性数 + 事件数 + 行为数不能超过 100。
15. 属性 id 不要使用平台保留键：ts、event_id、event_type、event_ts。
16. 属性、事件、行为、参数 id 使用英文小写 snake_case 或小驼峰；不要使用中文 id。
17. TSL 必须放入 create_product 或 update_thing_model 的 tsl 参数，不要把 TSL 放在普通正文或代码块里代替参数。
"""

TSL_MINIMAL_EXAMPLE = """最小合法 TSL：
{
  "version": "1.0",
  "profile": {
    "ProductId": "<product_id>"
  },
  "properties": []
}"""

TSL_SENSOR_EXAMPLE = """传感器产品示例：
{
  "version": "1.0",
  "profile": {
    "ProductId": "<product_id>",
    "CategoryId": "1"
  },
  "properties": [
    {
      "id": "temperature",
      "name": "温度",
      "mode": "r",
      "define": {
        "type": "float",
        "min": -40,
        "max": 125,
        "step": 0.1,
        "unit": "℃"
      }
    },
    {
      "id": "humidity",
      "name": "湿度",
      "mode": "r",
      "define": {
        "type": "float",
        "min": 0,
        "max": 100,
        "unit": "%"
      }
    }
  ],
  "events": [
    {
      "id": "overTemperature",
      "name": "温度超限",
      "type": "alert",
      "params": [
        {
          "id": "temperature",
          "name": "当前温度",
          "define": {
            "type": "float",
            "min": -40,
            "max": 200,
            "unit": "℃"
          }
        }
      ]
    }
  ],
  "actions": [
    {
      "id": "setReportInterval",
      "name": "设置上报周期",
      "input": [
        {
          "id": "interval",
          "name": "上报周期",
          "define": {
            "type": "int",
            "min": 5,
            "max": 3600,
            "unit": "s"
          }
        }
      ],
      "output": [
        {
          "id": "success",
          "name": "是否成功",
          "define": {
            "type": "bool"
          }
        }
      ]
    }
  ]
}"""

TSL_ANTI_PATTERNS = """不要生成：
- 顶层数组
- 缺少 version、profile 或 properties
- ProductId 与 product_id 不一致
- 缺少 mode 或 define
- 中文 id 或数字开头的 id
- enum 或 enum_string 的 mapping 少于 2 项
- enum 的 mapping 键使用非数字
- 事件参数使用 struct
- struct 嵌套 struct
- 属性使用 ts、event_id、event_type、event_ts 作为 id"""


def tsl_generation_rules() -> str:
    return "\n".join(
        [
            TSL_GENERATION_RULES,
            TSL_MINIMAL_EXAMPLE,
            TSL_SENSOR_EXAMPLE,
            TSL_ANTI_PATTERNS,
        ]
    )
