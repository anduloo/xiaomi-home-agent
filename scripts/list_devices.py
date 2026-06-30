#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Home Agent Skill - 设备列表查询
使用 mijiaAPI 获取设备列表
"""

import sys
import os
import json

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(SKILL_ROOT, 'config')
AUTH_FILE = os.path.join(CONFIG_DIR, 'auth.json')

# WorkBuddy sandbox: use workspace-local auth path instead of ~/.config/mijia-api/
def _get_auth_path():
    workspace_auth = os.path.expanduser('~/.workbuddy/skills/xiaomi-home-agent/config/auth.json')
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth

def list_devices():
    """列出所有设备"""
    try:
        # 使用 mijiaAPI 获取设备
        from mijiaAPI import mijiaAPI
        
        print("☁️  正在获取设备列表...\n")
        
        # 创建 API 实例（使用 workspace-local auth 路径适配 WorkBuddy 沙箱）
        api = mijiaAPI(auth_data_path=_get_auth_path())
        
        # 获取设备列表
        devices = api.get_devices_list()
        
        if not devices:
            print("📭 暂无可用设备")
            return
        
        print(f"🏠 米家设备列表 (共 {len(devices)} 个设备)\n")
        print("=" * 70)
        
        # 按房间分组
        rooms = {}
        for device in devices:
            room_name = device.get('room_name', '未分组')
            if room_name not in rooms:
                rooms[room_name] = []
            rooms[room_name].append(device)
        
        for room_name, room_devices in rooms.items():
            print(f"\n📍 {room_name}")
            print("-" * 40)
            
            for device in room_devices:
                did = device.get('did', 'N/A')
                name = device.get('name', '未知设备')
                model = device.get('model', 'N/A')
                # API 返回的是 isOnline 而不是 online
                online = device.get('isOnline', False) or device.get('online', False)
                status = "🟢 在线" if online else "🔴 离线"
                
                # 获取设备类型
                device_type = get_device_type(model)
                
                print(f"  {status} {name}")
                print(f"         ID: {did}")
                print(f"         型号: {model}")
                print(f"         类型: {device_type}")
        
        print("\n" + "=" * 70)
        print("\n💡 使用示例:")
        print(f"   python3 {SKILL_ROOT}/scripts/control_device.py --did <设备ID> --action turn_on")
        
        # 保存设备列表到缓存
        save_devices_cache(devices)
        
    except ImportError:
        print("❌ 未安装 mijiaAPI，请先运行:")
        print("   pip3 install mijiaAPI")
    except Exception as e:
        print(f"❌ 获取设备列表失败: {e}")
        print("\n请确保已登录:")
        print("   /Users/xiezh/Library/Python/3.9/bin/mijiaAPI -l")

def save_devices_cache(devices):
    """保存设备列表缓存"""
    cache_file = os.path.join(CONFIG_DIR, 'devices_cache.json')
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  保存缓存失败: {e}")

def get_device_type(model):
    """根据设备模型识别设备类型"""
    if not model:
        return "📱 其他设备"
    
    model_lower = model.lower()
    
    type_mapping = {
        'light': '💡 灯具',
        'lamp': '💡 灯具',
        'bulb': '💡 灯泡',
        'strip': '💡 灯带',
        'switch': '🔌 开关',
        'outlet': '🔌 插座',
        'plug': '🔌 插头',
        'sensor': '📊 传感器',
        'thermostat': '🌡️ 温控',
        'aircondition': '❄️ 空调',
        'ac': '❄️ 空调',
        'humidifier': '💨 加湿器',
        'fan': '🌀 风扇',
        'purifier': '🌿 空气净化器',
        'vacuum': '🤖 扫地机器人',
        'lock': '🔒 智能门锁',
        'camera': '📷 摄像头',
        'doorbell': '🔔 门铃',
        'curtain': '🪟 窗帘电机',
        'curtains': '🪟 窗帘电机',
        'speaker': '🔊 音箱',
        'tv': '📺 电视',
        'remote': '🎮 遥控器',
        'washer': '🧺 洗衣机',
        'fridge': '🧊 冰箱',
        'cooker': '🍳 电饭煲',
        'oven': '🍗 烤箱',
        'microwave': '📦 微波炉',
        'water': '💧 水壶',
        'kettle': '💧 电热水壶',
    }
    
    for key, device_type in type_mapping.items():
        if key in model_lower:
            return device_type
    
    return "📱 其他设备"

if __name__ == '__main__':
    list_devices()
