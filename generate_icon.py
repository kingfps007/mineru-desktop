"""生成 MinerU Desktop 应用图标（build/icon.ico）。

设计：紫色渐变背景 + 白色 "M" 字母，圆角矩形，多尺寸打包到 .ico。

PIL .ico 多尺寸生成：传 sizes= 参数让 PIL 自动从最大图缩放打包，
不要用 append_images（实测会丢帧）。
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"c:\Users\King\Desktop\aoto-review260524-trea\electron-app\build\icon.ico"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# 颜色：与 UI 主题色 --accent #6366f1 一致
BG_TOP = (99, 102, 241)     # #6366f1
BG_BOTTOM = (67, 56, 202)   # #4338ca
FG = (255, 255, 255)


def make_square(size: int) -> Image.Image:
    """生成单张 RGBA 图标。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = size // 5
    # 渐变背景
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    # 圆角
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    # 画 M 字母
    text = "M"
    font = None
    for path in [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\verdana.ttf",
    ]:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, int(size * 0.62))
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] - size * 0.02
    draw2 = ImageDraw.Draw(out)
    draw2.text((x, y), text, fill=FG, font=font)
    return out


# Windows .ico 标准尺寸
sizes = [16, 24, 32, 48, 64, 128, 256]
# 用最大尺寸 256 作基础，PIL 会自动按 sizes 缩放打包所有帧
base = make_square(256)
base.save(
    OUT,
    format="ICO",
    sizes=[(s, s) for s in sizes],
)
print(f"Saved: {OUT}")
print(f"Size: {os.path.getsize(OUT)} bytes")

# 验证多帧
verify = Image.open(OUT)
print(f"ICO sizes: {verify.info.get('sizes')}")
print(f"ICO n_frames: {verify.n_frames}")
