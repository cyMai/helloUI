"""Extract reviewable design evidence from a small HTML/CSS project.

This script never writes DESIGN.md. It records observations and candidate rules;
an agent or maintainer must decide which candidates become project policy.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

SKIP_DIRS = {".git", ".hello-ui", ".design-spec", "node_modules", "dist", "build", "coverage", ".next", ".venv"}
HTML_EXT = {".html", ".htm"}
CSS_EXT = {".css", ".scss"}
SHARED_PROPERTIES = {"color", "background", "background-color", "font-family", "font-size", "font-weight", "border-radius", "box-shadow", "gap", "padding", "margin"}
IGNORED_VALUES = {"none", "inherit", "initial", "unset", "revert", "transparent", "currentcolor", "0", "auto"}


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sources(root: Path) -> list[Path]:
    found = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in HTML_EXT | CSS_EXT and path.stat().st_size <= 500_000:
            found.append(path)
            if len(found) >= 1000:
                break
    return sorted(found)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.classes = Counter()
        self.stylesheets = []
        self.inline_styles = 0
        self.viewport = False
        self.landmarks = Counter()
        self.in_style = False
        self.style_blocks = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for name in (values.get("class") or "").split():
            self.classes[name] += 1
        if values.get("style"):
            self.inline_styles += 1
        if tag == "meta" and (values.get("name") or "").lower() == "viewport":
            self.viewport = True
        if tag == "link" and "stylesheet" in (values.get("rel") or "").lower().split() and values.get("href"):
            self.stylesheets.append(values["href"])
        if tag in {"header", "nav", "main", "section", "aside", "footer"}:
            self.landmarks[tag] += 1
        if tag == "style":
            self.in_style = True
            self.style_blocks.append({"line": self.getpos()[0], "text": ""})

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.style_blocks[-1]["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False


def parse_page(path: Path, root: Path) -> dict:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return {
        "path": relative(path, root),
        "viewport": parser.viewport,
        "stylesheets": parser.stylesheets,
        "classes": dict(sorted(parser.classes.items())),
        "inline_style_count": parser.inline_styles,
        "embedded_style_count": len(parser.style_blocks),
        "landmarks": dict(sorted(parser.landmarks.items())),
        "embedded_styles": parser.style_blocks,
    }


def blank_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda m: "".join("\n" if c == "\n" else " " for c in m.group()), text, flags=re.S)


def css_blocks(text: str):
    """Yield (header, body, line, ancestor headers) for ordinary CSS blocks."""
    text = blank_comments(text)
    stack = []
    start = 0
    quote = None
    escaped = False
    for i, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "{":
            header = text[start:i].strip()
            stack.append((header, text.count("\n", 0, start) + 1))
            start = i + 1
        elif char == "}" and stack:
            body = text[start:i]
            header, line = stack.pop()
            yield header, body, line, [item[0] for item in stack]
            start = i + 1


def parse_css_text(text: str, filename: str, line_offset: int = 0) -> tuple[list[dict], list[dict]]:
    rules = []
    queries = []
    for header, body, line, ancestors in css_blocks(text):
        line += line_offset
        if header.startswith(("@media", "@container")):
            queries.append({"file": filename, "line": line, "query": header})
            continue
        if not header or header.startswith("@"):
            continue
        declarations = {}
        for part in body.split(";"):
            if ":" not in part:
                continue
            property_name, value = part.split(":", 1)
            property_name = property_name.strip().lower()
            value = re.sub(r"\s+", " ", value.strip())
            if re.fullmatch(r"--[\w-]+|[a-z-]+", property_name) and value:
                declarations[property_name] = value
        if declarations:
            rules.append({
                "file": filename,
                "line": line,
                "selector": header,
                "context": [name for name in ancestors if name.startswith(("@media", "@container"))],
                "declarations": declarations,
            })
    return rules, queries


def parse_css(path: Path, root: Path) -> tuple[list[dict], list[dict]]:
    return parse_css_text(path.read_text(encoding="utf-8", errors="replace"), relative(path, root))


def analyze(root: Path) -> dict:
    files = sources(root)
    pages = [parse_page(path, root) for path in files if path.suffix.lower() in HTML_EXT]
    rules = []
    queries = []
    for path in files:
        if path.suffix.lower() in CSS_EXT:
            file_rules, file_queries = parse_css(path, root)
            rules.extend(file_rules)
            queries.extend(file_queries)
    for page in pages:
        for block in page.pop("embedded_styles"):
            file_rules, file_queries = parse_css_text(block["text"], page["path"], block["line"])
            rules.extend(file_rules)
            queries.extend(file_queries)

    tokens = defaultdict(list)
    values = defaultdict(list)
    for rule in rules:
        source = {"file": rule["file"], "line": rule["line"], "selector": rule["selector"], "context": rule["context"]}
        for prop, value in rule["declarations"].items():
            if prop.startswith("--"):
                tokens[prop].append({**source, "value": value})
            if prop in SHARED_PROPERTIES and value.lower() not in IGNORED_VALUES:
                values[(prop, value)].append(source)

    repeated = []
    for (prop, value), occurrences in values.items():
        distinct = {(item["file"], item["selector"], tuple(item["context"])) for item in occurrences}
        if len(distinct) >= 2:
            repeated.append({"property": prop, "value": value, "occurrences": occurrences})
    repeated.sort(key=lambda item: (-len(item["occurrences"]), item["property"], item["value"]))

    page_classes = defaultdict(list)
    for page in pages:
        for class_name in page["classes"]:
            page_classes[class_name].append(page["path"])
    shared_classes = [{"class": name, "pages": paths} for name, paths in sorted(page_classes.items()) if len(paths) >= 2]

    issues = []
    for page in pages:
        if not page["viewport"]:
            issues.append({"kind": "missing-viewport", "file": page["path"], "detail": "未发现 viewport meta"})
        if page["inline_style_count"]:
            issues.append({"kind": "inline-style", "file": page["path"], "detail": f"发现 {page['inline_style_count']} 处行内样式；请核对是否偏离共享规则"})
        if page["embedded_style_count"]:
            issues.append({"kind": "page-local-style", "file": page["path"], "detail": f"发现 {page['embedded_style_count']} 组页面内 CSS；请核对与共享样式的差异"})
    for name, entries in tokens.items():
        distinct = {entry["value"] for entry in entries if not entry["context"]}
        if len(distinct) > 1:
            filenames = ", ".join(sorted({entry["file"] for entry in entries}))
            issues.append({"kind": "token-conflict", "file": filenames, "detail": f"{name} 在默认上下文中有多个值：{', '.join(sorted(distinct))}"})
    for rule in rules:
        declarations = rule["declarations"]
        width = declarations.get("width", "")
        columns = declarations.get("grid-template-columns", "")
        if re.fullmatch(r"\d{3,}px", width) or re.search(r"\b\d{3,}px\b", columns):
            issues.append({"kind": "fixed-width-review", "file": f"{rule['file']}:{rule['line']}", "detail": f"`{rule['selector']}` 使用固定宽度/栏宽；请检查窄屏溢出"})

    return {
        "schema_version": 1,
        "source_hashes": {relative(path, root): hashlib.sha256(path.read_bytes()).hexdigest()[:16] for path in files},
        "pages": pages,
        "css_rules": rules,
        "tokens": dict(sorted(tokens.items())),
        "queries": queries,
        "repeated_values": repeated,
        "shared_classes": shared_classes,
        "issues": issues,
        "limits": ["仅分析静态 HTML 与 CSS/SCSS 文本", "不计算浏览器实际样式、不验证视觉呈现", "候选规则未经设计审核，不能直接当作项目规范"],
    }


def render_proposals(data: dict) -> str:
    lines = [
        "# helloUI 候选设计规则（待审核）", "",
        "以下内容由源码提取，不代表已批准的设计意图。核对实际页面后，才把适用规则写入项目根目录的 `DESIGN.md`。", "",
        "## 页面与响应式线索", "",
    ]
    if data["pages"]:
        for page in data["pages"]:
            lines.append(f"- `{page['path']}`：viewport {'已设置' if page['viewport'] else '未发现'}；引用样式表 {', '.join(f'`{s}`' for s in page['stylesheets']) or '未发现'}。")
    else:
        lines.append("- 未发现静态 HTML 页面。")
    lines.extend(["", "媒体/容器查询（只证明代码中存在这些条件）："])
    lines.extend(f"- `{q['query']}` — `{q['file']}:{q['line']}`" for q in data["queries"][:30])
    if not data["queries"]:
        lines.append("- 未发现。")

    lines.extend(["", "## 共享视觉线索", ""])
    if data["tokens"]:
        lines.append("CSS 自定义属性候选：")
        for name, entries in list(data["tokens"].items())[:30]:
            lines.append(f"- `{name}`：" + "；".join(f"`{e['value']}`（`{e['file']}:{e['line']}`，`{e['selector']}`）" for e in entries[:4]))
    else:
        lines.append("未发现 CSS 自定义属性。")
    lines.append("")
    if data["repeated_values"]:
        lines.append("重复样式值（需判断是规则还是巧合）：")
        for item in data["repeated_values"][:25]:
            samples = "、".join(f"`{e['file']}:{e['line']}` {e['selector']}" for e in item["occurrences"][:4])
            lines.append(f"- `{item['property']}: {item['value']}` 出现 {len(item['occurrences'])} 次；例如 {samples}。")
    else:
        lines.append("未发现跨选择器重复的目标样式值。")
    lines.extend(["", "跨页面共享类名："])
    lines.extend(f"- `.{item['class']}`：{', '.join(f'`{p}`' for p in item['pages'])}" for item in data["shared_classes"][:25])
    if not data["shared_classes"]:
        lines.append("- 未发现。")

    lines.extend(["", "## 需要人工核对", ""])
    lines.extend(f"- {item['detail']}（{item['file']}）" for item in data["issues"])
    if not data["issues"]:
        lines.append("- 静态扫描未发现上述风险；仍需检查实际页面。")
    lines.extend(["", "## 审核步骤", "", "1. 在手机与桌面宽度查看同一份页面，并补查布局转换处的宽度。", "2. 对照现有模板和用户要求，区分全局规则、页面例外与历史漂移。", "3. 只把确认后的规则写入 `DESIGN.md`；已有规则不能仅凭本报告被覆盖。", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, help="默认写入 <project-root>/.hello-ui")
    args = parser.parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        parser.error("project root does not exist")
    out_dir = (args.out_dir or root / ".hello-ui").resolve()
    data = analyze(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = out_dir / "evidence.json"
    proposal_file = out_dir / "proposals.md"
    evidence_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    proposal_file.write_text(render_proposals(data), encoding="utf-8")
    print(f"pages={len(data['pages'])} css_rules={len(data['css_rules'])} tokens={len(data['tokens'])} repeated_values={len(data['repeated_values'])} issues={len(data['issues'])}")
    print(evidence_file)
    print(proposal_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
