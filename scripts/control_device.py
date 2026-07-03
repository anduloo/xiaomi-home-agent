#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Home Agent Skill - 设备控制
使用 mijiaAPI 控制设备，支持动作同义词和类型推断。
"""

import argparse
import os
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_auth_path():
    workspace_auth = os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth


# ---------------------------------------------------------------------------
# 模型 → 类型推断（与 smart-home-aggregator 保持同步）
# ---------------------------------------------------------------------------
_MODEL_TYPE_MAP = {
    "wopener":     "WindowCovering",
    "airer":       "ClotheDryingMachine",
    "sensor_occupy": "OccupancySensor",
    "flood":       "Sensor",
    "switch":      "Switch",
    "wifispeaker": "Speaker",
    "cookbook":    "Other",
    "fishbowl":    "Other",
    "gateway":     "Hub",
    "intercom":    "Other",
    "fan":         "Fan",
    "remote":      "Button",
}


def infer_type(model: str) -> str:
    """从米家 model 字段推断设备类型。"""
    if not model:
        return ""
    m = model.lower()
    for prefix, dtype in _MODEL_TYPE_MAP.items():
        if prefix in m:
            return dtype
    return ""


# 位置控制类型集合
_POSITION_TYPES = {"WindowCovering", "ClotheDryingMachine"}

# 开关型设备：open/close → on/off
_SWITCH_TYPES = {"Switch", "Light", "Button", "Outlet", "Fan", "Speaker", "Other"}


def normalize_action(action: str, device_type: str):
    """动作同义词归一化。

    返回 (normalized_action, value_override)
    - open → on   for switches; → set_position/100 for curtains
    - close → off  for switches; → set_position/0   for curtains
    - set_position → stays, with value from caller or default 50
    - stop → stays for curtains
    """
    act = action.lower().strip()

    # 窗帘/晾衣架/窗：open/close → 位置控制
    if device_type in _POSITION_TYPES:
        if act == "open":
            return "set_position", 100
        if act == "close":
            return "set_position", 0
        if act in ("stop", "pause"):
            return "stop", None
        if act == "set_position":
            return "set_position", None  # caller provides value
        return act, None

    # 开关型设备：open/close → turn_on/turn_off
    if device_type in _SWITCH_TYPES or not device_type:
        if act == "open":
            return "turn_on", None
        if act == "close":
            return "turn_off", None

    # 通用映射
    if act == "open":
        return "turn_on", None
    if act == "close":
        return "turn_off", None

    # 直通
    return act, None


# ---------------------------------------------------------------------------
# 设备控制
# ---------------------------------------------------------------------------
def control_device(did, action, value=None, device_type=""):
    try:
        from mijiaAPI import mijiaAPI

        # 动作归一化
        norm_action, norm_value = normalize_action(action, device_type)
        if norm_value is not None and value is None:
            value = norm_value
        action = norm_action

        api = mijiaAPI(auth_data_path=_get_auth_path())

        print(f"🎛️  控制设备: {did}")
        print(f"   动作: {action}")
        if value is not None:
            print(f"   值: {value}")
        print()

        # --- turn_on ---
        if action == "turn_on":
            try:
                data = {"did": did, "siid": 2, "aiid": 1}
                result = api.run_action(data)
                if result.get("code") == 0:
                    print("✅ 设备已开启")
                    return True
            except Exception:
                pass
            try:
                data = [{"did": did, "siid": 2, "piid": 1, "value": True}]
                result = api.set_devices_prop(data)
                if result and len(result) > 0 and result[0].get("code") in [0, 1]:
                    print("✅ 设备已开启")
                    return True
            except Exception:
                pass
            print("❌ 无法开启设备")
            return False

        # --- turn_off ---
        elif action == "turn_off":
            try:
                data = {"did": did, "siid": 2, "aiid": 2}
                result = api.run_action(data)
                if result.get("code") == 0:
                    print("✅ 设备已关闭")
                    return True
            except Exception:
                pass
            try:
                data = [{"did": did, "siid": 2, "piid": 1, "value": False}]
                result = api.set_devices_prop(data)
                if result and len(result) > 0 and result[0].get("code") in [0, 1]:
                    print("✅ 设备已关闭")
                    return True
            except Exception:
                pass
            print("❌ 无法关闭设备")
            return False

        # --- set_position (窗帘/晾衣架百分比位置) ---
        elif action == "set_position":
            if value is None:
                value = 50
            try:
                val = int(value)
            except (ValueError, TypeError):
                val = 50
            val = max(0, min(100, val))
            data = [{"did": did, "siid": 2, "piid": 2, "value": val}]
            result = api.set_devices_prop(data)
            print(f"✅ 位置已设置为 {val}%")
            return True

        # --- stop ---
        elif action == "stop":
            data = [{"did": did, "siid": 2, "piid": 4, "value": "stop"}]
            result = api.set_devices_prop(data)
            print("✅ 设备已暂停")
            return True

        # --- set_brightness ---
        elif action == "set_brightness":
            if value is None:
                value = 50
            data = [{"did": did, "piid": 2, "value": int(value)}]
            result = api.set_devices_prop(data)
            print(f"✅ 亮度已设置为 {value}%")
            return True

        # --- set_temperature ---
        elif action == "set_temperature":
            if value is None:
                value = 26
            data = [{"did": did, "piid": 3, "value": int(value)}]
            result = api.set_devices_prop(data)
            print(f"✅ 温度已设置为 {value}°C")
            return True

        # --- run_action (低层直达) ---
        elif action == "run_action":
            data = {"did": did, "siid": 2, "aiid": value if isinstance(value, int) else 1}
            result = api.run_action(data)
            print(f"✅ 动作已执行: {value}")
            return True

        else:
            print(f"❌ 不支持的动作: {action}")
            return False

    except Exception as e:
        print(f"❌ 控制失败: {e}")
        if "offline" in str(e).lower() or "-8" in str(e):
            print("\n⚠️  设备可能处于离线状态")
            print("   请检查：设备是否通电 / 是否连接到 WiFi / 是否在其他家庭")
        return False


def find_device_by_name(api, name_query):
    try:
        devices = api.get_devices_list()
        matches = []
        for d in devices:
            if name_query in d.get("name", ""):
                matches.append(d)
        return matches
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="控制米家设备（支持动作同义词和类型推断）")
    parser.add_argument("--did", type=str, help="设备 ID")
    parser.add_argument("--name", type=str, help="设备名称（模糊匹配）")
    parser.add_argument("--action", type=str, required=True,
                        help="动作: turn_on/on/open | turn_off/off/close | set_brightness | set_temperature | set_position | stop | run_action")
    parser.add_argument("--value", type=str, help="控制值")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    try:
        from mijiaAPI import mijiaAPI
        api = mijiaAPI(auth_data_path=_get_auth_path())
    except ImportError:
        print(json.dumps({"ok": False, "error": "未安装 mijiaAPI"}, ensure_ascii=False) if args.json else "❌ 未安装 mijiaAPI")
        return

    # 解析设备 DID 和类型
    did = args.did
    device_type = ""
    device_name = ""

    if args.name and not did:
        devices = find_device_by_name(api, args.name)
        if not devices:
            msg = f"未找到设备: {args.name}"
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False) if args.json else f"❌ {msg}")
            return
        elif len(devices) == 1:
            d = devices[0]
            did = d["did"]
            device_name = d.get("name", "")
            device_type = infer_type(d.get("model", ""))
            if not args.json:
                print(f"✅ 找到设备: {device_name} (DID: {did}, 类型: {device_type or '未知'})")
        else:
            if args.json:
                print(json.dumps({"ok": False, "error": "多个匹配设备", "matches": [
                    {"did": d["did"], "name": d.get("name", ""), "model": d.get("model", "")}
                    for d in devices
                ]}, ensure_ascii=False, indent=2))
            else:
                print(f"⚠️  找到 {len(devices)} 个匹配设备，请用 --did 指定:")
                for i, d in enumerate(devices, 1):
                    dtype = infer_type(d.get("model", ""))
                    print(f"  {i}. {d['name']}  DID={d['did']}  类型={dtype or '未知'}")
            return

    if not did:
        msg = "请提供 --did 或 --name 参数"
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False) if args.json else f"❌ {msg}")
        return

    # 如果通过 --did 传入，补查类型
    if not device_type and not args.name:
        try:
            for d in api.get_devices_list():
                if str(d.get("did", "")) == str(did):
                    device_name = d.get("name", "")
                    device_type = infer_type(d.get("model", ""))
                    break
        except Exception:
            pass

    # 动作归一化
    norm_action, norm_value = normalize_action(args.action, device_type)
    if norm_value is not None and args.value is None:
        args.value = str(norm_value)

    if not args.json:
        print(f"🎛️  [{device_type or '未知类型'}] {device_name or did} → {norm_action}" +
              (f" = {args.value}" if args.value else ""))

    # 转换值
    value = None
    if args.value:
        try:
            value = int(args.value)
        except ValueError:
            value = args.value

    ok = control_device(did, norm_action, value, device_type)
    if args.json:
        print(json.dumps({"ok": ok, "did": did, "action": norm_action, "value": value},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
