#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Home Agent - 登录态强拦截

在一切设备操作（查询 / 控制）之前调用 require_auth()，统一检测：
  1. mijiaAPI 是否已安装
  2. 登录凭证 config/auth.json 是否存在
  3. auth.json 是否非空可读
  4. 能否用凭证构造 mijiaAPI 实例（登录是否过期/失效）
未就绪时打印明确、可执行的错误（JSON 模式带 need_auth 标记）并以非零退出，
避免把“未登录”误当成普通异常交给 agent 自行判断。
"""

import os
import sys
import json
import time


def _get_auth_path():
    return os.path.expanduser("~/.workbuddy/skills/xiaomi-home-agent/config/auth.json")


def _emit(msg, json_output):
    if json_output:
        print(json.dumps(
            {"ok": False, "error": msg, "need_auth": True},
            ensure_ascii=False, indent=2,
        ))
    else:
        print("🔒 " + msg)


def _fmt_ts(ms):
    """毫秒时间戳 → 可读本地时间字符串。"""
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ms) / 1000))
    except (TypeError, ValueError):
        return str(ms)


def require_auth(json_output=False):
    """检测登录态；未就绪则打印错误并 sys.exit（不返回）。就绪则返回 mijiaAPI 实例。"""
    # 1. mijiaAPI 是否安装
    try:
        from mijiaAPI import mijiaAPI
    except ImportError:
        _emit(
            "未安装 mijiaAPI，请先安装：pip install mijiaAPI",
            json_output,
        )
        sys.exit(2)

    # 2. auth.json 是否存在
    auth_path = _get_auth_path()
    if not os.path.exists(auth_path):
        _emit(
            "未登录米家：缺少登录凭证 config/auth.json。\n"
            "请先登录：运行 scripts/auth_mijia.py，或终端执行 `mijiaAPI -l` 用米家 APP 扫码；"
            "登录成功后凭证会自动保存，再重试本命令。",
            json_output,
        )
        sys.exit(3)

    # 3. auth.json 是否非空可读
    try:
        with open(auth_path, encoding="utf-8") as f:
            data = json.load(f)
        if not data or not isinstance(data, dict):
            raise ValueError("empty or malformed")
    except Exception:
        _emit(
            "登录凭证 config/auth.json 为空或不可读，请重新登录：运行 scripts/auth_mijia.py",
            json_output,
        )
        sys.exit(4)

    # 3.5 凭证过期检测（调用前，基于 auth.json 的 expireTime 毫秒时间戳）
    expire_ms = data.get("expireTime")
    if expire_ms is not None:
        try:
            expire_ms = float(expire_ms)
            if expire_ms <= time.time() * 1000:
                _emit(
                    "登录凭证已过期（过期时间：%s）。\n"
                    "请重新登录：运行 scripts/auth_mijia.py（或终端 `mijiaAPI -l` 重新扫码）。"
                    % _fmt_ts(expire_ms),
                    json_output,
                )
                sys.exit(6)
        except (TypeError, ValueError):
            pass  # 非数值则交给后续实例构造兜底

    # 4. 构造实例校验登录态（mijiaAPI 会加载已保存凭证）
    try:
        return mijiaAPI(auth_data_path=auth_path)
    except Exception as e:  # 登录已过期 / 凭证失效
        _emit(
            f"登录已过期或凭证无效：{e}\n"
            "请重新登录：运行 scripts/auth_mijia.py（或终端 `mijiaAPI -l` 重新扫码）。",
            json_output,
        )
        sys.exit(5)
