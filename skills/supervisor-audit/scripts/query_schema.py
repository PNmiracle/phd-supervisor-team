#!/usr/bin/env python3
"""Print Feishu Bitable schema and all records for debugging."""
import json

import feishu_client as client


def main():
    # 1. Fields schema
    fields = client.get_fields()
    print("Fields schema:")
    for f in fields:
        print(f"  {f['field_name']} (id={f['field_id']}, type={f.get('type')}, ui={f.get('ui_type')})")

    # 2. All records
    records = client.get_records(page_size=500)
    print(f"\nTotal records: {len(records)}")
    for r in records:
        print(f"\nRecord ID: {r['record_id']}")
        for k, v in r.get("fields", {}).items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
