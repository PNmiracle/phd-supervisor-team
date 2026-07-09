#!/usr/bin/env python3
"""Simplified Bitable-based task scheduler for the supervisor automation engine.

Design principles:
- Single source of truth: Feishu Bitable (no local pass_log.json).
- Batch over single-task: claim and complete tasks in batches.
- One-shot processing + audit: no 8-round deep-optimization loop.
- Confidence-based routing: audit passes -> 已完成; fails -> 人工待审批 (or retry).
- Stale-lock recovery: tasks stuck in AI处理中 for too long are reset automatically.
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta

import feishu_config as cfg
import feishu_client as client


# ---- Configuration ----
TZ = timezone(timedelta(hours=8))  # Beijing time
WORK_START_HOUR = 6
WORK_END_HOUR = 23
LOCK_TTL_SECONDS = 30 * 60  # 30 minutes
MAX_ERRORS = 3  # move to review/paused after this many consecutive failures
BATCH_SIZE = 5  # process at most this many tasks per automation run


# ---- Time helpers ----
def _now_ts():
    return int(time.time())


def _now_beijing():
    return datetime.now(TZ)


def _now_ms():
    """Current timestamp in milliseconds (Feishu DateTime field format)."""
    return int(_now_ts() * 1000)


def _beijing_now_str():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def is_working_hours():
    """Return True if current Beijing time is 06:00-23:00."""
    return WORK_START_HOUR <= _now_beijing().hour < WORK_END_HOUR


def _parse_timestamp_ms(value):
    """Parse Feishu DateTime field (millisecond timestamp) to seconds."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value / 1000)
    if isinstance(value, str):
        try:
            return int(value) // 1000
        except ValueError:
            return 0
    return 0


def _priority_score(record):
    priority = (record.get("fields", {}).get(cfg.FIELD_PRIORITY) or "").strip()
    return cfg.PRIORITY_ORDER.get(priority, 3)


def _start_time_numeric(record):
    st = record.get("fields", {}).get(cfg.FIELD_START_TIME, 0)
    if isinstance(st, (int, float)):
        return int(st)
    if isinstance(st, str):
        try:
            return int(st)
        except ValueError:
            return 9999999999999
    return 9999999999999


# ---- Field access helpers ----
def _get_field(record, field_name, default=None):
    return record.get("fields", {}).get(field_name, default)


def _stage(record):
    return (_get_field(record, cfg.FIELD_STAGE) or "").strip()


def _prompt(record):
    return (_get_field(record, cfg.FIELD_PROMPT) or "").strip()


# ---- Core scheduler ----
def get_pending_tasks(limit=None):
    """Fetch pending tasks sorted by priority then start time.

    Args:
        limit: Optional max number of records to return.

    Returns:
        List of Feishu record dicts with 阶段 == 任务发布未进行 and 提示词 non-empty.
    """
    records = [
        r for r in client.get_records()
        if _stage(r) == cfg.STAGE_PENDING and _prompt(r)
    ]
    records.sort(key=lambda r: (_priority_score(r), _start_time_numeric(r)))
    if limit:
        records = records[:limit]
    return records


def get_processing_tasks():
    """Fetch all tasks currently in AI处理中."""
    return [r for r in client.get_records() if _stage(r) == cfg.STAGE_PROCESSING]


def claim_tasks(record_ids, node_id="workbuddy"):
    """Claim a batch of tasks by setting stage to AI处理中 and recording lock metadata.

    Args:
        record_ids: List of Feishu record IDs.
        node_id: Identifier for the processing node/session.

    Returns:
        Dict mapping record_id -> True/False for success.
    """
    if not record_ids:
        return {}
    now_ms = _now_ms()
    updates = []
    for rid in record_ids:
        updates.append({
            "record_id": rid,
            "fields": {
                cfg.FIELD_STAGE: cfg.STAGE_PROCESSING,
                cfg.FIELD_LOCK_TIME: now_ms,
                cfg.FIELD_NODE: node_id,
            },
        })

    result = client.batch_update_records(updates)
    updated_ids = {r["record_id"] for r in result.get("data", {}).get("records", [])}
    return {rid: rid in updated_ids for rid in record_ids}


