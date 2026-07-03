---
name: xiaomi-home-agent
description: |
  基于 mijiaAPI 的小米米家智能设备控制 Skill。
  支持设备查询、状态监控、设备控制（开关/亮度/温度等）、自动化场景。
  使用 mijiaAPI OAuth2.0 安全认证。
  
  使用场景：
  - 用户说 "查看米家设备"、"列出所有智能设备"
  - 用户说 "打开客厅灯"、"关闭空调"、"调节亮度到50%"
  - 用户说 "执行床头灯联动场景"
  - 用户说 "查看卧室温度"、"获取设备状态"
metadata:
  openclaw:
    emoji: "🏠"
    requires:
      bins:
        - python3
      pypi:
        - mijiaAPI
        - pyyaml
        - qrcode
        - pillow
---

# Xiaomi Home Agent Skill

基于 mijiaAPI 封装的 OpenClaw Agent Skill，用于控制小米米家智能设备和场景。

## ✅ 功能特性

- 🔐 **安全认证**：mijiaAPI OAuth2.0 扫码登录
- 📱 **设备管理**：查询设备列表、获取设备状态
- 🎛️ **设备控制**：开关、亮度、温度等属性调节
- 🤖 **自动化场景**：支持自定义联动规则
- 🏠 **多家庭支持**：支持多个米家家庭切换

## 🚀 快速开始

### 1. 环境安装

```bash
cd /Applications/QClaw.app/Contents/Resources/openclaw/config/skills/xiaomi-home-agent
python3 scripts/setup_env.py
```

### 2. 登录米家账号

WorkBuddy 会话内**不要直接运行** `mijiaAPI login` / `mijiaAPI -l` 这类交互登录命令；它会在终端等待扫码，容易阻塞会话。

推荐路径：

```bash
python3 scripts/generate_qr.py
```

生成二维码 PNG 后，由用户用米家 APP 扫码；认证文件保存在：

```text
~/.workbuddy/skills/xiaomi-home-agent/config/auth.json
```

如使用 `mijiaAPI` CLI，可让用户在独立终端执行：

```bash
uvx mijiaAPI login -p ~/.workbuddy/skills/xiaomi-home-agent/config/auth.json
```

### 3. 查看设备列表

```bash
python3 scripts/list_devices.py
```

### 4. 控制设备

```bash
# 打开设备
python3 scripts/control_device.py --did <设备ID> --action turn_on

# 关闭设备
python3 scripts/control_device.py --did <设备ID> --action turn_off

# 使用设备名称
python3 scripts/control_device.py --name "床头灯" --action turn_on
```

## 📖 使用说明

### 设备控制

```bash
# 打开/关闭设备
python3 scripts/control_device.py --did <did> --action turn_on
python3 scripts/control_device.py --did <did> --action turn_off

# 设置亮度 (0-100)
python3 scripts/control_device.py --did <did> --action set_brightness --value 50

# 设置温度
python3 scripts/control_device.py --did <did> --action set_temperature --value 26

# 使用设备名称（模糊匹配）
python3 scripts/control_device.py --name "吸顶灯" --action turn_off
```

### 自动化场景

```bash
# 场景1: 床头灯打开时，自动关闭吸顶灯
python3 scripts/auto_scene_bedside.py

# 场景2: 吸顶灯打开时，自动关闭床头灯
python3 scripts/auto_scene_ceiling.py
```

### 设备状态查询

```bash
# 查询设备详细信息
python3 scripts/get_device_status.py --did <设备ID>

# 查询传感器数据（如青萍空气检测仪）
python3 -c "
from mijiaAPI import mijiaAPI
api = mijiaAPI()
# 获取温度、湿度、PM2.5等数据
params = [{'did': '<设备ID>', 'siid': 3, 'piid': i} for i in range(1, 11)]
result = api.get_devices_prop(params)
for item in result:
    if item.get('code') == 0:
        print(f\"piid={item.get('piid')}: {item.get('value')}\")
"
```

## 🔧 技术实现细节

### 补充能力清单

本 skill 使用 Do1e `mijiaAPI` 包作为底层，以下为当前已提供的全部能力（含 v1.0.4 新增）：

