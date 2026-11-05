#!/usr/bin/env python3
"""把素材硬编码进 breathing-garden.html（生成单文件应用，不依赖任何本地文件）。

- 背景：平滑渐变插画，转 JPEG（体积远小于 PNG），画质取视觉无损档
- 花朵精灵：必须保留透明通道，继续用 PNG，仅缩到够用的分辨率
- 全部转成 data URI，写进 HTML 里的 ASSET_DATA 块

可重复运行：每次重写整块，不会叠加。
"""
import base64, io, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PIL import Image

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(D, "assets")
HTML = os.path.join(D, "breathing-garden.html")

THEMES = ["day", "dawn", "dusk", "night"]
SPRITES = ["flower-star-pink-sprite.png", "flower-star-yellow-sprite.png",
           "flower-bell-violet-sprite.png", "flower-bell-coral-sprite.png",
           "flower-reed-blue-sprite.png", "flower-reed-magenta-sprite.png"]

BG_QUALITY = 88      # 背景 JPEG 质量
BG_MAXW = 1672       # 背景最大宽度（保持原尺寸）
SPRITE_MAXH = 300    # 精灵最大高度（显示尺寸最大约 110px，2x 屏也够）


def jpeg_data_uri(path, quality, maxw):
    im = Image.open(path).convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), buf.tell()


def png_data_uri(path, maxh):
    im = Image.open(path).convert("RGBA")
    if im.height > maxh:
        im = im.resize((max(1, round(im.width * maxh / im.height)), maxh), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), buf.tell()


def main():
    entries, total = [], 0
    print("=== 背景 → JPEG (q%d) ===" % BG_QUALITY)
    for t in THEMES:
        p = os.path.join(A, "bg-%s.png" % t)
        uri, n = jpeg_data_uri(p, BG_QUALITY, BG_MAXW)
        total += n
        print("  bg-%-6s %6.0f KB  (base64 %5.0f KB)" % (t, n / 1024, len(uri) / 1024))
        entries.append(("bg-%s.png" % t, uri))

    print("=== 花朵精灵 → PNG (≤%dpx) ===" % SPRITE_MAXH)
    for s in SPRITES:
        p = os.path.join(A, s)
        uri, n = png_data_uri(p, SPRITE_MAXH)
        total += n
        print("  %-34s %6.0f KB  (base64 %5.0f KB)" % (s, n / 1024, len(uri) / 1024))
        entries.append((s, uri))

    print("\n原始文件合计 %.2f MB → 压缩后 %.2f MB → base64 后约 %.2f MB"
          % (sum(os.path.getsize(os.path.join(A, k)) for k, _ in entries) / 1048576,
             total / 1048576,
             sum(len(u) for _, u in entries) / 1048576))

    # 组装成 JS（每个 key 一行，便于 diff）
    lines = ["var ASSET_DATA = {"]
    for k, uri in entries:
        lines.append('"%s": "%s",' % (k, uri))
    lines.append("};")
    block = "\n".join(lines)

    html = open(HTML, encoding="utf-8").read()
    pat = re.compile(r'(<script id="assetData">)(.*?)(</script>)', re.S)
    if not pat.search(html):
        print("❌ 未找到 assetData 块，未做修改")
        sys.exit(1)
    html2 = pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(3), html)

    open(HTML, "w", encoding="utf-8").write(html2)
    print("\n已写入 %s   成品 %.2f MB" % (os.path.basename(HTML),
                                        os.path.getsize(HTML) / 1048576))


if __name__ == "__main__":
    main()