def complete_task(record_id, passed, failure_reason=None, feedback_lines=None):
    """Mark a single task as completed or needing manual review.

    Args:
        record_id: Feishu record ID.
        passed: True if audit passed -> 已完成; False -> 人工待审批.
        failure_reason: Optional short reason for failure (used when passed=False).
        feedback_lines: Optional list of lines to append to AI 反馈.

    Returns:
        API response dict.
    """
    record = client.api("GET", f"/records/{record_id}").get("data", {}).get("record", {})
    existing_feedback = _get_field(record, cfg.FIELD_FEEDBACK, "")

    fields = {
        cfg.FIELD_STAGE: cfg.STAGE_DONE if passed else cfg.STAGE_REVIEW,
        cfg.FIELD_CONFIDENCE: "通过" if passed else "未通过",
        cfg.FIELD_LOCK_TIME: None,
        cfg.FIELD_NODE: "",
    }
    if passed:
        fields[cfg.FIELD_FAILURE_REASON] = ""
        fields[cfg.FIELD_END_TIME] = int(_now_ts() * 1000)
    else:
        fields[cfg.FIELD_FAILURE_REASON] = failure_reason or ""

    if feedback_lines:
        fields[cfg.FIELD_FEEDBACK] = build_append_feedback(existing_feedback, feedback_lines)

    return client.update_record(record_id, fields)


def fail_task(record_id, failure_reason, retry=True, feedback_lines=None):
    """Handle a processing failure.

    If retry=True and error count < MAX_ERRORS, increment error count and
    return to pending. Otherwise move to review/paused.

    Args:
        record_id: Feishu record ID.
        failure_reason: Reason for failure.
        retry: Whether to allow retry.
        feedback_lines: Optional feedback lines to append.

    Returns:
        API response dict.
    """
    record = client.api("GET", f"/records/{record_id}").get("data", {}).get("record", {})
    error_count = _get_field(record, cfg.FIELD_ERROR_COUNT, 0) or 0
    existing_feedback = _get_field(record, cfg.FIELD_FEEDBACK, "")

    if retry and error_count < MAX_ERRORS:
        new_stage = cfg.STAGE_PENDING
        new_error_count = error_count + 1
    else:
        new_stage = cfg.STAGE_REVIEW
        new_error_count = error_count

    fields = {
        cfg.FIELD_STAGE: new_stage,
        cfg.FIELD_CONFIDENCE: "未通过",
        cfg.FIELD_FAILURE_REASON: failure_reason or "",
        cfg.FIELD_ERROR_COUNT: new_error_count,
        cfg.FIELD_LOCK_TIME: None,
        cfg.FIELD_NODE: "",
    }

    if feedback_lines:
        fields[cfg.FIELD_FEEDBACK] = build_append_feedback(existing_feedback, feedback_lines)

    return client.update_record(record_id, fields)


def release_stale_locks(ttl_seconds=LOCK_TTL_SECONDS):
    """Reset tasks stuck in AI处理中 for longer than ttl_seconds back to pending.

    Returns:
        List of released record IDs.
    """
    cutoff = _now_ts() - ttl_seconds
    stuck = []
    for r in get_processing_tasks():
        lock_time = _get_field(r, cfg.FIELD_LOCK_TIME)
        lock_ts = _parse_timestamp_ms(lock_time)
        # Missing lock time on a processing task means pre-migration stale state.
        if lock_ts == 0 or lock_ts < cutoff:
            stuck.append(r["record_id"])

    if not stuck:
        return []

    updates = []
    for rid in stuck:
        updates.append({
            "record_id": rid,
            "fields": {
                cfg.FIELD_STAGE: cfg.STAGE_PENDING,
                cfg.FIELD_LOCK_TIME: None,
                cfg.FIELD_NODE: "",
            },
        })
    client.batch_update_records(updates)
    return stuck


# ---- Feedback helper ----
def build_append_feedback(existing_feedback, new_lines):
    """Append new log lines to existing AI 反馈, never overwrite."""
    existing = (existing_feedback or "").strip()
    lines = existing.split("\n") if existing else []
    lines.extend(new_lines)

    if len(lines) > 30:
        header = lines[:2]
        tail = lines[-28:]
        overflow_count = len(lines) - 30
        lines = header + [f"...（中间省略 {overflow_count} 行日志）..."] + tail

    return "\n".join(lines)


# ---- Status formatting ----
def count_pending_tasks():
    return len(get_pending_tasks())


def count_processing_tasks():
    return len(get_processing_tasks())


def format_batch_status():
    pending = count_pending_tasks()
    processing = count_processing_tasks()
    working = "☀️ 工作时间" if is_working_hours() else "🌙 夜间模式"
    return f"待处理: {pending} | 处理中: {processing} | {working}"


# ---- Per-student chat helpers ----
def _normalize(name):
    """Normalize student name for matching: remove extra spaces and newlines."""
    if not name:
        return ""
    return " ".join(name.split())


def find_task_by_student(student_name):
    """Find a task whose 学生 field contains the given name (case-insensitive).

    Returns:
        Feishu record dict or None.
    """
    needle = _normalize(student_name).lower()
    if not needle:
        return None
    for r in client.get_records():
        student = _normalize(_get_field(r, cfg.FIELD_STUDENT))
        if needle in student.lower():
            return r
    return None


