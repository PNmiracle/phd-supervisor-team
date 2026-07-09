#!/usr/bin/env python3
"""One-time setup: ensure required scheduler fields exist in Feishu Bitable."""

import feishu_client as client


def main():
    added = client.ensure_scheduler_fields()
    if added:
        print(f"已添加字段: {', '.join(added)}")
    else:
        print("所有字段已存在，无需添加。")


if __name__ == "__main__":
    main()
