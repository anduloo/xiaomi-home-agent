#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discover Xiaomi device MIoT spec properties via Do1e mijiaAPI.
Queries device model, fetches MIoT spec from miot-spec.org, and scans
PIID ranges to discover writable/readable properties — reducing hardcoded siid/piid maps.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def _get_auth_path() -> str:
    workspace_auth = os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")
    os.makedirs(os.path.dirname(workspace_auth), exist_ok=True)
    return workspace_auth


def _fetch_miot_spec(model: str) -> Optional[Dict[str, Any]]:
    """Try MIoT spec server for a model — returns parsed JSON or None."""
    if not model:
        return None
    # Some models use direct lookup: urn:miot-spec-v2:device:<type>:<model>:<version>
    # Try the search-by-model endpoint first
    try:
        url = f"https://miot-spec.org/miot-spec-v2/instances?model={model}"
        req = urllib.request.Request(url, headers={"User-Agent": "xiaomi-home-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            instances = data.get("instances") or []
            # Pick the first instance after sorting by version
            if instances:
                instances.sort(key=lambda x: x.get("version", 0), reverse=True)
                instance = instances[0]
                return {
                    "type": instance.get("type", ""),
                    "model": instance.get("model", model),
                    "version": instance.get("version", 0),
                    "services": instance.get("services", []),
                }
    except Exception:
        pass
    return None


def _scan_properties(api: Any, did: str, siid_ranges: List[tuple]) -> List[Dict[str, Any]]:
    """Scan PIID ranges on a device and return discovered properties."""
    discovered: List[Dict[str, Any]] = []
    for siid, start, end in siid_ranges:
        props = [{"did": did, "siid": siid, "piid": piid} for piid in range(start, end + 1)]
        if not props:
            continue
        try:
            results = api.get_devices_prop(props)
            if not isinstance(results, list):
                continue
            for item in results:
                if isinstance(item, dict) and item.get("code") == 0:
                    discovered.append({
                        "siid": item.get("siid", siid),
                        "piid": item.get("piid", 0),
                        "value": item.get("value"),
                        "description": "",
                    })
        except Exception:
            continue
    return discovered


def inspect_device(did: str = None, name: str = None, model: str = None,
                   json_output: bool = False, scan: bool = False) -> int:
    try:
        from mijiaAPI import mijiaAPI

        api = mijiaAPI(auth_data_path=_get_auth_path())

        # Resolve device
        actual_model = model
        actual_did = did
        actual_name = name
        if not actual_model or not actual_did:
            devices = api.get_devices_list()
            for d in devices:
                match = False
                if did and str(d.get("did", "")) == str(did):
                    match = True
                if name and name in str(d.get("name", "")):
                    match = True
                if match:
                    actual_did = str(d.get("did", ""))
                    actual_model = actual_model or d.get("model", "")
                    actual_name = d.get("name", actual_name or "")
                    break

        if not actual_model:
            output = {"ok": False, "error": "未找到匹配设备或缺少 model 信息"}
            print(json.dumps(output, ensure_ascii=False, indent=2) if json_output else output["error"])
            return 1

        result: Dict[str, Any] = {
            "ok": True,
            "did": actual_did,
            "name": actual_name,
            "model": actual_model,
        }

        # Fetch MIoT spec
        spec = _fetch_miot_spec(actual_model)
        if spec:
            result["miot_spec"] = {
                "type": spec["type"],
                "version": spec["version"],
                "service_count": len(spec.get("services", [])),
                "services": [],
            }
            for svc in spec.get("services", []):
                svc_info = {
                    "siid": svc.get("iid", svc.get("siid", 0)),
                    "name": svc.get("description", svc.get("name", "")),
                    "property_count": len(svc.get("properties", [])),
                    "properties": [],
                }
                for prop in svc.get("properties", []):
                    prop_info = {
                        "piid": prop.get("iid", prop.get("piid", 0)),
                        "name": prop.get("description", prop.get("name", "")),
                        "format": prop.get("format", ""),
                        "access": ", ".join(prop.get("access", [])),
                        "unit": prop.get("unit", ""),
                        "value_range": prop.get("value-range", []),
                    }
                    svc_info["properties"].append(prop_info)
                result["miot_spec"]["services"].append(svc_info)
        else:
            result["miot_spec"] = None

        # Scan properties if requested and DID is known
        if scan and actual_did:
            ranges = [
                (2, 1, 9),
                (3, 1, 9),
                (4, 1, 9),
                (2, 1005, 1080),
                (4, 1003, 1003),
            ]
            scanned = _scan_properties(api, actual_did, ranges)
            # Merge description from spec if available
            if spec:
                desc_map: Dict[tuple, str] = {}
                for svc in spec.get("services", []):
                    siid_val = svc.get("iid", svc.get("siid", 0))
                    for prop in svc.get("properties", []):
                        piid_val = prop.get("iid", prop.get("piid", 0))
                        desc_map[(int(siid_val), int(piid_val))] = prop.get("description", prop.get("name", ""))
                for p in scanned:
                    key = (p["siid"], p["piid"])
                    if key in desc_map:
                        p["description"] = desc_map[key]
            result["scanned_properties"] = scanned
            result["scanned_count"] = len(scanned)

        if json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        # Pretty output
        print(f"🔍 设备规格: {result.get('name') or actual_model}")
        print(f"  模型: {result['model']}")
        if result.get("did"):
            print(f"  DID:  {result['did']}")
        print()

        spec_data = result.get("miot_spec")
        if spec_data:
            print(f"📋 MIoT Spec (type={spec_data.get('type','')}, version={spec_data.get('version','')})")
            print(f"   服务数: {spec_data.get('service_count', 0)}")
            print("=" * 60)
            for svc in spec_data.get("services", []):
                print(f"\n  📦 SIID={svc['siid']} — {svc['name']} ({svc['property_count']} 个属性)")
                print(f"  {'PIID':<6} {'名称':<24} {'格式':<12} {'权限':<16} {'取值范围'}")
                print(f"  {'-'*60}")
                for prop in svc.get("properties", []):
                    piid_str = str(prop["piid"])
                    name_str = prop["name"][:22]
                    fmt_str = prop["format"][:10]
                    access_str = prop["access"][:14]
                    range_str = str(prop.get("value_range", []))[:20]
                    print(f"  {piid_str:<6} {name_str:<24} {fmt_str:<12} {access_str:<16} {range_str}")
        else:
            print("⚠️  MIoT Spec 服务器未返回数据（model 较新或网络问题）")

        if result.get("scanned_properties"):
            print(f"\n📡 在线探测属性 ({result['scanned_count']} 个有效):")
            for p in result["scanned_properties"]:
                desc = p.get("description") or ""
                print(f"  SIID={p['siid']}, PIID={p['piid']}, value={p['value']}  {desc}")

        if not spec_data and not result.get("scanned_properties"):
            print("💡 提示: 使用 --scan 可在线探测设备属性")
            print("   python scripts/get_device_info.py --name \"设备名\" --scan")

        return 0
    except ImportError:
        print("❌ 未安装 mijiaAPI")
        return 1
    except Exception as exc:
        output = {"ok": False, "error": str(exc)}
        print(json.dumps(output, ensure_ascii=False, indent=2) if json_output else f"❌ {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="发现米家设备 MIoT 规格和可探测属性")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--did", help="设备 DID")
    group.add_argument("--name", help="设备名称关键词")
    group.add_argument("--model", help="设备型号（如 lumi.sensor_ht）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--scan", action="store_true", help="在线探测设备属性（需 DID）")
    args = parser.parse_args()
    return inspect_device(did=args.did, name=args.name, model=args.model,
                          json_output=args.json, scan=args.scan)


if __name__ == "__main__":
    sys.exit(main())
