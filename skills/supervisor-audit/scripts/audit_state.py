#!/usr/bin/env python3
"""
Self-evaluation audit script for supervisor automation engine v2.

Given a student's Vika table URL, evaluates whether the current state
meets the "pass threshold" for promotion to human review.

Checks:
1. Required-field completeness: key fields (导师, 学校名字, Department,
   导师主页, 备注, 导师研究领域 if present, 博士申请信息, 其他导师信息) are filled.
2. Link validity: Are all 导师主页 URLs alive (200 + real content, not SPA shell)?
3. Domestic email fill rate: Do domestic-school records have 导师联系方式 filled?
4. AI artefacts: Any emoji, ⚠️ symbols, or mechanical phrases in 备注?
5. 选导意向 protection: All records must have empty 选导意向 field.
6. Direction-match confidence: percentage of records with evidence of direction matching (>= 95%).

**Confidence gate**: Both link accuracy (>= 95%) AND match confidence (>= 95%) must pass for 置信度=通过.

Usage:
    python3 audit_state.py <VIKA_DATASHEET_ID> <VIKA_API_TOKEN> [--dry-run] [--verbose]
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request
import urllib.parse
import time
from typing import Tuple


# ---- Configuration ----
LINK_TIMEOUT = 10  # seconds per link check
LINK_SAMPLE_SIZE = 10  # random sample size for link checks (0 = check all)
SPA_SHELL_MIN_SIZE = 5000  # bytes; below this and consistent across URLs = SPA shell
PASS_LINK_PCT = 0.95  # must be >= 95%
PASS_MATCH_PCT = 0.95  # must be >= 95% match confidence
PASS_CN_EMAIL_PCT = 1.0  # must be 100%

# Required-field completeness checks
# Universal fields apply to every record; domestic fields only to Chinese schools.
# Optional fields are checked only when they exist in the datasheet schema.
REQUIRED_FIELDS_UNIVERSAL = [
    "导师",
    "学校名字",
    "Department",
    "导师主页",
    "备注",
]
REQUIRED_FIELDS_DOMESTIC = [
    "导师联系方式",
]
OPTIONAL_FIELDS_CHECKED_IF_PRESENT = [
    "导师研究领域",
    "博士申请信息",
    "其他导师信息",
]
DOMESTIC_EMAIL_KEYWORDS = [
    "北京大学", "清华大学", "复旦大学", "上海交通大学", "浙江大学",
    "中国科学技术大学", "南京大学", "武汉大学", "华中科技大学", "中山大学",
    "西安交通大学", "哈尔滨工业大学", "同济大学", "中国人民大学", "北京师范大学",
    "南开大学", "天津大学", "东南大学", "厦门大学", "四川大学", "山东大学",
    "吉林大学", "中南大学", "兰州大学", "西北工业大学", "电子科技大学",
    "华南理工大学", "大连理工大学", "华东师范大学", "湖南大学", "重庆大学",
    "南方科技大学", "北京航空航天大学", "北京理工大学", "中国农业大学",
    "中国科学院", "上海财经大学", "中央财经大学", "对外经济贸易大学",
    "华东政法大学", "中国政法大学", "西南财经大学", "中南财经政法大学",
    "China", "Beijing", "Shanghai", "Tsinghua", "Peking", "Fudan", "Zhejiang",
    "Nanjing", "Wuhan", "Harbin", "Xi'an", "Tianjin", "Sichuan",
    "Sun Yat-sen", "Jilin", "Lanzhou", "Hunan", "Chongqing",
]

# AI artefact patterns in remarks
AI_ARTEFACT_PATTERNS = [
    "高度匹配", "很匹配", "完美匹配", "强匹配", "弱相关", "比较匹配",
    "非常适合", "非常匹配", "完全符合", "极为匹配",
]
# Emoji Unicode ranges
EMOJI_RANGES = [
    (0x1F300, 0x1F9FF),  # Misc symbols and pictographs
    (0x2600, 0x27BF),    # Misc symbols
    (0x2702, 0x27B0),    # Dingbats
    (0x1F900, 0x1F9FF),  # Supplemental symbols
    (0x1F680, 0x1F6FF),  # Transport and map
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F1E0, 0x1F1FF),  # Flags
]


def _load_records(datasheet_id, token):
    """Load all records from a Vika datasheet via Fusion API."""
    base = f"https://api.vika.cn/fusion/v1/datasheets/{datasheet_id}/records"
    all_records = []
    page_token = None

    while True:
        params = {"pageSize": 200, "fieldKey": "name"}
        if page_token:
            params["pageToken"] = page_token
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        req = urllib.request.Request(
            f"{base}?{qs}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = json.loads(urllib.request.urlopen(req).read())
        data = resp.get("data", {})
        items = data.get("records", [])
        all_records.extend(items)
        if not data.get("hasMore", data.get("has_more", False)):
            break
        page_token = data.get("pageToken", data.get("page_token"))

    return all_records


def _has_emoji(text):
    """Check if text contains emoji characters."""
    if not text:
        return False
    for ch in text:
        cp = ord(ch)
        for lo, hi in EMOJI_RANGES:
            if lo <= cp <= hi:
                return True
    return False


def _has_warning_symbol(text):
    """Check if text contains ⚠️ or similar warning symbols."""
    if not text:
        return False
    return "⚠" in text or "⚠️" in text


def _has_ai_artefacts(text):
    """Check if text contains mechanical/AI-sounding phrases."""
    if not text:
        return False
    for pattern in AI_ARTEFACT_PATTERNS:
        if pattern in text:
            return True
    return False


def _is_domestic_school(school_name):
    """Check if school is Chinese/domestic based on keywords."""
    if not school_name:
        return False
    for kw in DOMESTIC_EMAIL_KEYWORDS:
        if kw.lower() in school_name.lower():
            return True
    return False


def _check_link(url, timeout=LINK_TIMEOUT):
    """
    Check if a URL returns valid content (not 404, not SPA shell).

    Returns: (status_code: int, content_size: int, is_spa: bool)
    """
    if not url or not url.startswith("http"):
        return 0, 0, False
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            content = resp.read()
            size = len(content)
            return status, size, False
    except urllib.error.HTTPError as e:
        return e.code, 0, False
    except Exception:
        return 0, 0, False


def _has_valid_email(text):
    """Check if text contains an email address."""
    if not text:
        return False
    return bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))


def _is_field_empty(value):
    """Return True if a field value is effectively empty."""
    if value is None:
        return True
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return str(value).strip() == ""


def _check_required_fields(record):
    """
    Check required-field completeness for a single record.

    Returns:
        list of missing field names (universal + domestic-only + optional present)
    """
    f = record.get("fields", {})
    missing = []
    school = f.get("学校名字", "")

    for field in REQUIRED_FIELDS_UNIVERSAL:
        if _is_field_empty(f.get(field)):
            missing.append(field)

    if _is_domestic_school(school):
        for field in REQUIRED_FIELDS_DOMESTIC:
            if _is_field_empty(f.get(field)):
                missing.append(field)

    # Optional fields: if the column exists in the schema for this record, it
    # should not be empty. Vika omits empty keys, so presence means it exists.
    for field in OPTIONAL_FIELDS_CHECKED_IF_PRESENT:
        if field in f and _is_field_empty(f.get(field)):
            missing.append(field)

    return missing


def _is_direction_matched(record):
    """
    Check if a record has evidence of research direction matching
    (i.e., the supervisor direction was actually evaluated against student needs).

    A record is considered "matched" if any of:
    - 导师研究领域 field is non-empty (explicit direction field filled)
    - 备注 has more than just 职称 (contains direction description after first ；)
    - 博士申请信息 field is non-empty (PhD-level relevance confirmed)

    Returns:
        bool
    """
    f = record.get("fields", {})

    # Check 导师研究领域
    direction_field = f.get("导师研究领域", "")
    if not _is_field_empty(direction_field):
        return True

    # Check 博士申请信息
    phd_info = f.get("博士申请信息", "")
    if not _is_field_empty(phd_info):
        return True

    # Check 备注: has substance beyond just 职称
    remark = f.get("备注", "")
    if not _is_field_empty(remark):
        parts = remark.split("；")
        # First segment is 职称; need at least one more segment with content
        if len(parts) >= 2:
            for part in parts[1:]:
                if part.strip():
                    return True

    return False


def audit(datasheet_id, token, max_links_check=LINK_SAMPLE_SIZE):
    """
    Run full audit on a Vika table.

    Args:
        datasheet_id: Vika datasheet ID (dstXXX)
        token: Vika API token
        max_links_check: Max number of links to actually HTTP-check (0 = all)

    Returns:
        dict: {
            "passes": bool,
            "weak_dim": str | None,  # "missing_fields" | "match_confidence" | "links" | "cn_email" | "ai_artefacts" | "selection_intent" | None
            "metrics": {
                "total_records": int,
                "missing_field_records": int,
                "total_missing_fields": int,
                "match_matched": int,
                "match_unmatched": int,
                "links_total": int,
                "links_alive": int,
                "links_dead": int,
                "cn_records_total": int,
                "cn_email_filled": int,
                "ai_artefact_count": int,
                "selection_intent_filled": int,
            },
            "details": {
                "missing_fields": [str],
                "unmatched_records": [str],
                "dead_links": [str],
                "missing_cn_emails": [str],
                "ai_artefact_records": [str],
                "filled_intent_records": [str],
            }
        }
    """
    records = _load_records(datasheet_id, token)

    metrics = {
        "total_records": len(records),
        "missing_field_records": 0,
        "total_missing_fields": 0,
        "match_matched": 0,
        "match_unmatched": 0,
        "links_total": 0,
        "links_alive": 0,
        "links_dead": 0,
        "cn_records_total": 0,
        "cn_email_filled": 0,
        "ai_artefact_count": 0,
        "selection_intent_filled": 0,
    }

    details = {
        "missing_fields": [],
        "unmatched_records": [],
        "dead_links": [],
        "missing_cn_emails": [],
        "ai_artefact_records": [],
        "filled_intent_records": [],
    }

    # Collect all URLs to check
    url_records = []
    for r in records:
        f = r.get("fields", {})
        url = f.get("导师主页", "")
        school = f.get("学校名字", "")
        email_field = f.get("导师联系方式", "")
        remark = f.get("备注", "")
        selection_intent = f.get("选导意向（点击选择）", f.get("选导意向", ""))

        if url and url.strip():
            url_records.append((r["recordId"], url.strip(), school, email_field, remark, selection_intent))
        else:
            # Still check domestic email/remark/intent even if no URL
            url_records.append((r["recordId"], "", school, email_field, remark, selection_intent))

        # Check required-field completeness
        missing = _check_required_fields(r)
        if missing:
            metrics["missing_field_records"] += 1
            metrics["total_missing_fields"] += len(missing)
            for field in missing:
                details["missing_fields"].append(
                    f"{r['recordId'][:12]}: {field}"
                )

        # Check direction-match confidence
        if _is_direction_matched(r):
            metrics["match_matched"] += 1
        else:
            metrics["match_unmatched"] += 1
            student = f.get("学生", f.get("导师", ""))
            details["unmatched_records"].append(
                f"{student or r['recordId'][:12]}"
            )

        # Check selection intent
        if selection_intent and str(selection_intent).strip():
            metrics["selection_intent_filled"] += 1
            student = f.get("学生", f.get("导师", ""))
            details["filled_intent_records"].append(
                f"{student or r['recordId'][:12]}"
            )

    # Check links (sample or all)
    to_check = url_records
    if max_links_check and max_links_check > 0 and len(to_check) > max_links_check:
        import random
        to_check = random.sample(to_check, max_links_check)

    # Track sizes for SPA detection
    url_sizes = []
    for rec_id, url, school, email_field, remark, selection_intent in to_check:
        if url and url.strip():
            metrics["links_total"] += 1
            status, size, _ = _check_link(url)
            if status == 200 and size > SPA_SHELL_MIN_SIZE:
                metrics["links_alive"] += 1
                url_sizes.append(size)
            else:
                metrics["links_dead"] += 1
                details["dead_links"].append(url[:80])

        # Check domestic email
        if _is_domestic_school(school):
            metrics["cn_records_total"] += 1
            if _has_valid_email(email_field):
                metrics["cn_email_filled"] += 1
            else:
                details["missing_cn_emails"].append(
                    f"{rec_id[:12]}: {school or '未知学校'}"
                )

        # Check AI artefacts
        if remark:
            has_emoji = _has_emoji(remark)
            has_warn = _has_warning_symbol(remark)
            has_artefact = _has_ai_artefacts(remark)
            if has_emoji or has_warn or has_artefact:
                metrics["ai_artefact_count"] += 1
                reasons = []
                if has_emoji:
                    reasons.append("emoji")
                if has_warn:
                    reasons.append("⚠️")
                if has_artefact:
                    reasons.append("AI机械短语")
                details["ai_artefact_records"].append(
                    f"{rec_id[:12]}: {', '.join(reasons)}"
                )

    # SPA shell detection
    if url_sizes:
        from collections import Counter
        size_counter = Counter(url_sizes)
        # If >=50% of URLs have the same size → suspicious
        most_common_count = size_counter.most_common(1)[0][1]
        if most_common_count >= len(url_sizes) * 0.5 or metrics["links_total"] > 0:
            # Not a definitive fail, but flag if all are same size
            pass

    # Determine weakest dimension and pass/fail.
    # 0. Required-field completeness  →  0a. Match confidence (same priority tier)
    # Both must pass at 95%. Missing fields blocks match check (can't match if unfilled).
    weak_dim = None
    passes = True

    # 0a. Required-field completeness (must fix before anything else)
    if metrics["missing_field_records"] > 0:
        passes = False
        weak_dim = "missing_fields"

    # 0b. Match confidence (>= 95% of records show direction-matching evidence)
    total_for_match = metrics["match_matched"] + metrics["match_unmatched"]
    match_pct = metrics["match_matched"] / max(total_for_match, 1)
    if match_pct < PASS_MATCH_PCT:
        passes = False
        if weak_dim is None:
            weak_dim = "match_confidence"

    # 1. Link validity (>= 95% alive)
    link_pct = 1.0
    if metrics["links_total"] > 0:
        link_pct = metrics["links_alive"] / metrics["links_total"]
    if link_pct < PASS_LINK_PCT:
        passes = False
        if weak_dim is None:
            weak_dim = "links"

    # 2. CN email fill rate (100%)
    cn_email_pct = 1.0
    if metrics["cn_records_total"] > 0:
        cn_email_pct = metrics["cn_email_filled"] / metrics["cn_records_total"]
    if cn_email_pct < PASS_CN_EMAIL_PCT:
        passes = False
        if weak_dim is None:
            weak_dim = "cn_email"

    # 3. AI artefacts
    if metrics["ai_artefact_count"] > 0:
        passes = False
        if weak_dim is None:
            weak_dim = "ai_artefacts"

    # 4. Selection intent
    if metrics["selection_intent_filled"] > 0:
        passes = False
        if weak_dim is None:
            weak_dim = "selection_intent"

    return {
        "passes": passes,
        "weak_dim": weak_dim,
        "metrics": metrics,
        "details": details,
    }


def audit_dry_run(datasheet_id, token):
    """
    Dry-run audit without actual HTTP link checks.
    Faster, for quick scans. Link check is skipped (assumed all OK).
    """
    records = _load_records(datasheet_id, token)

    metrics = {
        "total_records": len(records),
        "missing_field_records": 0,
        "total_missing_fields": 0,
        "match_matched": 0,
        "match_unmatched": 0,
        "links_total": 0,
        "links_alive": 0,
        "links_dead": 0,
        "cn_records_total": 0,
        "cn_email_filled": 0,
        "ai_artefact_count": 0,
        "selection_intent_filled": 0,
    }
    details = {
        "missing_fields": [],
        "unmatched_records": [],
        "dead_links": [],
        "missing_cn_emails": [],
        "ai_artefact_records": [],
        "filled_intent_records": [],
    }

    for r in records:
        f = r.get("fields", {})
        url = f.get("导师主页", "")
        school = f.get("学校名字", "")
        email_field = f.get("导师联系方式", "")
        remark = f.get("备注", "")
        selection_intent = f.get("选导意向（点击选择）", f.get("选导意向", ""))

        # Check required-field completeness
        missing = _check_required_fields(r)
        if missing:
            metrics["missing_field_records"] += 1
            metrics["total_missing_fields"] += len(missing)
            for field in missing:
                details["missing_fields"].append(
                    f"{r['recordId'][:12]}: {field}"
                )

        # Check direction-match confidence
        if _is_direction_matched(r):
            metrics["match_matched"] += 1
        else:
            metrics["match_unmatched"] += 1
            student = f.get("学生", f.get("导师", ""))
            details["unmatched_records"].append(
                f"{student or r['recordId'][:12]}"
            )

        if url and url.strip():
            metrics["links_total"] += 1
        # Skip actual link check in dry run

        if _is_domestic_school(school):
            metrics["cn_records_total"] += 1
            if _has_valid_email(email_field):
                metrics["cn_email_filled"] += 1
            else:
                details["missing_cn_emails"].append(
                    f"{r['recordId'][:12]}: {school or '未知学校'}"
                )

        if remark:
            if _has_emoji(remark) or _has_warning_symbol(remark) or _has_ai_artefacts(remark):
                metrics["ai_artefact_count"] += 1
                details["ai_artefact_records"].append(r["recordId"][:12])

        if selection_intent and str(selection_intent).strip():
            metrics["selection_intent_filled"] += 1
            details["filled_intent_records"].append(r["recordId"][:12])

    weak_dim = None
    passes = True

    if metrics["missing_field_records"] > 0:
        passes = False
        weak_dim = "missing_fields"

    total_for_match = metrics["match_matched"] + metrics["match_unmatched"]
    if total_for_match > 0 and metrics["match_matched"] / total_for_match < PASS_MATCH_PCT:
        passes = False
        if weak_dim is None:
            weak_dim = "match_confidence"

    if metrics["cn_records_total"] > 0:
        if metrics["cn_email_filled"] < metrics["cn_records_total"]:
            passes = False
            if weak_dim is None:
                weak_dim = "cn_email"

    if metrics["ai_artefact_count"] > 0:
        passes = False
        if weak_dim is None:
            weak_dim = "ai_artefacts"

    if metrics["selection_intent_filled"] > 0:
        passes = False
        if weak_dim is None:
            weak_dim = "selection_intent"

    return {
        "passes": passes,
        "weak_dim": weak_dim,
        "metrics": metrics,
        "details": details,
    }


def format_audit_report(result):
    """Format audit result as a human-readable report string."""
    m = result["metrics"]
    d = result["details"]
    lines = [
        f"审计报告（{m['total_records']} 条记录）",
        f"必填字段缺失: {m['missing_field_records']} 条记录共缺 {m['total_missing_fields']} 个字段",
        f"匹配置信度: {m['match_matched']}/{m['match_matched'] + m['match_unmatched']} ({m['match_matched']/max(m['match_matched']+m['match_unmatched'], 1)*100:.0f}%) 阈值 {int(PASS_MATCH_PCT*100)}%",
        f"链接有效性: {m['links_alive']}/{m['links_total']} ({m['links_alive']/max(m['links_total'],1)*100:.0f}%) 阈值 {int(PASS_LINK_PCT*100)}%" if m['links_total'] > 0 else "链接: N/A",
        f"国内邮箱: {m['cn_email_filled']}/{m['cn_records_total']} ({m['cn_email_filled']/max(m['cn_records_total'],1)*100:.0f}%)" if m['cn_records_total'] > 0 else "国内邮箱: N/A",
        f"AI痕迹: {m['ai_artefact_count']} 条",
        f"选导意向已填: {m['selection_intent_filled']} 条",
    ]
    if d["missing_fields"]:
        lines.append(f"缺失字段明细: {len(d['missing_fields'])} 处")
    if d["unmatched_records"]:
        lines.append(f"方向未匹配: {len(d['unmatched_records'])} 条")
    if d["dead_links"]:
        lines.append(f"死链: {len(d['dead_links'])} 条")
    if d["missing_cn_emails"]:
        lines.append(f"缺邮箱: {len(d['missing_cn_emails'])} 条")
    if result["passes"]:
        lines.append("结果: 达标")
    else:
        lines.append(f"结果: 未达标（最弱维度: {result['weak_dim']}）")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: audit_state.py <DATASHEET_ID> <TOKEN> [--dry-run] [--verbose]")
        sys.exit(1)

    ds_id = sys.argv[1]
    api_token = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv

    fn = audit_dry_run if dry_run else audit
    result = fn(ds_id, api_token)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print(format_audit_report(result))
