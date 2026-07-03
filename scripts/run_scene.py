#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a Xiaomi Home scene via Do1e mijiaAPI with explicit confirmation."""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def _get_auth_path() -> str:
    workspace_auth = os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth


def _scene_id(scene: Dict[str, Any]) -> str:
    return str(scene.get("id") or scene.get("scene_id") or scene.get("us_id") or "")


def _scene_name(scene: Dict[str, Any]) -> str:
    return str(scene.get("name") or scene.get("scene_name") or "未命名场景")


def _find_scene(api: Any, scene_id: str = None, name: str = None, home_id: str = None) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    matches: List[Dict[str, Any]] = []
    homes = api.get_homes_list()
    for home in homes:
        current_home_id = str(home.get("id") or "")
        if home_id and current_home_id != str(home_id):
            continue
        for scene in api.get_scenes_list(home_id=current_home_id) or []:
            item = {
                "home_id": current_home_id,
                "home_name": home.get("name", ""),
                "scene": scene,
            }
            if scene_id and _scene_id(scene) == str(scene_id):
                return item, [item]
            if name and name in _scene_name(scene):
                matches.append(item)
    if len(matches) == 1:
        return matches[0], matches
    return None, matches


def run_scene(scene_id: str = None, name: str = None, home_id: str = None, yes: bool = False, json_output: bool = False) -> int:
    try:
        from mijiaAPI import mijiaAPI

        api = mijiaAPI(auth_data_path=_get_auth_path())
        target, matches = _find_scene(api, scene_id=scene_id, name=name, home_id=home_id)

        if not target:
            output = {"ok": False, "error": "未找到唯一场景", "matches": matches}
            if json_output:
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                print("❌ 未找到唯一场景，未执行")
                for match in matches:
                    scene = match["scene"]
                    print(f"- {_scene_name(scene)}  id={_scene_id(scene)}  home={match.get('home_name')}({match.get('home_id')})")
            return 1

        scene = target["scene"]
        actual_scene_id = _scene_id(scene)
        actual_home_id = target["home_id"]
        preview = {
            "scene_id": actual_scene_id,
            "scene_name": _scene_name(scene),
            "home_id": actual_home_id,
            "home_name": target.get("home_name"),
        }

        if not yes:
            output = {"ok": False, "dry_run": True, "message": "未加 --yes，未执行场景", "target": preview}
            if json_output:
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                print("⚠️  未加 --yes，未执行场景。将要执行：")
                print(f"  场景: {preview['scene_name']} ({preview['scene_id']})")
                print(f"  家庭: {preview['home_name']} ({preview['home_id']})")
                print("确认后执行：")
                print(f"  python scripts/run_scene.py --scene-id {preview['scene_id']} --home-id {preview['home_id']} --yes")
            return 2

        ok = api.run_scene(scene_id=actual_scene_id, home_id=actual_home_id)
        output = {"ok": bool(ok), "target": preview}
        if json_output:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print("✅ 场景执行请求已发送" if ok else "❌ 场景执行失败")
            print(f"  场景: {preview['scene_name']} ({preview['scene_id']})")
        return 0 if ok else 1
    except ImportError:
        print("❌ 未安装 mijiaAPI，请先安装依赖")
        return 1
    except Exception as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 执行场景失败: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="执行米家场景，默认 dry-run，必须 --yes 才执行")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scene-id", help="场景 ID")
    group.add_argument("--name", help="场景名称关键词")
    parser.add_argument("--home-id", help="家庭 ID（建议提供，避免多家庭重名）")
    parser.add_argument("--yes", action="store_true", help="确认执行场景")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    return run_scene(scene_id=args.scene_id, name=args.name, home_id=args.home_id, yes=args.yes, json_output=args.json)


if __name__ == "__main__":
    sys.exit(main())
