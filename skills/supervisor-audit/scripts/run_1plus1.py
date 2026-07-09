#!/usr/bin/env python3
"""1+1 workflow dispatcher for per-student chat processing.

Steps:
    claim    — claim task and return context (prompt, vika_url, attachments)
    audit    — run audit_state.py on the student's Vika table
    done     — complete or send-to-review based on audit
    fail     — record a processing failure (auto-retry or escalate)

Usage:
    python3 run_1plus1.py claim 张竣菘
    python3 run_1plus1.py audit 张竣菘 [--vika-datasheet dstXXX] [--vika-token uskXXX]
    python3 run_1plus1.py done 张竣菘 --passed [--reason "..."] [--feedback "..."]
    python3 run_1plus1.py fail 张竣菘 --reason "API timeout"
"""
import argparse
import json
import os
import sys

import feishu_client as client
import feishu_config as cfg
import state_machine as sm


def _find_student(name):
    """Find student by name, exit with JSON error if not found."""
    record = sm.find_task_by_student(name)
    if record is None:
        print(json.dumps({"ok": False, "message": f"未找到学生「{name}」"}, ensure_ascii=False))
        sys.exit(0)
    return record


def _vika_url_from_prompt(prompt):
    """Extract Vika datasheet ID from prompt text (supports both URL formats)."""
    import re
    m = re.search(r"https://vika\.cn/share/shr\S+", prompt or "")
    if m:
        return m.group(0)
    m = re.search(r"dst\w{13,16}", prompt or "")
    if m:
        return m.group(0)
    return ""


