#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Home Agent Skill - 设备列表查询
使用 mijiaAPI 获取设备列表，自动从 roomlist 补齐房间信息。
"""

import argparse
import json
import os
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(SKILL_ROOT, "config")


def _get_auth_path():
    workspace_auth = os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth


def _build_room_map(api) -> dict:
    """从米家 home roomlist 构建 did -> room/home 映射。"""
    room_map = {}
    try:
        homes = api.get_homes_list()
    except Exception:
        return room_map

    for home in homes or []:
        home_id = str(home.get("id", ""))
        home_name = home.get("name", "") or ""
        for room in home.get("roomlist", []) or []:
            room_name = room.get("name", "") or "-"
            room_id = str(room.get("id", ""))
            for did in room.get("dids", []) or []:
                room_map[str(did)] = {
                    "room": room_name,
                    "room_id": room_id,
                    "home": home_name,
                    "home_id": home_id,
                }
    return room_map


def get_device_type(model):
    """根据设备模型识别设备类型（纯文本，不含 emoji）。"""
    if not model:
        return "Other"
    model_lower = model.lower()
    type_mapping = {
        "light": "Light", "lamp": "Light", "bulb": "Light", "strip": "Light",
        "switch": "Switch", "outlet": "Outlet", "plug": "Outlet",
        "sensor": "Sensor", "thermostat": "Thermostat",
        "aircondition": "AirConditioner", "ac": "AirConditioner",
        "humidifier": "Humidifier", "fan": "Fan", "purifier": "AirPurifier",
        "vacuum": "SweepingRobot", "lock": "Lock",
        "camera": "Camera", "doorbell": "Doorbell",
        "curtain": "WindowCovering", "curtains": "WindowCovering",
        "speaker": "Speaker", "tv": "TV", "remote": "Button",
        "washer": "Washer", "fridge": "Fridge",
        "cooker": "Cooker", "oven": "Oven", "microwave": "Microwave",
        "water": "Kettle", "kettle": "Kettle",
    }
    for key, dtype in type_mapping.items():
        if key in model_lower:
            return dtype
    return "Other"


# Emoji + 中文展示映射（仅用于终端输出）
_TYPE_DISPLAY = {
    "Light": "💡 灯具", "Switch": "🔌 开关", "Outlet": "🔌 插座",
    "Sensor": "📊 传感器", "AirConditioner": "❄️ 空调", "Fan": "🌀 风扇",
    "WindowCovering": "🪟 窗帘", "SweepingRobot": "🤖 扫地机",
    "Speaker": "🔊 音箱", "TV": "📺 电视", "Button": "🎮 遥控",
    "Lock": "🔒 门锁", "Camera": "📷 摄像头", "Doorbell": "🔔 门铃",
    "ClotheDryingMachine": "👕 晾衣架", "AirPurifier": "🌿 净化器",
    "Humidifier": "💨 加湿器", "Thermostat": "🌡️ 温控",
    "OccupancySensor": "📊 人体存在", "Hub": "🔷 网关",
    "Kettle": "💧 水壶", "Cooker": "🍳 电饭煲", "Fridge": "🧊 冰箱",
    "Washer": "🧺 洗衣机", "Oven": "🍗 烤箱", "Microwave": "📦 微波炉",
    "Other": "📱 其他",
}


def list_devices(json_output=False):
    from _auth_guard import require_auth

    api = require_auth(json_output=json_output)

    try:
        # Build room map from roomlist
        room_map = _build_room_map(api)

        devices = api.get_devices_list()
        if not devices:
            output = {"ok": True, "count": 0, "devices": [], "homes": []}
            print(json.dumps(output, ensure_ascii=False, indent=2) if json_output else "📭 暂无可用设备")
            return

        enriched = []
        for d in devices:
            did = str(d.get("did", "?"))
            room_info = room_map.get(did, {})
            room_name = d.get("room_name") or room_info.get("room") or "-"
            home_name = room_info.get("home") or ""
            enriched.append({
                "did": did,
                "name": d.get("name", "?"),
                "model": d.get("model", "?"),
                "online": bool(d.get("isOnline", False)),
                "room": room_name,
                "room_id": room_info.get("room_id", ""),
                "home": home_name,
                "home_id": room_info.get("home_id", ""),
                "type": get_device_type(d.get("model", "")),
            })

        if json_output:
            print(json.dumps({"ok": True, "count": len(enriched), "devices": enriched},
                             ensure_ascii=False, indent=2))
            return

        # Pretty print grouped by room
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        print(f"🏠 米家设备列表 (共 {len(enriched)} 个设备)\n")
        print("=" * 70)

        rooms = {}
        for d in enriched:
            room = d.get("room", "未分组")
            rooms.setdefault(room, []).append(d)

        for room_name, room_devices in sorted(rooms.items()):
            print(f"\n📍 {room_name}")
            print("-" * 40)
            for d in room_devices:
                status = "🟢 在线" if d["online"] else "🔴 离线"
                home_tag = f" [{d['home']}]" if d.get("home") else ""
                type_display = _TYPE_DISPLAY.get(d.get("type", ""), d.get("type", "未知"))
                print(f"  {status} {d['name']}{home_tag}")
                print(f"         DID:  {d['did']}")
                print(f"         型号: {d['model']}")
                print(f"         类型: {type_display}")

        print("\n" + "=" * 70)
        print("\n💡 使用示例:")
        print(f"   python3 {SKILL_ROOT}/scripts/control_device.py --did <设备ID> --action turn_on")

        # Save cache
        cache_file = os.path.join(CONFIG_DIR, "devices_cache.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(enriched, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存缓存失败: {e}")

    except ImportError:
        print("❌ 未安装 mijiaAPI，请先安装依赖")
    except Exception as e:
        output = {"ok": False, "error": str(e)}
        print(json.dumps(output, ensure_ascii=False, indent=2) if json_output else f"❌ 获取设备列表失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="列出米家设备列表（含自动房间映射）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    list_devices(json_output=args.json)


if __name__ == "__main__":
    main()
