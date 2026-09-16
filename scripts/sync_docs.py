"""Create and refresh observable source pointers in six design documents."""

import argparse
import hashlib
import json
import time
from pathlib import Path

DOCS = {
    "spec.md": "功能目标、任务链、状态流转、验收与跨端差异",
    "domain.md": "业务对象、术语、风险和责任规则",
    "craft.md": "排版、密度、反馈、动效与触控差异",
    "design.md": "语义 token、主题、字体、间距与响应式尺度",
    "components.md": "组件用途、变体、状态、无障碍与自适应",
    "template.md": "页面类型、导航、区域与栏位转换",
}
START = "<!-- living-design:source:start -->"
END = "<!-- living-design:source:end -->"
IGNORE = {".git", "node_modules", "dist", "build", "coverage", ".next", ".venv", ".design-spec"}


def sources(root):
    result = []
    for path in root.rglob("*"):
        if len(result) >= 1000:
            break
        if any(part in IGNORE for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in {".css", ".scss", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"} and path.stat().st_size < 500_000:
            result.append(path)
    return sorted(result)


def classify(name):
    p = name.lower()
    if "token" in p or "theme" in p or p.endswith((".css", ".scss")):
        return {"design.md", "craft.md", "template.md"}
    if "component" in p or "/ui/" in p:
        return {"components.md", "craft.md"}
    if "page" in p or "route" in p or "screen" in p or "/app/" in p:
        return {"spec.md", "template.md"}
    if "model" in p or "schema" in p or "domain" in p:
        return {"domain.md", "spec.md"}
    return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--mode", choices=("immediate", "passive"), default="immediate")
    ap.add_argument("--quiet-minutes", type=float, default=30)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        ap.error("project root does not exist")
    if args.check:
        problems = [name for name in DOCS if not (root / name).exists() or (root / name).read_text(encoding="utf-8").count(START) != 1 or (root / name).read_text(encoding="utf-8").count(END) != 1]
        print("valid" if not problems else "missing or invalid: " + ", ".join(problems))
        return 0 if not problems else 2
    paths = sources(root)
    mapping = {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in paths}
    state_path = root / ".design-spec" / "source-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    old = state.get("snapshot", {})
    changed = {p for p in set(mapping) | set(old) if mapping.get(p) != old.get(p)}
    pending = set(state.get("pending", [])) | changed
    now = time.time()
    last_change = now if changed else state.get("last_change", now)
    due = args.mode == "immediate" or (pending and now - last_change >= args.quiet_minutes * 60)
    selected = (set(DOCS) if args.mode == "immediate" or not old else set().union(*(classify(p) for p in pending))) if due else set()
    if not due:
        print(f"pending changes: {len(pending)}; quiet period not reached")
    for name in sorted(selected):
        relevant = [p for p in mapping if name in classify(p)][:30]
        pointers = "\n".join("- `" + p + "`" for p in relevant) or "- 本次未找到可归类的源码；请人工核对。"
        block = START + "\n## 源码线索（自动更新，不代表设计决策）\n\n" + pointers + "\n" + END
        target = root / name
        if not target.exists():
            target.write_text("# " + name.removesuffix(".md") + "\n\n范围：" + DOCS[name] + "。\n\n" + block + "\n\n## 当前规则\n\n[待确认]\n", encoding="utf-8")
            print(name + ": created")
            continue
        text = target.read_text(encoding="utf-8")
        if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
            print(name + ": preserved (invalid or missing markers)")
            continue
        before = text.split(START, 1)[0]
        after = text.split(END, 1)[1]
        updated = before + block + after
        if updated != text:
            target.write_text(updated, encoding="utf-8")
            print(name + ": updated")
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text(json.dumps({"snapshot": mapping, "pending": sorted(set() if due else pending), "last_change": last_change}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
