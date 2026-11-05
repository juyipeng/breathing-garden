#!/usr/bin/env python3
"""把生图素材预处理成可直接 drawImage 的资源：
   1) 花朵：白底抠成透明、去白边(matte removal)、裁到内容边界、缩到统一高度
   2) 背景：探测地平线位置（草甸起始行），供运行时对齐种花基线
"""
import os, sys, glob, collections
from PIL import Image, ImageFilter

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(D, "assets")
os.makedirs(A, exist_ok=True)

FLOWERS = ["flower-star-pink", "flower-star-yellow",
           "flower-bell-violet", "flower-bell-coral",
           "flower-reed-blue", "flower-reed-magenta"]

SPRITE_H = 360        # 精灵统一高度（像素）
KEY_SOFT = 0.075      # 距离白的分界：小于此视为背景


def dist_white(r, g, b):
    """到纯白的归一化距离：白=0，饱和色或深色→大"""
    return ((255 - r) ** 2 + (255 - g) ** 2 + (255 - b) ** 2) ** 0.5 / 441.673


def key_white(im, light=0.02, blur=1.0):
    """抠图。两条关键：
    1) alpha 必须由「泛洪掩膜」决定，不能由「到白的距离」决定 ——
       紫花花瓣根部到花心是一大片近白色，按距离算会被判成透明，花心就没了。
       封闭在花瓣内部、泛洪到不了的近白区域，属于花的一部分，必须保留。
    2) 只有与画面四边连通的近白区域才算背景；生成图底色实测极均匀（d≤0.008），
       阈值取 0.02 就能干净分开，且不会误伤浅色花瓣。"""
    im = im.convert("RGB")
    w, h = im.size
    px = im.load()

    near = bytearray(w * h)                       # 1 = 近白
    for y in range(h):
        row = y * w
        for x in range(w):
            r, g, b = px[x, y]
            if dist_white(r, g, b) < light:
                near[row + x] = 1

    bg = bytearray(w * h)                          # 1 = 背景
    dq = collections.deque()
    for x in range(w):
        for y in (0, h - 1):
            i = y * w + x
            if near[i] and not bg[i]:
                bg[i] = 1; dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            i = y * w + x
            if near[i] and not bg[i]:
                bg[i] = 1; dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                i = ny * w + nx
                if near[i] and not bg[i]:
                    bg[i] = 1; dq.append((nx, ny))

    # alpha 直接来自掩膜（非背景=不透明），再轻微模糊做抗锯齿
    alpha = Image.new("L", (w, h))
    alpha.putdata([0 if bg[i] else 255 for i in range(w * h)])
    if blur:
        alpha = alpha.filter(ImageFilter.GaussianBlur(blur))

    out = Image.new("RGBA", (w, h))
    op = out.load()
    ap = alpha.load()
    for y in range(h):
        for x in range(w):
            a = ap[x, y] / 255.0
            if a <= 0.004:
                op[x, y] = (0, 0, 0, 0); continue
            r, g, b = px[x, y]
            # 去白蒙版：边缘像素是「花色 + 白底」的混合，去掉白底才不会留白晕
            nr = (r - 255 * (1 - a)) / a
            ng = (g - 255 * (1 - a)) / a
            nb = (b - 255 * (1 - a)) / a
            op[x, y] = (max(0, min(255, int(nr))),
                        max(0, min(255, int(ng))),
                        max(0, min(255, int(nb))),
                        int(a * 255))
    return out


def main():
    print("=== 花朵：抠图 / 裁剪 / 缩放 ===")
    for name in FLOWERS:
        src = os.path.join(D, "source", name + ".png")
        if not os.path.exists(src):
            print("  skip (缺失)", name); continue
        im = Image.open(src)
        cut = key_white(im)
        bbox = cut.getbbox()
        if bbox:
            cut = cut.crop(bbox)
        # 缩放到统一高度，宽度按比例
        r = SPRITE_H / cut.height
        cut = cut.resize((max(1, int(cut.width * r)), SPRITE_H), Image.LANCZOS)
        dst = os.path.join(A, name + "-sprite.png")
        cut.save(dst, optimize=True)
        print(f"  {name}-sprite.png  {cut.size[0]}x{cut.size[1]}  "
              f"{os.path.getsize(dst)//1024} KB")

    print("\n=== 背景：探测地平线（草甸起始行占比）===")
    for p in sorted(glob.glob(os.path.join(A, "bg-*.png"))):
        im = Image.open(p).convert("RGB")
        w, h = im.size
        px = im.load()
        # 从下往上扫：找到第一行「绿色明显强于蓝」的位置即地平线上方
        horizon = None
        for y in range(int(h * 0.35), h):
            r = g = b = 0
            step = max(1, w // 60)
            n = 0
            for x in range(0, w, step):
                pr, pg, pb = px[x, y]
                r += pr; g += pg; b += pb; n += 1
            r /= n; g /= n; b /= n
            if g > r + 6 and g > b + 14:      # 草甸：绿占优
                horizon = y; break
        frac = (horizon / h) if horizon else None
        print(f"  {os.path.basename(p)}  {w}x{h}  地平线 "
              + (f"{horizon}px  占比 {frac:.3f}" if horizon else "未探测到"))


if __name__ == "__main__":
    main()
