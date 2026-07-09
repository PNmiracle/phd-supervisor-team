#!/usr/bin/env python3
"""Per-student chat runner for WorkBuddy space parallel processing.

Usage:
    python3 chat_runner.py "张竣菘"

Output (JSON):
    {
        "ok": true,
        "message": "领取成功",
        "student": "张竣菘",
        "record_id": "recXXX",
        "stage": "AI 处理中",
        "prompt": "...",
        "vika_url": "https://vika.cn/share/...",
        "attachments": [...],
        "priority": "P2-低优",
        "round": "初选",
        "feedback": "...",
        "locked_by": "workbuddy-chat"
    }

If the task is already locked by another chat, ok=false and locked_by
shows the current owner.
"""
import json
import re
import sys

import state_machine as sm
import feishu_config as cfg


def _extract_vika_url(text):
    """Extract the first Vika share URL from prompt text."""
    if not text:
        return ""
    match = re.search(r"https://vika\.cn/share/\S+", text)
    return match.group(0) if match else ""


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "message": "Usage: chat_runner.py <学生名>"}, ensure_ascii=False))
        sys.exit(1)

    student_name = sys.argv[1].strip()
    record = sm.find_task_by_student(student_name)

    if record is None:
        print(json.dumps({
            "ok": False,
            "message": f"未找到学生「{student_name}」的任务，请确认 Bitable 中 学生 字段",
        }, ensure_ascii=False))
        sys.exit(0)

    rid = record["record_id"]
    details = sm.get_task_details(rid)

    # If already completed or in review, just report.
    stage = details.get("阶段", "")
    if stage == cfg.STAGE_DONE:
        print(json.dumps({
            "ok": False,
            "message": "该学生任务已完成",
            "student": student_name,
            "record_id": rid,
            "stage": stage,
        }, ensure_ascii=False))
        sys.exit(0)

    if stage == cfg.STAGE_REVIEW:
        print(json.dumps({
            "ok": False,
            "message": "该学生任务处于人工待审批，请先处理",
            "student": student_name,
            "record_id": rid,
            "stage": stage,
            "failure_reason": details.get("失败原因", ""),
        }, ensure_ascii=False))
        sys.exit(0)

    # Try to claim. Use a node id derived from student name so re-entry from the
    # same chat is allowed.
    node_id = f"chat-{student_name}"
    success, claimed_record, message = sm.claim_task_by_id(rid, node_id=node_id)
    details = sm.get_task_details(rid)

    result = {
        "ok": success,
        "message": message,
        "student": student_name,
        "record_id": rid,
        "stage": details.get("阶段", ""),
        "priority": details.get("优先级", ""),
        "round": details.get("第几轮选导", ""),
        "prompt": details.get("提示词", ""),
        "vika_url": _extract_vika_url(details.get("提示词", "")),
        "attachments": details.get("附件", []),
        "feedback": details.get("AI 反馈", ""),
        "locked_by": details.get("处理节点", ""),
        "error_count": details.get("错误次数", 0),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
