#!/usr/bin/env python3
"""Dump all Feishu Bitable records with truncated field values for quick debugging."""

import feishu_client as client


def main():
    records = client.get_records(page_size=500)
    for item in records:
        print(f"\n=== Record: {item['record_id']} ===")
        fields = item.get("fields", {})
        for k, v in fields.items():
            val = str(v)[:200] if v is not None else "[EMPTY]"
            print(f"  {k}: {val}")


if __name__ == "__main__":
    main()
