#!/usr/bin/env python3
"""Profile a tabular file for chart selection. No third-party dependencies."""
import argparse
import csv
import io
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    re.compile(r"^\d{4}-\d{2}$"),
    re.compile(r"^\d{4}$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"),
]


def read_csv(path, max_rows):
    raw = open(path, "rb").read(65536)
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(dict(row))
        return rows, reader.fieldnames or []


def read_json(path, max_rows):
    data = json.load(open(path, "r", encoding="utf-8-sig"))
    if isinstance(data, list):
        if not data:
            return [], []
        if isinstance(data[0], dict):
            return data[:max_rows], list(data[0].keys())
        width = max(len(r) for r in data if isinstance(r, list))
        rows = [{"col%d" % (i + 1): (r[i] if i < len(r) else "") for i in range(width)} for r in data[:max_rows]]
        return rows, list(rows[0].keys()) if rows else []
    if isinstance(data, dict):
        cols = list(data.keys())
        length = max((len(v) for v in data.values() if isinstance(v, list)), default=0)
        rows = []
        for i in range(min(length, max_rows)):
            rows.append({c: (data[c][i] if isinstance(data[c], list) and i < len(data[c]) else "") for c in cols})
        return rows, cols
    raise ValueError("JSON 必须是对象数组、二维数组或列对象")


def clean_num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("%", "")
    if s == "" or s.lower() in {"na", "n/a", "nan", "null", "none", "-"}:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def is_date(s):
    s = str(s).strip()
    if not s:
        return False
    if not any(p.match(s) for p in DATE_PATTERNS):
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except Exception:
        return len(s) in (4, 7, 10)


def infer_type(values):
    vals = [str(v).strip() for v in values if str(v).strip() != ""]
    if not vals:
        return "empty"
    lowered = {v.lower() for v in vals}
    if lowered <= {"true", "false", "yes", "no"}:
        return "boolean"
    nums = [clean_num(v) for v in vals]
    if all(x is not None for x in nums):
        return "numeric"
    if len(vals) >= 2 and all(is_date(v) for v in vals):
        return "datetime"
    return "categorical"


def column_stats(name, values):
    vals = [str(v).strip() for v in values]
    non_null = [v for v in vals if v != "" and v.lower() not in {"na", "n/a", "nan", "null", "none", "-"}]
    typ = infer_type(non_null)
    out = {
        "name": name,
        "type": typ,
        "non_null": len(non_null),
        "missing": len(vals) - len(non_null),
        "unique": len(set(non_null)),
    }
    if typ == "numeric":
        nums = [clean_num(v) for v in non_null if clean_num(v) is not None]
        if nums:
            out.update({
                "min": min(nums),
                "max": max(nums),
                "mean": sum(nums) / len(nums),
                "zeros": sum(1 for x in nums if x == 0),
                "negatives": sum(1 for x in nums if x < 0),
            })
    elif typ == "datetime":
        parsed = []
        for v in non_null:
            try:
                parsed.append(datetime.fromisoformat(v.replace("Z", "+00:00")))
            except Exception:
                pass
        if parsed:
            out["min"] = min(parsed).isoformat()
            out["max"] = max(parsed).isoformat()
    else:
        out["top"] = [{"value": k, "count": v} for k, v in Counter(non_null).most_common(5)]
    return out


