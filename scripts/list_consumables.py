#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List Xiaomi Home consumable item life data via Do1e mijiaAPI."""

import argparse
import json
import os
import sys
from typing import Any, Dict, List


def _get_auth_path() -> str:
    workspace_auth = os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth


def _percent(value: Any) -> str:
    if value is None:
        return "未知"
    try:
        number = float(value)
        if number <= 1:
            number *= 100
        return f"{number:.0f}%"
    except (TypeError, ValueError):
        return str(value)


def list_consumables(json_output: bool = False, home_id: str = None) -> int:
    try:
        from mijiaAPI import mijiaAPI

        api = mijiaAPI(auth_data_path=_get_auth_path())
        homes = api.get_homes_list()
        results: List[Dict[str, Any]] = []

        for home in homes:
            current_home_id = str(home.get("id") or "")
            if home_id and current_home_id != str(home_id):
                continue
            items = api.get_consumable_items(home_id=current_home_id) or []
            results.append({
                "home_id": current_home_id,
                "home_name": home.get("name", ""),
                "count": len(items),
                "items": items,
            })

        if json_output:
            print(json.dumps({"ok": True, "homes": results}, ensure_ascii=False, indent=2))
            return 0

        total = sum(home.get("count", 0) for home in results)
        if total == 0:
            print("📭 未找到耗材寿命数据")
            return 0

        for home in results:
            if home.get("count", 0) == 0:
                continue
            print(f"🏠 {home.get('home_name') or home.get('home_id')} — {home.get('count', 0)} 项耗材")
            print("=" * 60)
            for item in home.get("items", []):
                name = item.get("name") or item.get("item_name") or item.get("device_name") or "未知耗材"
                device_name = item.get("device_name") or item.get("dev_name") or item.get("did") or "未知设备"
                remain = item.get("remain_life") or item.get("remain") or item.get("value") or item.get("life")
                print(f"- {device_name}: {name}  剩余={_percent(remain)}")
            print()
        return 0
    except ImportError:
        print("❌ 未安装 mijiaAPI，请先安装依赖")
        return 1
    except Exception as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 获取耗材数据失败: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="列出米家设备耗材寿命")
    parser.add_argument("--home-id", help="只查询指定家庭 ID")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    return list_consumables(json_output=args.json, home_id=args.home_id)


if __name__ == "__main__":
    sys.exit(main())