def cmd_claim(args):
    """Claim a student task and return context."""
    import chat_runner as cr
    record = _find_student(args.student)
    rid = record["record_id"]

    # Use chat_runner's claim logic
    node_id = f"chat-{args.student}"
    success, _, message = sm.claim_task_by_id(rid, node_id=node_id)
    details = sm.get_task_details(rid)

    result = {
        "ok": success,
        "message": message,
        "student": args.student,
        "record_id": rid,
        "stage": details.get("阶段", ""),
        "priority": details.get("优先级", ""),
        "round": details.get("第几轮选导", ""),
        "prompt": details.get("提示词", ""),
        "vika_url": _vika_url_from_prompt(details.get("提示词", "")),
        "attachments": details.get("附件", []),
        "feedback": details.get("AI 反馈", ""),
        "locked_by": details.get("处理节点", ""),
        "error_count": details.get("错误次数", 0),
    }

    if success:
        sm.build_append_feedback(
            details.get("AI 反馈", ""),
            [f"[{sm._beijing_now_str()}] 1+1 工作流启动，领取任务"],
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_audit(args):
    """Run audit_state.py on the student's Vika table."""
    import audit_state as auditor

    record = _find_student(args.student)
    rid = record["record_id"]
    details = sm.get_task_details(rid)

    # Resolve Vika credentials
    ds_id = args.vika_datasheet
    token = args.vika_token or cfg.VIKA_TOKEN or os.environ.get("VIKA_TOKEN")

    if not ds_id:
        # Try to extract from prompt
        url = _vika_url_from_prompt(details.get("提示词", ""))
        if url and "dst" in url:
            import re
            m = re.search(r"dst\w+", url)
            if m:
                ds_id = m.group(0)

    if not ds_id:
        print(json.dumps({
            "ok": False,
            "message": "无法解析 Vika datasheet ID，请通过 --vika-datasheet 参数提供",
        }, ensure_ascii=False))
        sys.exit(1)

    if not token:
        print(json.dumps({
            "ok": False,
            "message": "VIKA_TOKEN 未设置，请设置环境变量或通过 --vika-token 参数提供",
        }, ensure_ascii=False))
        sys.exit(1)

    # Run audit
    result = auditor.audit(ds_id, token)
    report = auditor.format_audit_report(result)

    # Append feedback to Feishu Bitable
    matched = result["metrics"].get("match_matched", 0)
    unmatched = result["metrics"].get("match_unmatched", 0)
    match_pct = matched / max(matched + unmatched, 1) * 100
    links_alive = result["metrics"].get("links_alive", 0)
    links_total = result["metrics"].get("links_total", 0)
    link_pct = links_alive / max(links_total, 1) * 100
    feedback_lines = [
        f"[{sm._beijing_now_str()}] 自查结果: {'达标' if result['passes'] else '未达标'}（最弱维度: {result.get('weak_dim') or '无'}）",
        f"[{sm._beijing_now_str()}] 链接准确率: {link_pct:.0f}% (≥95% → 通过) | 匹配置信度: {match_pct:.0f}% (≥95% → 通过)",
    ]
    if not result["passes"] and result.get("details"):
        if result["details"].get("missing_fields"):
            feedback_lines.append(
                f"[{sm._beijing_now_str()}] 必填字段缺失 {len(result['details']['missing_fields'])} 处，需返工给选导助手补充: {', '.join(result['details']['missing_fields'][:10])}"
            )
        if result["details"].get("unmatched_records"):
            feedback_lines.append(
                f"[{sm._beijing_now_str()}] 方向未匹配 {len(result['details']['unmatched_records'])} 条，需返工: {', '.join(result['details']['unmatched_records'][:10])}"
            )
        if result["details"].get("dead_links"):
            feedback_lines.append(
                f"[{sm._beijing_now_str()}] 死链 {len(result['details']['dead_links'])} 条"
            )

    new_feedback = sm.build_append_feedback(details.get("AI 反馈", ""), feedback_lines)
    client.update_record(rid, {cfg.FIELD_FEEDBACK: new_feedback})
    updated = sm.get_task_details(rid)

    output = {
        "ok": True,
        "student": args.student,
        "record_id": rid,
        "passes": result["passes"],
        "weak_dim": result["weak_dim"],
        "metrics": result["metrics"],
        "details": result["details"],
        "report": report,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_done(args):
    """Complete a student task."""
    record = _find_student(args.student)
    rid = record["record_id"]
    details = sm.get_task_details(rid)

    feedback_lines = []
    if args.feedback:
        feedback_lines.append(f"[{sm._beijing_now_str()}] {args.feedback}")

    if args.passed:
        feedback_lines.append(f"[{sm._beijing_now_str()}] 1+1 工作流完成，全部检查通过")
    else:
        reason = args.reason or "audit 未通过"
        feedback_lines.append(f"[{sm._beijing_now_str()}] 1+1 工作流完成，未通过: {reason}")

    sm.complete_task(rid, passed=args.passed, failure_reason=args.reason, feedback_lines=feedback_lines)
    updated = sm.get_task_details(rid)

    print(json.dumps({
        "ok": True,
        "student": args.student,
        "record_id": rid,
        "stage": updated.get("阶段"),
        "confidence": updated.get("置信度"),
        "failure_reason": updated.get("失败原因"),
    }, ensure_ascii=False, indent=2))


def cmd_fail(args):
    """Record a processing failure for a student task."""
    record = _find_student(args.student)
    rid = record["record_id"]

    reason = args.reason or "处理异常"
    sm.fail_task(rid, reason, retry=True, feedback_lines=[
        f"[{sm._beijing_now_str()}] 处理异常: {reason}",
    ])
    updated = sm.get_task_details(rid)

    print(json.dumps({
        "ok": True,
        "student": args.student,
        "record_id": rid,
        "stage": updated.get("阶段"),
        "error_count": updated.get("错误次数"),
        "failure_reason": updated.get("失败原因"),
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="1+1 workflow dispatcher")
    parser.add_argument("step", choices=["claim", "audit", "done", "fail"])
    parser.add_argument("student", help="学生姓名（与 Bitable 学生字段匹配）")
    parser.add_argument("--vika-datasheet", help="Vika datasheet ID (dstXXX)")
    parser.add_argument("--vika-token", help="Vika API token")
    parser.add_argument("--passed", type=lambda x: x.lower() in ("true", "1", "yes"), default=None, help="audit 是否通过")
    parser.add_argument("--reason", help="失败原因（passed=false 或 fail 时使用）")
    parser.add_argument("--feedback", help="追加到 AI 反馈的说明")

    args = parser.parse_args()

    dispatch = {
        "claim": cmd_claim,
        "audit": cmd_audit,
        "done": cmd_done,
        "fail": cmd_fail,
    }
    dispatch[args.step](args)


if __name__ == "__main__":
    main()
