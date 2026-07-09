#!/usr/bin/env python3
"""Shared Feishu Bitable API client using only Python standard library."""
import json
import urllib.request
import urllib.parse
import urllib.error
import time

import feishu_config as cfg


class FeishuAPIError(Exception):
    """Raised when Feishu API returns an error code."""
    def __init__(self, message, code=None, response=None):
        super().__init__(message)
        self.code = code
        self.response = response


def get_tenant_token():
    """Fetch tenant_access_token from Feishu auth endpoint."""
    req = urllib.request.Request(
        cfg.AUTH_URL,
        data=json.dumps({
            "app_id": cfg.APP_ID,
            "app_secret": cfg.APP_SECRET,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise FeishuAPIError(f"Auth failed: HTTP {e.code} {body}", response=body)

    if data.get("code") != 0:
        raise FeishuAPIError(
            f"Auth failed: {data.get('msg')} (code {data.get('code')})",
            code=data.get("code"),
            response=data,
        )
    return data["tenant_access_token"]


_TOKEN = None
_TOKEN_EXPIRES_AT = 0


def _get_token():
    """Return cached tenant token, refreshing if near expiry."""
    global _TOKEN, _TOKEN_EXPIRES_AT
    now = time.time()
    # Token TTL is 7200s; refresh 60s early.
    if _TOKEN is None or now >= _TOKEN_EXPIRES_AT - 60:
        _TOKEN = get_tenant_token()
        _TOKEN_EXPIRES_AT = now + 7000
    return _TOKEN


def api(method, path, data=None, params=None, field_key="name"):
    """Call Feishu Bitable API.

    Args:
        method: HTTP method.
        path: API path after /apps/{APP_TOKEN}/tables/{TABLE_ID}, e.g. "/records".
        data: Optional dict body for POST/PATCH.
        params: Optional dict of query parameters.
        field_key: "name" (default) or "id" for field naming in responses.

    Returns:
        Parsed JSON response dict.
    """
    base = f"{cfg.BASE_URL}/apps/{cfg.APP_TOKEN}/tables/{cfg.TABLE_ID}"
    url = base + path

    qs_parts = {}
    if params:
        qs_parts.update(params)
    if field_key:
        qs_parts["field_key"] = field_key
    if qs_parts:
        url += "?" + urllib.parse.urlencode(qs_parts, doseq=True)

    headers = {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }

    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = None
        raise FeishuAPIError(
            f"Feishu API error: {method} {path} -> HTTP {e.code} {body[:500]}",
            code=parsed.get("code") if parsed else None,
            response=parsed or body,
        )

    if result.get("code") != 0:
        raise FeishuAPIError(
            f"Feishu API error: {method} {path} -> {result.get('msg')} (code {result.get('code')})",
            code=result.get("code"),
            response=result,
        )
    return result


def get_records(page_size=500, field_key="name"):
    """Fetch all records from the table.

    Args:
        page_size: Page size (max 500).
        field_key: "name" or "id".

    Returns:
        List of record dicts.
    """
    all_records = []
    page_token = None
    while True:
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        resp = api("GET", "/records", params=params, field_key=field_key)
        data = resp.get("data", {})
        all_records.extend(data.get("items", []))
        if not data.get("has_more", False):
            break
        page_token = data.get("page_token")
    return all_records


def update_record(record_id, fields, field_key="name"):
    """Update a single record."""
    return api(
        "PUT",
        f"/records/{record_id}",
        data={"fields": fields},
        params={"user_id_type": "open_id"},
        field_key=field_key,
    )


def batch_update_records(records, field_key="name"):
    """Update multiple records (uses single-record API for compatibility).

    Args:
        records: List of dicts {"record_id": str, "fields": dict}.

    Returns:
        API response dict with accumulated results.
    """
    if not records:
        return {"data": {"records": []}}

    updated = []
    for rec in records:
        resp = update_record(rec["record_id"], rec["fields"], field_key=field_key)
        updated.append(resp.get("data", {}).get("record", rec))

    return {"data": {"records": updated}}


def get_fields():
    """Return list of field schema dicts."""
    resp = api("GET", "/fields", params={"page_size": 500})
    return resp.get("data", {}).get("items", [])


def field_exists(field_name):
    """Check if a field with the given name already exists."""
    return any(f.get("field_name") == field_name for f in get_fields())


def add_field(field_name, field_type, property=None):
    """Add a new field to the table.

    Args:
        field_name: Display name of the field.
        field_type: Feishu field type integer (see Feishu docs).
            1=Text, 2=Number, 5=DateTime, 3=SingleSelect, etc.
        property: Optional property dict for the field type.

    Returns:
        API response dict or None if field already exists.
    """
    if field_exists(field_name):
        return None
    # Feishu field creation endpoint uses "type", not "field_type".
    payload = {"field_name": field_name, "type": field_type}
    if property is not None:
        payload["property"] = property
    return api("POST", "/fields", data=payload)


def ensure_scheduler_fields():
    """Ensure all scheduler-required fields exist in the table."""
    added = []
    # DateTime for lock timestamp
    if add_field(cfg.FIELD_LOCK_TIME, 5, {"date_formatter": "yyyy/MM/dd HH:mm", "auto_fill": False}):
        added.append(cfg.FIELD_LOCK_TIME)
    # Text for node id
    if add_field(cfg.FIELD_NODE, 1):
        added.append(cfg.FIELD_NODE)
    # Number for error count
    if add_field(cfg.FIELD_ERROR_COUNT, 2, {"formatter": "0"}):
        added.append(cfg.FIELD_ERROR_COUNT)
    # Text for failure reason
    if add_field(cfg.FIELD_FAILURE_REASON, 1):
        added.append(cfg.FIELD_FAILURE_REASON)
    # SingleSelect for confidence
    if add_field(cfg.FIELD_CONFIDENCE, 3, {
        "options": [
            {"name": "通过", "color": 0},
            {"name": "未通过", "color": 1},
        ]
    }):
        added.append(cfg.FIELD_CONFIDENCE)
    return added
