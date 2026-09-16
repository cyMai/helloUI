"""Capture full-page UI baselines and report visual changes without accepting them.

Optional dependencies: pip install -r requirements-visual.txt
"""

from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def image_dependencies():
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise RuntimeError("缺少图片对比依赖；先运行 python -m pip install -r <helloUI>/requirements-visual.txt。") from exc
    return Image, ImageChops


def browser_dependencies():
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("缺少截图依赖；先运行 python -m pip install -r <helloUI>/requirements-visual.txt，并准备 Chrome、Edge 或 Playwright Chromium。") from exc
    return PlaywrightTimeoutError, sync_playwright


def safe_name(page: str) -> str:
    import hashlib

    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", page).strip("-")[:50] or "home"
    return f"{name}-{hashlib.sha256(page.encode('utf-8')).hexdigest()[:8]}"


def page_url(root: Path, page: str, base_url: str | None) -> str:
    if base_url:
        return urljoin(base_url.rstrip("/") + "/", page.lstrip("/"))
    path = (root / page).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"页面不在项目内或不存在：{page}；动态路由请使用 --base-url")
    return path.as_uri()


def launch_browser(playwright, choice: str):
    choices = [choice] if choice != "auto" else ["chrome", "msedge", "chromium"]
    errors = []
    for channel in choices:
        try:
            options = {"headless": True}
            if channel != "chromium":
                options["channel"] = channel
            return playwright.chromium.launch(**options), channel
        except Exception as exc:
            errors.append(f"{channel}: {str(exc).splitlines()[0]}")
    raise RuntimeError("无法启动浏览器。可安装 Chrome/Edge，或运行 python -m playwright install chromium。" + " | ".join(errors))


def capture(root: Path, pages: list[str], widths: list[int], height: int, base_url: str | None, browser_choice: str):
    PlaywrightTimeoutError, sync_playwright = browser_dependencies()
    shots = {}
    with sync_playwright() as playwright:
        browser, channel = launch_browser(playwright, browser_choice)
        try:
            for page_name in pages:
                url = page_url(root, page_name, base_url)
                for width in widths:
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                        locale="zh-CN",
                        timezone_id="Asia/Shanghai",
                        reduced_motion="reduce",
                        color_scheme="light",
                    )
                    try:
                        page = context.new_page()
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=5000)
                        except PlaywrightTimeoutError:
                            pass
                        page.evaluate("() => Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, 3000))])")
                        page.evaluate("() => Promise.race([Promise.allSettled(Array.from(document.images, img => img.decode().catch(() => {}))), new Promise(resolve => setTimeout(resolve, 3000))])")
                        shots[(page_name, width)] = page.screenshot(full_page=True, animations="disabled")
                    finally:
                        context.close()
            version = browser.version
        finally:
            browser.close()
    return shots, channel, version


