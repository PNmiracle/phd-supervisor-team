#!/usr/bin/env python3
"""Query Feishu Bitable for pending supervisor tasks."""
import json

import feishu_config as cfg
import feishu_client as client


def main():
    records = client.get_records(page_size=500)

    pending = []
    for r in records:
        f = r.get("fields", {})
        if f.get(cfg.FIELD_STAGE) != cfg.STAGE_PENDING or not f.get(cfg.FIELD_PROMPT):
            continue
        pending.append({
            "record_id": r["record_id"],
            "学生": f.get(cfg.FIELD_STUDENT, ""),
            "提示词": f.get(cfg.FIELD_PROMPT, ""),
            "附件": f.get(cfg.FIELD_ATTACHMENTS, ""),
            "阶段": f.get(cfg.FIELD_STAGE, ""),
            "优先级": f.get(cfg.FIELD_PRIORITY, ""),
        })

    print(json.dumps({
        "pending": pending,
        "total_pending": len(pending),
        "total_all": len(records),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
