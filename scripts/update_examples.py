#!/usr/bin/env python3
"""Refresh the local ECharts example index and cached option files."""
import argparse
import json
import os
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
EXAMPLES = os.path.join(ASSETS, "examples")
INDEX = os.path.join(ASSETS, "index.json")
API = "https://api.github.com/repos/apache/echarts-examples/contents"
HEADERS = {"Accept": "application/vnd.github.raw", "User-Agent": "echarts-sci-figure-skill"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as r:
        remaining = r.headers.get("X-RateLimit-Remaining")
        data = r.read()
    return data, int(remaining) if remaining is not None else None


def parse_index(data):
    text = data.decode("utf-8")
    start = text.index("[")
    end = text.rindex("]") + 1
    return json.loads(text[start:end])


def refresh_index():
    data, left = fetch(f"{API}/src/data/chart-list-data.js")
    arr = parse_index(data)
    old = {}
    if os.path.exists(INDEX):
        try:
            old_data = json.load(open(INDEX, encoding="utf-8"))
            old = {e["id"]: e for e in old_data.get("examples", [])}
        except Exception:
            pass
    items = []
    for e in arr:
        eid = e["id"]
        item = {
            "id": eid,
            "title": e.get("title", ""),
            "titleCN": e.get("titleCN", ""),
            "category": e.get("category", []),
            "tags": e.get("tags", []),
            "difficulty": e.get("difficulty", 0),
            "ts": bool(e.get("ts", False)),
            "file": f"assets/examples/{eid}.ts",
            "cached": False,
        }
        if eid in old and old[eid].get("cached") and os.path.exists(os.path.join(ROOT, item["file"])):
            item["cached"] = True
        for ext in (".ts", ".js"):
            if os.path.exists(os.path.join(EXAMPLES, eid + ext)):
                item["file"] = f"assets/examples/{eid}{ext}"
                item["cached"] = True
                break
        items.append(item)
    payload = {
        "source": "https://github.com/apache/echarts-examples",
        "source_index": "src/data/chart-list-data.js",
        "generated_at": time.strftime("%Y-%m-%d"),
        "count": len(items),
        "examples": items,
    }
    os.makedirs(ASSETS, exist_ok=True)
    json.dump(payload, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"index: {len(items)} examples, rate-limit remaining={left}")
    return payload


def download_one(item):
    os.makedirs(EXAMPLES, exist_ok=True)
    for ext in (".ts", ".js"):
        url = f"{API}/public/examples/{'ts' if ext == '.ts' else 'js'}/{item['id']}{ext}"
        try:
            data, left = fetch(url)
        except Exception as e:
            print(f"  fail {item['id']}{ext}: {e}")
            continue
        path = os.path.join(EXAMPLES, item["id"] + ext)
        open(path, "wb").write(data)
        item["file"] = f"assets/examples/{item['id']}{ext}"
        item["cached"] = True
        print(f"  ok {item['id']}{ext} {len(data)}B (remaining={left})")
        return left
    return None


def main():
    ap = argparse.ArgumentParser(description="Update the local ECharts examples cache.")
    ap.add_argument("--index-only", action="store_true", help="只刷新索引，不下载示例")
    ap.add_argument("--id", action="append", default=[], help="下载指定 id，可重复")
    ap.add_argument("--cached", action="store_true", help="重新下载所有已缓存的示例")
    ap.add_argument("--all", action="store_true", help="下载全部示例（会消耗大量 GitHub API 配额）")
    ap.add_argument("--yes", action="store_true", help="配合 --all 确认")
    args = ap.parse_args()

    idx = refresh_index()
    if args.index_only:
        return 0

    by_id = {e["id"]: e for e in idx["examples"]}
    targets = []
    if args.all:
        if not args.yes:
            print("--all 会发起数百次请求；确认请加 --yes。")
            return 1
        targets = [e for e in idx["examples"] if e.get("ts")]
    elif args.cached:
        targets = [e for e in idx["examples"] if e.get("cached")]
    else:
        for eid in args.id:
            if eid not in by_id:
                print(f"索引中没有 id: {eid}")
                continue
            targets.append(by_id[eid])

    if not targets:
        print("没有要下载的示例。用 --id <id> 指定，或 --cached 刷新已有缓存。")
        return 0

    remaining = None
    for i, item in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {item['id']}")
        remaining = download_one(item)
        if remaining == 0:
            print("GitHub API 配额已用完，停止。稍后可重跑同一命令。")
            break
        time.sleep(0.25)

    json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done: {sum(1 for e in idx['examples'] if e.get('cached'))}/{len(idx['examples'])} cached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
