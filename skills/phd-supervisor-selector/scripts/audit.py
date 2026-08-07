#!/usr/bin/env python3
"""
Vika table audit script for PhD Supervisor Selector skill.

Usage:
    python3 audit.py [DATASHEET_ID] [VIKA_TOKEN]

If arguments are not provided, reads from environment variables:
    VIKA_DATASHEET_ID and VIKA_TOKEN

Audit checks:
1. Cross links: URL domain does not match Department keyword
2. Notes format: missing Chinese ； delimiter or ending period 。
3. Notes with garbage/placeholder content
4. Missing required fields: 导师主页, 博士申请信息, 其他导师信息
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse

# ── Config ─────────────────────────────────────────────────────────────────────

BASE = "https://api.vika.cn/fusion/v1"

REQUIRED_FIELDS = ["导师主页", "博士申请信息", "其他导师信息"]
NOTES_FIELD = "备注"

# Fields that should contain URLs
URL_FIELDS = ["导师主页", "博士申请信息", "其他导师信息"]

# Garbage patterns in notes (case-insensitive)
GARBAGE_PATTERNS = [
    r"TODO",
    r"FIXME",
    r"placeholder",
    r"test\s*test",
    r"^.{0,3}$",  # too short to be useful
]

# ── Helpers ────────────────────────────────────────────────────────────────────


def vika_request(method, url, token, body=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            body_json = json.loads(body_text)
            msg = body_json.get("message", str(e))
        except Exception:
            msg = body_text[:200]
        print(f"  [ERROR] API {e.code}: {msg}")
        return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def get_all_records(datasheet_id, token):
    """Fetch all records from the datasheet."""
    all_records = []
    page_token = None

    while True:
        params = urllib.parse.urlencode({
            "maxRecords": 200,
            "pageSize": 200,
        })
        if page_token:
            params += f"&pageToken={urllib.parse.quote(page_token)}"

        url = f"{BASE}/datasheets/{datasheet_id}/records?{params}"
        result = vika_request("GET", url, token)
        if not result:
            break

        data = result.get("data", {})
        records = data.get("records", [])
        all_records.extend(records)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_records


def extract_domain(url_str):
    """Extract domain from a URL string. Handles Vika URL field format."""
    if not url_str:
        return ""
    # Vika URL fields may be returned as {"text": "...", "link": "..."}
    if isinstance(url_str, dict):
        url_str = url_str.get("link", "") or url_str.get("text", "")
    # Extract domain
    m = re.search(r"https?://([^/]+)", str(url_str))
    return m.group(1) if m else ""


def check_notes_format(notes):
    """Check if notes field follows the required format."""
    if not notes:
        return []
    issues = []
    text = str(notes)

    # Check for Chinese ； delimiter
    if "；" not in text and len(text) > 10:
        issues.append("missing Chinese delimiter ；")

    # Check for ending period 。
    if not text.rstrip().endswith("。"):
        issues.append("missing ending period 。")

    # Check for garbage patterns
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(f"possible garbage content (matches: {pattern})")

    return issues


def audit_records(records):
    """Run all audit checks on records. Returns list of (record_id, name, issues)."""
    results = []

    for rec in records:
        rid = rec["recordId"]
        f = rec.get("fields", {})
        name = f.get("导师", "(unknown)")

        issues = []

        # 1. Missing required fields
        for field in REQUIRED_FIELDS:
            val = f.get(field)
            if not val or (isinstance(val, str) and not val.strip()):
                issues.append(f"missing {field}")

        # 2. Notes format
        notes = f.get(NOTES_FIELD, "")
        if notes:
            note_issues = check_notes_format(notes)
            issues.extend([f"备注: {i}" for i in note_issues])

        # 3. Cross-link check: URL domain vs Department
        homepage = f.get("导师主页", "")
        dept = f.get("Department", "")
        if homepage and dept:
            domain = extract_domain(homepage)
            # Simple check: domain should contain a keyword from the department/school
            if domain and dept:
                # Extract likely keyword from dept (e.g., "University of Hong Kong" -> "hku")
                dept_lower = dept.lower().replace(" ", "").replace("-", "")
                if domain and domain.lower() not in dept_lower and dept_lower not in domain.lower():
                    # Only flag if clearly mismatched (both non-empty)
                    issues.append(f"cross-link: 导师主页 domain ({domain}) may not match Department ({dept})")

        if issues:
            results.append((rid, name, issues))

    return results


def main():
    datasheet_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VIKA_DATASHEET_ID", "")
    token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VIKA_TOKEN", "")

    if not datasheet_id:
        print("Usage: python3 audit.py [DATASHEET_ID] [VIKA_TOKEN]")
        print("  or set VIKA_DATASHEET_ID and VIKA_TOKEN environment variables")
        sys.exit(1)

    if not token:
        print("[ERROR] VIKA_TOKEN not set. Pass as argument or set environment variable.")
        sys.exit(1)

    print(f"Auditing datasheet: {datasheet_id}")
    print("-" * 60)

    records = get_all_records(datasheet_id, token)
    print(f"Fetched {len(records)} records.\n")

    results = audit_records(records)

    if not results:
        print("✅ No issues found!")
    else:
        print(f"Found issues in {len(results)} record(s):\n")
        for rid, name, issues in results:
            print(f"  {name} (id: {rid[:12]}...)")
            for issue in issues:
                print(f"    - {issue}")
            print()

    print("-" * 60)
    print(f"Audit complete. {len(results)} record(s) with issues.")


if __name__ == "__main__":
    main()
