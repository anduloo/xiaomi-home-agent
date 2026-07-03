#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List Xiaomi Home scenes via Do1e mijiaAPI."""

import argparse
import json
import os
import sys
from typing import Any, Dict, List


def _get_auth_path() -> str:
    workspace_auth = os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth


def _home_label(home: Dict[str, Any]) -> str:
    return str(home.get("name") or home.get("id") or "未知家庭")


def list_scenes(json_output: bool = False, home_id: str = None) -> int:
    try:
        from mijiaAPI import mijiaAPI

        api = mijiaAPI(auth_data_path=_get_auth_path())
        homes = api.get_homes_list()
        results: List[Dict[str, Any]] = []

        for home in homes:
            current_home_id = str(home.get("id") or "")
            if home_id and current_home_id != str(home_id):
                continue
            scenes = api.get_scenes_list(home_id=current_home_id) or []
            results.append({
                "home_id": current_home_id,
                "home_name": home.get("name", ""),
                "count": len(scenes),
                "scenes": scenes,
            })

        if json_output:
            print(json.dumps({"ok": True, "homes": results}, ensure_ascii=False, indent=2))
            return 0

        if not results:
            print("📭 未找到家庭或场景")
            return 0

        for home in results:
            print(f"🏠 {home.get('home_name') or home.get('home_id')} — {home.get('count', 0)} 个场景")
            print("=" * 60)
            for scene in home.get("scenes", []):
                scene_id = scene.get("id") or scene.get("scene_id") or scene.get("us_id") or "?"
                name = scene.get("name") or scene.get("scene_name") or "未命名场景"
                enable = scene.get("enable")
                status = "启用" if enable is True else "禁用" if enable is False else "未知"
                print(f"- {name}  id={scene_id}  状态={status}")
            print()
        print("执行场景前请先确认 ID：")
        print("  python scripts/run_scene.py --scene-id <场景ID> --home-id <家庭ID> --yes")
        return 0
    except ImportError:
        print("❌ 未安装 mijiaAPI，请先安装依赖")
        return 1
    except Exception as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 获取场景失败: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="列出米家自动化/手动场景")
    parser.add_argument("--home-id", help="只查询指定家庭 ID")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    return list_scenes(json_output=args.json, home_id=args.home_id)


if __name__ == "__main__":
    sys.exit(main())
