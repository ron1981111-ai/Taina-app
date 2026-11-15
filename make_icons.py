"""產生 PWA 圖示(只需執行一次,已附上成品)"""
import os
from PIL import Image, ImageDraw

os.makedirs("static/icons", exist_ok=True)
TEAL_TOP, TEAL_BOTTOM = (45, 212, 191), (13, 148, 136)


def gradient(size):
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        c = tuple(int(TEAL_TOP[i] * (1 - t) + TEAL_BOTTOM[i] * t) for i in range(3))
        for x in range(size):
            px[x, y] = c
    return img


def draw_skyline(img, scale):
    """scale: 內容佔畫面比例 (maskable 用 0.62,一般用 0.74)"""
    s = img.size[0]
    d = ImageDraw.Draw(img)
    box = s * scale
    left = (s - box) / 2
    base = s * 0.5 + box / 2
    # 太陽
    r = box * 0.14
    cx, cy = left + box * 0.78, s * 0.5 - box * 0.30
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(254, 240, 138))
    # 城市天際線(白色長條)
    heights = [0.42, 0.66, 0.52, 0.80, 0.36]
    w = box / (len(heights) * 1.35)
    gap = (box - w * len(heights)) / (len(heights) - 1)
    for i, h in enumerate(heights):
        x0 = left + i * (w + gap)
        d.rounded_rectangle([x0, base - box * h, x0 + w, base], radius=w * 0.18, fill="white")
        # 窗戶
        for k in range(int(h * 5)):
            wy = base - box * h + w * 0.35 + k * w * 0.55
            if wy + w * 0.2 < base - w * 0.2:
                d.rectangle([x0 + w * 0.3, wy, x0 + w * 0.7, wy + w * 0.2], fill=(13, 148, 136))
    return img


def make(size, scale, name, rounded=False):
    img = draw_skyline(gradient(size), scale)
    if rounded:
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=int(size * 0.22), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        img = out
    img.save(f"static/icons/{name}")


make(192, 0.74, "icon-192.png", rounded=True)
make(512, 0.74, "icon-512.png", rounded=True)
make(512, 0.60, "icon-maskable-512.png")       # 滿版,內容留在安全區內
make(180, 0.66, "apple-touch-icon.png")         # iOS 會自行裁圓角,需無透明
make(32, 0.80, "favicon-32.png", rounded=True)
print("icons done")