def compare_images(before_bytes: bytes, after_bytes: bytes, tolerance: int):
    Image, ImageChops = image_dependencies()
    with Image.open(BytesIO(before_bytes)) as before_image, Image.open(BytesIO(after_bytes)) as after_image:
        before = before_image.convert("RGB")
        after = after_image.convert("RGB")
    size_changed = before.size != after.size
    size = (max(before.width, after.width), max(before.height, after.height))
    old_canvas = Image.new("RGB", size, "white")
    new_canvas = Image.new("RGB", size, "white")
    old_canvas.paste(before, (0, 0))
    new_canvas.paste(after, (0, 0))
    difference = ImageChops.difference(old_canvas, new_canvas).convert("L")
    mask = difference.point(lambda value: 255 if value > tolerance else 0)
    changed_pixels = size[0] * size[1] - mask.histogram()[0]
    highlighted = Image.blend(new_canvas, Image.new("RGB", size, "red"), 0.65)
    overlay = Image.composite(highlighted, new_canvas, mask)
    return {
        "changed_pixels": changed_pixels,
        "changed_percent": round(changed_pixels * 100 / (size[0] * size[1]), 4),
        "before_size": before.size,
        "after_size": after.size,
        "size_changed": size_changed,
        "overlay": overlay,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--mode", choices=["baseline", "compare"], required=True)
    parser.add_argument("--pages", nargs="+", help="首次建立基线时必填；静态 HTML 路径或站点路由")
    parser.add_argument("--base-url", help="运行中站点的地址；不传则打开项目内的静态 HTML")
    parser.add_argument("--widths", nargs="+", type=int, help="首次建立基线默认 390 1280")
    parser.add_argument("--height", type=int, help="视口高度；首次建立基线默认 900")
    parser.add_argument("--browser", choices=["auto", "chrome", "msedge", "chromium"], default="auto")
    parser.add_argument("--pixel-tolerance", type=int, default=16, help="像素亮度差阈值，0-255")
    parser.add_argument("--max-diff-percent", type=float, default=0.1, help="超过该变化百分比则返回失败")
    parser.add_argument("--replace-baseline", action="store_true", help="明确接受变化后覆盖整套基线；仅用于 baseline 模式")
    args = parser.parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        parser.error("项目目录不存在")
    if not 0 <= args.pixel_tolerance <= 255 or not 0 <= args.max_diff_percent <= 100:
        parser.error("阈值超出有效范围")
    baseline_dir = root / "ui-baseline"
    manifest_file = baseline_dir / "manifest.json"
    if args.mode == "baseline":
        if not args.pages:
            parser.error("首次建立基线需要 --pages")
        if manifest_file.exists() and not args.replace_baseline:
            parser.error("基线已存在；先 compare 审核差异，确认后才使用 --replace-baseline")
        pages = args.pages
        widths = args.widths or [390, 1280]
        height = args.height or 900
        base_url = args.base_url
    else:
        if args.replace_baseline:
            parser.error("--replace-baseline 只用于 baseline 模式")
        if not manifest_file.exists():
            parser.error("未找到 ui-baseline/manifest.json；先建立基线")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        pages = manifest["pages"]
        widths = manifest["widths"]
        height = manifest["height"]
        base_url = args.base_url if args.base_url is not None else manifest.get("base_url")
        if args.pages or args.widths or args.height:
            parser.error("compare 使用基线中的页面和视口；新增页面请审核后重建基线")
    if not pages or any(width < 200 or width > 5000 for width in widths) or height < 200 or height > 5000:
        parser.error("页面或视口参数无效")

    try:
        browser_choice = manifest["browser"] if args.mode == "compare" and args.browser == "auto" else args.browser
        shots, channel, version = capture(root, pages, widths, height, base_url, browser_choice)
    except (RuntimeError, ValueError, OSError) as exc:
        parser.exit(2, f"截图失败：{exc}\n")
    if args.mode == "baseline":
        baseline_dir.mkdir(parents=True, exist_ok=True)
        for (page, width), shot in shots.items():
            (baseline_dir / f"{safe_name(page)}-{width}.png").write_bytes(shot)
        manifest_file.write_text(json.dumps({
            "schema_version": 1, "pages": pages, "widths": widths, "height": height,
            "base_url": base_url, "browser": channel, "browser_version": version,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已保存 {len(shots)} 张基线截图：{baseline_dir}")
        return 0

    report_dir = root / ".hello-ui" / "visual-report"
    report_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for (page, width), shot in shots.items():
        name = f"{safe_name(page)}-{width}"
        baseline_file = baseline_dir / f"{name}.png"
        if not baseline_file.exists():
            parser.exit(2, f"缺少基线截图：{baseline_file}\n")
        current_file = report_dir / f"{name}-current.png"
        diff_file = report_dir / f"{name}-diff.png"
        current_file.write_bytes(shot)
        comparison = compare_images(baseline_file.read_bytes(), shot, args.pixel_tolerance)
        comparison.pop("overlay").save(diff_file)
        changed = comparison["size_changed"] or comparison["changed_percent"] > args.max_diff_percent
        results.append({"page": page, "width": width, "changed": changed, **comparison,
                        "baseline": str(baseline_file), "current": str(current_file), "diff": str(diff_file)})
    summary = {"browser": channel, "browser_version": version,
               "baseline_browser": manifest["browser"], "baseline_browser_version": manifest["browser_version"],
               "max_diff_percent": args.max_diff_percent, "results": results}
    (report_dir / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# helloUI 页面截图对比", "", f"当前浏览器：{channel} {version}；基线：{manifest['browser']} {manifest['browser_version']}。", ""]
    if channel != manifest["browser"] or version != manifest["browser_version"]:
        lines.extend(["浏览器环境与基线不同，差异可能包含渲染环境变化。", ""])
    lines.extend(["| 页面 | 宽度 | 变化像素 | 变化比例 | 结果 |", "| --- | ---: | ---: | ---: | --- |"])
    for item in results:
        lines.append(f"| `{item['page']}` | {item['width']} | {item['changed_pixels']} | {item['changed_percent']:.4f}% | {'需审核' if item['changed'] else '通过'} |")
    lines.extend(["", "差异图中的红色区域表示变化；尺寸变化也会标为需审核。基线不会由 compare 自动更新。", ""])
    (report_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{sum(item['changed'] for item in results)} / {len(results)} 张截图需审核：{report_dir / 'report.md'}")
    return 1 if any(item["changed"] for item in results) else 0


if __name__ == "__main__":
    sys.exit(main())
