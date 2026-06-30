#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Home Agent Skill - 设备控制
使用 mijiaAPI 控制设备
"""

import sys
import os
import argparse

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_auth_path():
    workspace_auth = os.path.expanduser('~/.workbuddy/skills/xiaomi-home-agent/config/auth.json')
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth

def control_device(did, action, value=None):
    """控制设备"""
    try:
        from mijiaAPI import mijiaAPI
        
        api = mijiaAPI(auth_data_path=_get_auth_path())
        
        print(f"🎛️  控制设备: {did}")
        print(f"   动作: {action}")
        if value is not None:
            print(f"   值: {value}")
        print()
        
        # 根据动作执行不同操作
        if action == 'turn_on':
            # 打开设备 - 尝试多种方式
            try:
                # 方式1: 使用 run_action
                data = {
                    'did': did,
                    'siid': 2,
                    'aiid': 1,
                }
                result = api.run_action(data)
                if result.get('code') == 0:
                    print(f"✅ 设备已开启")
                    return True
            except:
                pass
            
            # 方式2: 使用 set_devices_prop 设置 power 属性
            try:
                data = [{'did': did, 'siid': 2, 'piid': 1, 'value': True}]
                result = api.set_devices_prop(data)
                if result and len(result) > 0 and result[0].get('code') in [0, 1]:
                    print(f"✅ 设备已开启")
                    return True
            except:
                pass
            
            print(f"❌ 无法开启设备")
            return False
            
        elif action == 'turn_off':
            # 关闭设备 - 尝试多种方式
            try:
                # 方式1: 使用 run_action
                data = {
                    'did': did,
                    'siid': 2,
                    'aiid': 2,
                }
                result = api.run_action(data)
                if result.get('code') == 0:
                    print(f"✅ 设备已关闭")
                    return True
            except:
                pass
            
            # 方式2: 使用 set_devices_prop 设置 power 属性
            try:
                data = [{'did': did, 'siid': 2, 'piid': 1, 'value': False}]
                result = api.set_devices_prop(data)
                if result and len(result) > 0 and result[0].get('code') in [0, 1]:
                    print(f"✅ 设备已关闭")
                    return True
            except:
                pass
            
            print(f"❌ 无法关闭设备")
            return False
            
        elif action == 'set_brightness':
            # 设置亮度
            if value is None:
                value = 50
            data = [{
                'did': did,
                'piid': 2,  # 亮度属性
                'value': int(value),
            }]
            result = api.set_devices_prop(data)
            print(f"✅ 亮度已设置为 {value}%")
            return True
            
        elif action == 'set_temperature':
            # 设置温度
            if value is None:
                value = 26
            data = [{
                'did': did,
                'piid': 3,  # 温度属性
                'value': int(value),
            }]
            result = api.set_devices_prop(data)
            print(f"✅ 温度已设置为 {value}°C")
            return True
            
        elif action == 'run_action':
            # 执行设备动作
            data = {
                'did': did,
                'siid': 2,
                'aiid': value if isinstance(value, int) else 1,
            }
            result = api.run_action(data)
            print(f"✅ 动作已执行: {value}")
            return True
            
        else:
            print(f"❌ 不支持的动作: {action}")
            return False
            
    except Exception as e:
        print(f"❌ 控制失败: {e}")
        
        # 检查是否是因为设备离线
        if 'offline' in str(e).lower() or '-8' in str(e):
            print("\n⚠️  设备可能处于离线状态")
            print("   请检查：")
            print("   1. 设备是否通电")
            print("   2. 设备是否连接到 WiFi")
            print("   3. 设备是否在其他家庭（天津之家）")
        
        return False

def find_device_by_name(name_query):
    """根据名称查找设备"""
    try:
        from mijiaAPI import mijiaAPI
        
        api = mijiaAPI(auth_data_path=_get_auth_path())
        devices = api.get_devices_list()
        
        matches = []
        for device in devices:
            name = device.get('name', '')
            if name_query in name:
                matches.append(device)
        
        return matches
    except Exception as e:
        print(f"❌ 查找设备失败: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description='控制米家设备')
    parser.add_argument('--did', type=str, help='设备ID')
    parser.add_argument('--name', type=str, help='设备名称（模糊匹配）')
    parser.add_argument('--action', type=str, required=True,
                       choices=['turn_on', 'turn_off', 'set_brightness', 'set_temperature', 'run_action'],
                       help='控制动作')
    parser.add_argument('--value', type=str, help='控制值')
    args = parser.parse_args()
    
    # 如果提供了名称，先查找设备
    if args.name and not args.did:
        devices = find_device_by_name(args.name)
        if not devices:
            print(f"❌ 未找到设备: {args.name}")
            return
        elif len(devices) == 1:
            args.did = devices[0]['did']
            print(f"✅ 找到设备: {devices[0]['name']} (ID: {args.did})")
        else:
            print(f"找到 {len(devices)} 个匹配设备:")
            for i, device in enumerate(devices, 1):
                print(f"  {i}. {device['name']} (ID: {device['did']})")
            print("\n请使用 --did 指定具体设备ID")
            return
    
    if not args.did:
        print("❌ 请提供 --did 或 --name 参数")
        return
    
    # 转换值为合适类型
    value = None
    if args.value:
        try:
            value = int(args.value)
        except ValueError:
            value = args.value
    
    # 执行控制
    control_device(args.did, args.action, value)

if __name__ == '__main__':
    main()