| 能力 | 脚本 / API | 说明 |
|------|-----------|------|
| 家庭/房间映射 | `list_devices.py` / `get_homes_list()` | 自动补齐设备房间和家庭信息 |
| 设备列表 | `scripts/list_devices.py` | 按房间分组展示，输出设备 DID/型号/类型/在线状态 |
| 设备状态 | `scripts/get_device_status.py` | 标准 + BLE PIID 双范围扫描，覆盖传感器属性 |
| 设备控制 | `scripts/control_device.py` | 支持 on/off/brightness/temperature/position 等动作 |
| 属性读写（通用） | `control_device.py` / `get_device_status.py` | 底层 `get_devices_prop()` / `set_devices_prop()` / `run_action()` |
| 场景列表 | `scripts/list_scenes.py` | v1.0.4 新增，按家庭列出自动化/手动场景 |
| 执行场景 | `scripts/run_scene.py` | v1.0.4 新增，默认 dry-run，需 `--yes` 确认 |
| 耗材寿命 | `scripts/list_consumables.py` | v1.0.4 新增，查询滤芯/耗材剩余寿命 |
| 设备规格发现 | `scripts/get_device_info.py` | v1.0.4 新增，MIoT spec 查询 + 在线 PIID 扫描 |

以下能力已有底层支持但建议按需使用：
- `get_homes_list()` / `get_shared_devices_list()`：可通过 Python API 直接调用
- `mijiaAPI run "<自然语言>"`：不推荐脚本化，跨平台一致性要求用户显式确认
- `mijiaAPI mcp`：不推荐脚本化，长运行 service 不适合 WorkBuddy 会话

禁止在 agent 会话中直接调用：
- `mijiaAPI login`：二维码登录会阻塞等待扫码
- `mijiaAPI mcp`：会启动长运行 stdio server

### 设备控制方式

根据设备类型，使用不同的控制方式：

1. **插座/开关类设备**（如 xiaomi.switch.w1）:
   - 使用 `set_devices_prop` 设置 power 属性
   - 参数: `[{'did': did, 'siid': 2, 'piid': 1, 'value': True/False}]`

2. **动作类设备**（如 cuco.plug.v3）:
   - 使用 `run_action` 执行动作
   - 参数: `{'did': did, 'siid': 2, 'aiid': 1}` (开启) / `aiid: 2` (关闭)

3. **传感器类设备**（如青萍空气检测仪）:
   - 使用 `get_devices_prop` 查询属性
   - 温度通常在 siid=3, piid=7
   - CO2 通常在 siid=3, piid=8

### 在线状态字段

**重要**: 小米 API 返回的在线状态字段是 `isOnline` 而不是 `online`。

```python
online = device.get('isOnline', False)  # 正确
# online = device.get('online', False)  # 错误
```

### BLE/传感器设备 PIID 范围（重要）

**⚠️ MIoT 设备有两种 PIID 分布模式，查询时必须两者都覆盖：**

| 设备类型 | SIID | PIID 范围 | 示例属性 |
|---------|------|----------|---------|
| 标准设备（开关/灯/窗帘） | 2 | 1-6 | on/off(1), brightness(2), mode(4) |
| 环境传感器 | 3 | 1-7 | temperature(1), humidity(2), PM2.5(3), CO2(4) |
| **BLE/人体存在传感器** | **2** | **1005-1080** | occupancy-status(1078), no-one-duration(1079), illumination(1005) |
| BLE 电池 | 4 | 1003 | battery-level |

**根因**：Linptect ES3 等 BLE mesh 传感器使用 MIoT spec v2，其属性 ID 从 1000 起编，与标准 Wi-Fi/Zigbee 设备 (piid 1-10) 完全不同。**仅查询 piid 1-10 会静默返回"属性不存在"(code=-704040003)**。

**正确做法**：查询传感器时必须同时扫描 `siid=2, piid=1-9` + `siid=3, piid=1-7` + `siid=2, piid=(1005,1078,1079,1080)` + `siid=4, piid=(1,1003)`。

**MIoT spec 查询**：如果上述范围仍不够，可通过小米官方 spec 服务器获取完整属性定义：
```
https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:<device-type>:<model>:<version>
```

### 错误码处理

常见错误码：
- `-704040003`: 属性不存在（常见原因：PIID 不在该设备的有效范围内，如 BLE 设备需查 1000+ 范围）
- `-704040005`: Action 不存在
- `-8`: 数据类型无效（通常是设备离线）

