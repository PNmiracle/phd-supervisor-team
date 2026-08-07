#!/usr/bin/env python3
"""
链接批量审计脚本 (link-audit.py)
================================
对 Vika 选导表中的导师链接做全量健康检查，区分真 404 / SPA 壳 / WAF 拦截 / 疑似正常，
并对疑似问题链接输出 WebFetch 穿透验证清单。

用途：用户反馈"链接打不开/404"时，先全量审计再针对性修复（配合 SKILL.md「链接修复工作流」步骤 0）。

用法：
    python3 link-audit.py <DATASHEET_ID> [VIKA_TOKEN]

环境变量 VIKA_TOKEN 已设置时可省略第二个参数。

输出：
    1. 每个 URL 的状态码 + 字节数 + title（每 URL 独立临时文件，避免并发污染）
    2. 按学校分组的汇总表
    3. 需要 WebFetch 穿透验证的 URL 清单（存疑项）
    4. 修复建议（旧 404 → 需搜索的替代）

关键认知（2026-08-04 沉淀）：
- 并发 curl 共享临时文件会污染 title，但状态码可靠 → 本脚本每个 URL 用独立文件
- CityU scholars 403 ≠ 有效：可能是 WAF 壳，也可能是离任教授页面已删除（穿透 WAF 可见
  "The page does not exist"）→ 存疑项必须 WebFetch 穿透验证
- 离任导师检测：WebFetch 穿透 + CityU 学术目录（Visiting/Adjunct 标注）+ 系级教职员列表
"""

import subprocess
import sys
import re
import json
import os
import tempfile
import time
from collections import defaultdict

BASE = "https://api.vika.cn/fusion/v1"
URL_FIELDS = ["导师主页", "博士申请信息", "其他导师信息"]


def vika_get(datasheet_id, token, path):
    """调用 Vika Fusion API GET"""
    import urllib.request
    req = urllib.request.Request(
        f"{BASE}/datasheets/{datasheet_id}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def extract_url(val):
    """Vika URL 字段可能返回 dict {title, text} 或字符串"""
    if not val:
        return ""
    if isinstance(val, dict):
        return val.get("text", val.get("title", ""))
    return str(val)


def curl_check(url, tmp_dir, idx):
    """用独立临时文件检查 URL，返回 (code, size, title)"""
    tmp = os.path.join(tmp_dir, f"chk_{idx}.html")
    try:
        result = subprocess.run(
            [
                "curl", "-sL", "-m", "25", "-o", tmp,
                "-w", "%{http_code}|%{size_download}",
                "-A",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=35,
        )
        parts = result.stdout.strip().split("|")
        code = parts[0] if parts else "ERR"
        size = parts[1] if len(parts) > 1 else "0"
        title = ""
        try:
            with open(tmp, "rb") as fh:
                content = fh.read()
            m = re.search(rb"<title[^>]*>(.*?)</title>", content[:80000], re.I | re.S)
            if m:
                title = m.group(1).decode("utf-8", errors="ignore").strip()[:80]
        except Exception:
            pass
        return code, size, title
    except Exception as e:
        return "ERR", "0", str(e)[:80]


def classify(code, size, title):
    """对单条 URL 分类"""
    if code == "404":
        return "真404"
    if code == "403":
        return "403-需穿透验证"  # 可能是 WAF，也可能是离任教授失效页
    if code == "200" and int(size or 0) < 2000 and not title:
        return "疑似WAF壳/空页"
    if code == "200" and not title:
        return "200-无title需验证"
    if code == "200":
        return "OK"
    return f"{code}-异常"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    datasheet_id = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VIKA_TOKEN", "")
    if not token:
        print("错误：需要 VIKA_TOKEN（环境变量或第二个参数）")
        sys.exit(1)

    # 1. 拉取全部记录
    all_records = []
    page = 1
    while True:
        r = vika_get(datasheet_id, token, f"/records?maxRecords=500&pageNum={page}&fieldKey=name")
        records = r.get("data", {}).get("records", [])
        all_records.extend(records)
        total = r.get("data", {}).get("total", 0)
        if len(records) < 500 or page * 500 >= total:
            break
        page += 1
    print(f"记录总数: {len(all_records)}")

    # 2. 提取去重 URL
    url_meta = {}  # url -> list[(mentor, field)]
    for rec in all_records:
        fields = rec.get("fields", {})
        mentor = fields.get("导师", "?")
        for fname in URL_FIELDS:
            u = extract_url(fields.get(fname))
            if u:
                url_meta.setdefault(u, []).append((mentor, fname))

    print(f"去重 URL 总数: {len(url_meta)}\n")

    # 3. 逐个 curl 检查（独立临时文件）
    tmp_dir = tempfile.mkdtemp(prefix="link_audit_")
    results = {}
    for idx, url in enumerate(url_meta):
        code, size, title = curl_check(url, tmp_dir, idx)
        results[url] = {"code": code, "size": size, "title": title}
        cls = classify(code, size, title)
        print(f"[{cls}] [{code}] {size:>7}B | {url[:95]}")
        if cls != "OK" and title:
            print(f"              title: {title}")
        time.sleep(0.1)

    # 4. 按状态汇总
    print("\n=== 汇总 ===")
    grouped = defaultdict(list)
    for url, res in results.items():
        grouped[classify(res["code"], res["size"], res["title"])].append(url)
    for cls, urls in sorted(grouped.items()):
        print(f"{cls}: {len(urls)} 条")
        for u in urls:
            print(f"    {u[:100]}")

    # 5. 输出待穿透验证清单（403 / 无 title / WAF 壳）
    print("\n=== 需 WebFetch 穿透验证的 URL（疑似问题项）===")
    suspect = 0
    for url, res in results.items():
        cls = classify(res["code"], res["size"], res["title"])
        if cls in ("403-需穿透验证", "疑似WAF壳/空页", "200-无title需验证", "ERR-异常"):
            suspect += 1
            owners = url_meta[url]
            print(f"  [{cls}] {url}")
            print(f"      涉及: {', '.join(f'{m}/{f}' for m, f in owners)}")
    print(f"\n疑似问题 {suspect} 条。对以上每条用 WebFetch 打开确认："
          f"能显示导师姓名/职称/院系 → 有效保留；'The page does not exist'/404 → 失效需修复或删除"
          f"（离任导师删除记录，见 SKILL.md CityU 章节）")

    # 保存结果供后续修复
    out = "/tmp/link_audit_results.json"
    with open(out, "w") as fh:
        json.dump({"results": results, "url_meta": url_meta}, fh, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out}")


if __name__ == "__main__":
    main()
