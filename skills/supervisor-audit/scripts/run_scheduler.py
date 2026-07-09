#!/usr/bin/env python3
"""Entry point for the WorkBuddy automation: pick the next batch of tasks.

Usage:
    python3 run_scheduler.py

Output (JSON):
    {
        "working_hours": true,
        "stale_released": ["recXXX", ...],
        "claimed": ["recXXX", ...],
        "remaining_pending": 2,
        "status": "待处理: 2 | 处理中: 1 | ☀️ 工作时间"
    }
"""
import json

import state_machine as sm


def main():
    if not sm.is_working_hours():
        print(json.dumps({
            "working_hours": False,
            "stale_released": [],
            "claimed": [],
            "remaining_pending": 0,
            "status": sm.format_batch_status(),
        }, ensure_ascii=False, indent=2))
        return

    # Recover any tasks left stuck by crashed or old-state automations.
    stale = sm.check_stale_locks()

    # Claim the next batch.
    pending = sm.get_pending_tasks(limit=sm.BATCH_SIZE)
    claimed_ids = [r["record_id"] for r in pending]
    claim_result = sm.claim_tasks(claimed_ids, node_id="workbuddy-auto")

    # Report which ones were actually claimed.
    successfully_claimed = [rid for rid, ok in claim_result.items() if ok]

    print(json.dumps({
        "working_hours": True,
        "stale_released": stale,
        "claimed": successfully_claimed,
        "remaining_pending": sm.count_pending_tasks(),
        "status": sm.format_batch_status(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