## 📁 目录结构

```
xiaomi-home-agent/
├── SKILL.md                    # 本文件
├── README.md                   # 项目介绍
├── LICENSE                     # MIT 许可证
├── requirements.txt            # Python 依赖
├── config/
│   └── config.yaml            # 配置文件
├── scripts/
│   ├── setup_env.py           # 环境检查与安装
│   ├── auth_mijia.py          # mijiaAPI 认证指引
│   ├── list_devices.py        # 设备列表查询
│   ├── get_device_status.py   # 设备状态查询
│   ├── control_device.py      # 设备控制（支持多种方式）
│   ├── list_scenes.py         # 自动化/手动场景列表 (v1.0.4)
│   ├── run_scene.py           # 执行场景，默认 dry-run (v1.0.4)
│   ├── list_consumables.py    # 耗材寿命查询 (v1.0.4)
│   ├── get_device_info.py     # 设备 MIoT 规格发现 (v1.0.4)
│   ├── auto_scene_bedside.py  # 场景1: 床头灯联动
│   ├── auto_scene_ceiling.py  # 场景2: 吸顶灯联动
│   └── generate_qr.py         # 二维码生成
└── reference/
    ├── device_types.json      # 设备类型映射表
    ├── miot_spec.md           # MIoT-Spec-V2 协议说明
    └── error_codes.md         # 错误码对照表
```

## 🔒 安全说明

- mijiaAPI Token 存储在 `~/.workbuddy/skills/xiaomi-home-agent/config/auth.json`（WorkBuddy 沙箱适配）
- 支持本地局域网控制和云端控制
- 绝不泄露敏感 Token

## ⚠️ WorkBuddy 沙箱适配

WorkBuddy 沙箱限制访问 `~/.config/` 目录，因此所有脚本使用 workspace-local auth 路径：
- Auth 文件: `~/.workbuddy/skills/xiaomi-home-agent/config/auth.json`
- 设备缓存: `~/.workbuddy/skills/xiaomi-home-agent/config/devices_cache.json`

## 📝 更新日志

### v1.0.4 (2026-07-03)
- ✅ 新增 4 个脚本：`list_scenes.py`、`run_scene.py`、`list_consumables.py`、`get_device_info.py`
- ✅ `list_devices.py` 升级：自动从 `get_homes_list().roomlist` 补齐房间和家庭信息
- ✅ `control_device.py` 升级：支持动作同义词（open/close → on/off/position）和模型类型推断
- ✅ 移除 SKILL.md 中不准确的 Do1e 描述，仅列出已实现能力

### v1.0.3 (2026-07-03)
- ✅ 确认当前底层已是 Do1e `mijiaAPI`，无需整体替换
- ✅ 登录说明改为 WorkBuddy 安全流程：禁止在会话内直接运行阻塞式 `mijiaAPI login` / `mijiaAPI -l`

### v1.0.2 (2026-06-30)
- ✅ 修复 BLE/人体存在传感器 PIID 盲区：`get_device_status.py` 新增 1000+ 范围扫描
- ✅ 新增 MIoT BLE 传感器 PIID 参考文档
- ✅ 修复环境传感器 (siid=3) 属性扫描覆盖

### v1.0.1 (2026-06-30)
- ✅ WorkBuddy 沙箱适配：auth 路径改为 workspace-local
- ✅ 修复 list_devices / control_device / get_device_status 的 auth 路径

### v1.0.0 (2026-03-24)
- ✅ 初始版本发布
- ✅ 支持 mijiaAPI OAuth2.0 登录
- ✅ 支持设备列表查询
- ✅ 支持设备控制（开关、亮度、温度）
- ✅ 支持自动化场景
- ✅ 修复吸顶灯控制方式（set_devices_prop）
- ✅ 修复在线状态字段（isOnline）

## 🔗 相关链接

- [mijiaAPI](https://github.com/Do1e/mijiaAPI) - 小米米家 API 封装
- [MIoT-Spec-V2](https://iot.mi.com/v2/new/doc/introduction/knowledge/spec) - 小米 IoT 协议规范
- [OpenClaw](https://docs.openclaw.ai) - OpenClaw 文档

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件
