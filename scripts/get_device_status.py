#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Home Agent Skill - 设备状态查询
"""

import sys
import os
import argparse

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_auth_path():
    workspace_auth = os.path.expanduser('~/.workbuddy/skills/xiaomi-home-agent/config/auth.json')
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth

def get_device_status(did):
    """获取设备状态"""
    try:
        from mijiaAPI import mijiaAPI
        
        api = mijiaAPI(auth_data_path=_get_auth_path())
        
        # 从设备列表中查找
        devices = api.get_devices_list()
        device = None
        for d in devices:
            if d.get('did') == did:
                device = d
                break
        
        if not device:
            print(f"❌ 未找到设备: {did}")
            return
        
        name = device.get('name', '未知设备')
        model = device.get('model', 'N/A')
        online = device.get('isOnline', False)
        
        print(f"📱 设备状态: {name}")
        print(f"   型号: {model}")
        print(f"   状态: {'🟢 在线' if online else '🔴 离线'}")
        print(f"   IP: {device.get('localip', 'N/A')}")
        print(f"   WiFi: {device.get('ssid', 'N/A')}")
        print(f"   信号: {device.get('rssi', 'N/A')} dBm")
        print(f"   MAC: {device.get('mac', 'N/A')}")
        
        # 传感器类设备：双重扫描 — 标准 PIID (1-9) + BLE/扩展 PIID (1000+)
        is_sensor = any(kw in model.lower() for kw in
                        ['air', 'sensor', 'occupy', 'motion', 'presence',
                         'detector', 'weather', 'monitor', 'temp'])
        if is_sensor:
            print()
            print("🌡️  获取传感器数据...")
            try:
                params = []
                # 1. 标准范围 (piid 1-9)，覆盖开关、亮度、温度等
                for piid in range(1, 10):
                    params.append({'did': did, 'siid': 2, 'piid': piid})
                # 2. 环境属性 (siid=3)，温度/湿度/PM2.5/CO2/TVOC/甲醛
                for piid in range(1, 8):
                    params.append({'did': did, 'siid': 3, 'piid': piid})
                # 3. BLE/人体存在传感器专属高 PIID 范围
                #    occupancy-status=1078, no-one-duration=1079, has-someone-duration=1080
                for piid in (1005, 1078, 1079, 1080):
                    params.append({'did': did, 'siid': 2, 'piid': piid})
                # 4. 电池/信号属性
                for piid in (1, 1003):
                    params.append({'did': did, 'siid': 4, 'piid': piid})

                # 常用 PIID 中文名
                label_map = {
                    (2,1):"开关", (2,2):"亮度/位置", (2,3):"目标温度", (2,4):"模式",
                    (2,5):"风速", (2,6):"摆风", (2,7):"温度", (2,8):"湿度",
                    (2,1005):"光照度(lux)", (2,1078):"有人状态",
                    (2,1079):"无人持续(秒)", (2,1080):"有人持续(秒)",
                    (3,1):"温度(℃)", (3,2):"湿度(%)", (3,3):"PM2.5",
                    (3,4):"CO2(ppm)", (3,5):"TVOC", (3,6):"甲醛",
                    (4,1):"电量(%)", (4,1003):"电量(%)",
                }

                result = api.get_devices_prop(params)
                found = []
                for item in result:
                    if item.get('code') == 0:
                        siid = item.get('siid')
                        piid = item.get('piid')
                        value = item.get('value')
                        label = label_map.get((siid, piid), f"siid{siid}.piid{piid}")
                        found.append((label, value))

                if found:
                    print("   传感器数据:")
                    for label, value in found:
                        print(f"     - {label}: {value}")
                else:
                    print("   ⚠️  未找到可读取属性")
                    print("   💡 该设备可能需通过 MIoT spec 查询属性定义")

            except Exception as e:
                print(f"   ⚠️  获取传感器数据失败: {e}")
        
    except ImportError:
        print("❌ 未安装 mijiaAPI")
    except Exception as e:
        print(f"❌ 查询失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='获取设备状态')
    parser.add_argument('--did', type=str, required=True, help='设备ID')
    args = parser.parse_args()
    
    get_device_status(args.did)

if __name__ == '__main__':
    main()
