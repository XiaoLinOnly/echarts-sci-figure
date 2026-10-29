#!/usr/bin/env python3
"""Search the local ECharts example index."""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "assets", "index.json")


def load_index():
    with open(INDEX, "r", encoding="utf-8") as f:
        return json.load(f)


def score(item, tokens):
    hay_id = item["id"].lower()
    hay_title = (item.get("title", "") + " " + item.get("titleCN", "")).lower()
    hay_cat = " ".join(item.get("category", [])).lower()
    hay_tags = " ".join(item.get("tags", [])).lower()
    total = 0
    for t in tokens:
        if t == hay_id:
            total += 100
        elif t in hay_id:
            total += 12
        if t in hay_title:
            total += 8
        if t in hay_cat:
            total += 6
        if t in hay_tags:
            total += 4
    return total


def format_example(item):
    return {
        "id": item["id"],
        "title": item.get("title", ""),
        "titleCN": item.get("titleCN", ""),
        "category": item.get("category", []),
        "difficulty": item.get("difficulty", 0),
        "cached": bool(item.get("cached")),
        "file": item.get("file", ""),
    }


def show_text(item):
    path = os.path.join(ROOT, item["file"])
    if not os.path.exists(path):
        print(f"未缓存：{path}\n运行: python scripts/update_examples.py --id {item['id']}")
        return
    with open(path, "r", encoding="utf-8") as f:
        print(f.read())


def main():
    ap = argparse.ArgumentParser(description="Search ECharts examples by keyword, category or id.")
    ap.add_argument("--query", "-q", default="", help="关键词（支持中文/英文，空格分词）")
    ap.add_argument("--category", "-c", default="", help="按类别过滤，如 bar / line / sankey")
    ap.add_argument("--id", default="", help="精确查看某个示例")
    ap.add_argument("--cached-only", action="store_true", help="只显示本地已缓存的示例")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show", action="store_true", help="与 --id 一起用，打印示例源码")
    args = ap.parse_args()

    idx = load_index()
    items = idx["examples"]

    if not args.query and not args.category and not args.id:
        cats = {}
        for e in items:
            for c in e.get("category", []):
                cats[c] = cats.get(c, 0) + 1
        print("可用类别：")
        print("  " + "  ".join(f"{k}({v})" for k, v in sorted(cats.items(), key=lambda x: (-x[1], x[0]))))
        print("\n示例：python scripts/find_example.py --query 雷达 --cached-only")
        return 0

    if args.id:
        matches = [e for e in items if e["id"] == args.id]
        if not matches:
            print(f"未找到 id: {args.id}")
            return 1
        item = matches[0]
        if args.json:
            print(json.dumps(format_example(item), ensure_ascii=False, indent=2))
        else:
            print(f"# {item['id']}")
            print(f"- 标题：{item.get('titleCN') or item.get('title')}")
            print(f"- 类别：{', '.join(item.get('category', []))}")
            print(f"- 难度：{item.get('difficulty', 0)}/10")
            print(f"- 缓存：{'是' if item.get('cached') else '否'}")
            print(f"- 文件：{os.path.join(ROOT, item.get('file', ''))}")
            if args.show:
                print("\n```ts\n" + open(os.path.join(ROOT, item["file"]), encoding="utf-8").read() + "\n```")
        return 0

    tokens = [t for t in args.query.lower().replace("，", " ").replace(",", " ").split() if t]
    results = []
    for e in items:
        if args.cached_only and not e.get("cached"):
            continue
        if args.category and args.category.lower() not in " ".join(e.get("category", [])).lower():
            continue
        s = score(e, tokens) if tokens else 0
        if tokens and s == 0:
            continue
        results.append((s, e))
    results.sort(key=lambda x: (-x[0], x[1].get("difficulty", 0), x[1]["id"]))
    results = results[: args.limit]

    if args.json:
        print(json.dumps([format_example(e) for _, e in results], ensure_ascii=False, indent=2))
        return 0

    if not results:
        print("没有匹配。先去掉 --cached-only，或换更短的关键词。")
        return 1
    print("| id | 类别 | 中文名 | 难度 | 缓存 |")
    print("|---|---|---|---:|---|")
    for _, e in results:
        print(f"| `{e['id']}` | {', '.join(e.get('category', []))} | {e.get('titleCN') or e.get('title')} | {e.get('difficulty', 0)} | {'Y' if e.get('cached') else ''} |")
    print("\n查看源码：python scripts/find_example.py --id <id> --show")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