def profile(rows, columns):
    cols = []
    for c in columns:
        cols.append(column_stats(c, [r.get(c, "") for r in rows]))
    hints = []
    numeric = [c for c in cols if c["type"] == "numeric"]
    categorical = [c for c in cols if c["type"] == "categorical"]
    datetimes = [c for c in cols if c["type"] == "datetime"]
    names = {c["name"].lower() for c in cols}

    def is_error_col(c):
        n = c["name"].lower()
        return any(k in n for k in ("error", "err", "sd", "std", "sem", "ci", "uncertain", "sigma"))

    def is_count_col(c):
        return re.fullmatch(r"(n|count|size|sample_?size|replicates?)", c["name"].lower()) is not None

    error_cols = [c for c in numeric if is_error_col(c)]
    dim_numeric = [c for c in numeric if c not in error_cols and not is_count_col(c)]
    x_like = [c for c in dim_numeric
              if re.search(r"(temp|time|hour|day|dose|age|cycle|rate|pressure|speed|strain|freq)", c["name"].lower())]

    if datetimes and dim_numeric:
        hints.append("时间 + 数值：折线图；多系列可直接标注线尾；排名变化用 bump chart。")
    if len(categorical) == 1 and len(dim_numeric) == 1:
        hints.append("1 类别 + 1 数值：排序/比较优先用水平柱、点图或棒棒糖图。")
    if len(categorical) >= 2 and dim_numeric and not x_like:
        hints.append("2 个以上类别 + 数值：分组柱或热力图；层级构成用 treemap/sunburst。")
    if categorical and x_like and len(dim_numeric) >= 2 and not datetimes:
        hints.append(f"连续变量 {x_like[0]['name']} + 分组类别：多系列折线或分面；不要把它当成第三个类别做分组柱。")
    if len(dim_numeric) >= 3 and not x_like:
        hints.append("3 个以上数值列：散点矩阵、平行坐标或相关热力图；不要默认上雷达图。")
    if len(dim_numeric) == 2 and not x_like:
        hints.append("2 个数值列：散点图；第三维用气泡大小或颜色。")
    if {"source", "target"} <= names and ({"value", "weight"} & names):
        hints.append("检测到 source/target：流向数据，优先 sankey 或 chord。")
    if error_cols:
        hints.append("检测到误差列：用误差棒（custom-error-bar）或带阴影的区间。")
    if any(c.get("negatives", 0) for c in dim_numeric):
        hints.append("存在负值：避免堆叠柱和饼图；用发散色/双向柱。")
    if any(c.get("zeros", 0) for c in dim_numeric):
        hints.append("存在 0：对数轴会丢点，慎用 log。")
    if len(rows) > 200 and len(dim_numeric) >= 2:
        hints.append("样本较多：散点注意透明度/分箱，避免过绘。")
    if len(columns) > 12:
        hints.append("列数较多：先用平行坐标/热力图筛结构，再决定细节图。")

    warnings = []
    if not rows:
        warnings.append("没有读到数据行。")
    if any(c["missing"] for c in cols):
        warnings.append("存在缺失值；图上要么显式标注，要么在方法中说明剔除规则。")
    if len(rows) <= 3:
        warnings.append("样本量很小；避免用平滑、拟合或百分比堆叠制造过度确定性。")
    return {"rows": len(rows), "columns": cols, "hints": hints, "warnings": warnings}


def print_markdown(result, source):
    print(f"# 数据画像：{source}\n")
    print(f"- 行数：{result['rows']}")
    print(f"- 列数：{len(result['columns'])}\n")
    print("| 列 | 类型 | 非空 | 缺失 | 唯一 | 范围/高频值 |")
    print("|---|---|---:|---:|---:|---|")
    for c in result["columns"]:
        if c["type"] == "numeric" and "min" in c:
            detail = f"{c['min']:.6g} ~ {c['max']:.6g}（均值 {c['mean']:.6g}）"
            if c.get("negatives"):
                detail += f"；负值 {c['negatives']}"
        elif c["type"] == "datetime" and "min" in c:
            detail = f"{c['min']} ~ {c['max']}"
        elif c.get("top"):
            detail = "；".join(f"{x['value']} ({x['count']})" for x in c["top"])
        else:
            detail = "-"
        print(f"| {c['name']} | {c['type']} | {c['non_null']} | {c['missing']} | {c['unique']} | {detail} |")
    print("\n## 选图提示\n")
    for h in result["hints"]:
        print(f"- {h}")
    if not result["hints"]:
        print("- 没有命中规则；按 references/selection.md 的「数据形态 → 图族」手动判断。")
    if result["warnings"]:
        print("\n## 注意\n")
        for w in result["warnings"]:
            print(f"- {w}")


def main():
    ap = argparse.ArgumentParser(description="Profile a CSV/TSV/JSON table for chart selection.")
    ap.add_argument("path", help="CSV/TSV/JSON 文件")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而不是 Markdown")
    ap.add_argument("--max-rows", type=int, default=50000, help="最多读取的行数（默认 50000）")
    args = ap.parse_args()
    path = args.path
    try:
        if path.lower().endswith(".json"):
            rows, cols = read_json(path, args.max_rows)
        else:
            rows, cols = read_csv(path, args.max_rows)
        result = profile(rows, cols)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    if args.json:
        print(json.dumps({"ok": True, "source": path, **result}, ensure_ascii=False, indent=2))
    else:
        print_markdown(result, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