def get_task_details(record_id):
    """Return readable task details for a chat/agent."""
    record = client.api("GET", f"/records/{record_id}").get("data", {}).get("record", {})
    f = record.get("fields", {})
    return {
        "record_id": record_id,
        "学生": f.get(cfg.FIELD_STUDENT, ""),
        "阶段": f.get(cfg.FIELD_STAGE, ""),
        "优先级": f.get(cfg.FIELD_PRIORITY, ""),
        "第几轮选导": f.get(cfg.FIELD_ROUND, ""),
        "提示词": f.get(cfg.FIELD_PROMPT, ""),
        "附件": f.get(cfg.FIELD_ATTACHMENTS, []),
        "AI 反馈": f.get(cfg.FIELD_FEEDBACK, ""),
        "锁定时间": f.get(cfg.FIELD_LOCK_TIME),
        "处理节点": f.get(cfg.FIELD_NODE, ""),
        "错误次数": f.get(cfg.FIELD_ERROR_COUNT, 0),
        "失败原因": f.get(cfg.FIELD_FAILURE_REASON, ""),
        "置信度": f.get(cfg.FIELD_CONFIDENCE, ""),
    }


def claim_task_by_id(record_id, node_id="workbuddy-chat"):
    """Claim a specific task for a chat/session.

    Returns:
        (success: bool, record: dict or None, message: str)
    """
    record = client.api("GET", f"/records/{record_id}").get("data", {}).get("record", {})
    stage = _stage(record)
    current_node = _get_field(record, cfg.FIELD_NODE, "")

    if stage == cfg.STAGE_DONE:
        return False, record, "任务已完成"
    if stage == cfg.STAGE_REVIEW:
        return False, record, "任务处于人工待审批，请先处理"
    if stage == cfg.STAGE_PROCESSING:
        # Already processing. If it's us, allow continuing; otherwise reject.
        if current_node and current_node != node_id:
            return False, record, f"任务正被 {current_node} 处理中"
        # Same node or empty node: re-claim to refresh lock time.

    result = claim_tasks([record_id], node_id=node_id)
    if result.get(record_id):
        refreshed = client.api("GET", f"/records/{record_id}").get("data", {}).get("record", {})
        return True, refreshed, "领取成功"
    return False, record, "领取失败"


# ---- Backward-compatible wrappers ----
def find_next_task(feishu_records=None):
    """Return the highest-priority pending task, or (None, None).

    Kept for compatibility with older automation prompts.
    """
    pending = get_pending_tasks(limit=1)
    if pending:
        return pending[0], "new"
    return None, None


def acquire_lock(record_id):
    """Acquire lock for a task. Compatibility wrapper around claim_tasks.

    Returns:
        (success, message, rounds_done, weak_dim) where rounds_done is always 0.
    """
    result = claim_tasks([record_id])
    if result.get(record_id):
        return True, "接锁成功", 0, None
    return False, "接锁失败", 0, None


def release_lock(record_id, rounds_done=None, weak_dim=None, passes=False):
    """Release lock after processing. Compatibility wrapper.

    Args:
        record_id: Feishu record ID.
        rounds_done: Ignored (no longer tracked).
        weak_dim: Used as failure_reason when passes=False.
        passes: True -> 已完成; False -> 人工待审批.
    """
    return complete_task(record_id, passes, failure_reason=weak_dim)


def check_stale_locks(feishu_records=None):
    """Reset stuck locks and return list of released record IDs."""
    return release_stale_locks()


def unstale_lock(record_id):
    """Force reset a single stuck task back to pending."""
    client.update_record(record_id, {
        cfg.FIELD_STAGE: cfg.STAGE_PENDING,
        cfg.FIELD_LOCK_TIME: None,
        cfg.FIELD_NODE: "",
    })
    return True


def get_rounds_done(record_id):
    """Always returns 0; kept for compatibility."""
    return 0


# ---- Exports ----
__all__ = [
    # New API
    "get_pending_tasks", "get_processing_tasks", "claim_tasks",
    "complete_task", "fail_task", "release_stale_locks",
    "build_append_feedback", "is_working_hours",
    "count_pending_tasks", "count_processing_tasks", "format_batch_status",
    # Per-student chat API
    "find_task_by_student", "get_task_details", "claim_task_by_id",
    # Compatibility wrappers
    "find_next_task", "acquire_lock", "release_lock",
    "check_stale_locks", "unstale_lock", "get_rounds_done",
    # Config constants
    "STAGE_PENDING", "STAGE_PROCESSING", "STAGE_PAUSED",
    "STAGE_DONE", "STAGE_REVIEW", "BATCH_SIZE", "MAX_ERRORS",
]
