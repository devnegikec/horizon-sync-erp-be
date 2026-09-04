"""Shared zero-dependency helpers for the QR receiving test scripts.

Uses only the Python standard library (urllib) so the scripts run with a
plain ``python3`` — no ``requests`` needed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# ── Config ────────────────────────────────────────────────────────────────────
IDENTITY_URL = os.environ.get("IDENTITY_URL", "http://localhost:8000")
CORE_URL = os.environ.get("CORE_URL", "http://localhost:8001")

EMAIL = os.environ.get("WMS_EMAIL", "ttkwmsmanager@prestige.com")
PASSWORD = os.environ.get("WMS_PASSWORD", "Test@123")


def _request(method: str, url: str, token: str | None = None, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = resp.read()
            return json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}\n{detail}") from exc


def login() -> str:
    """Log in to the identity service and return a bearer access token."""
    data = _request(
        "POST",
        f"{IDENTITY_URL}/api/v1/identity/login",
        body={"email": EMAIL, "password": PASSWORD},
    )
    token = (data or {}).get("access_token")
    if not token:
        sys.exit(f"[FATAL] Login response missing access_token: {data}")
    return token


def api_get(path: str, token: str, params: dict | None = None):
    if params:
        path = f"{path}?{urllib.parse.urlencode(params)}"
    return _request("GET", f"{CORE_URL}/api/v1{path}", token=token)


def api_post(path: str, token: str, body=None):
    return _request("POST", f"{CORE_URL}/api/v1{path}", token=token, body=body)
