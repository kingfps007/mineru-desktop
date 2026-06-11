import math
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow (PIL) is not installed.")
    print("Install it with: pip install Pillow")
    print("Or if using this project's venv:")
    print("  venv\\Scripts\\activate")
    print("  pip install Pillow")
    sys.exit(1)

SIZE = 256
SUPERSCALE = 4
HIGH_RES = SIZE * SUPERSCALE
CENTER = HIGH_RES // 2
RADIUS = int(HIGH_RES * 0.38)

BACKGROUND_CENTER = (37, 99, 235)
BACKGROUND_EDGE = (25, 70, 160)

HEX_FILL = (220, 235, 255)
HEX_BORDER = (30, 64, 175)
BORDER_WIDTH = int(HIGH_RES * 0.04)

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "electron-app", "build"
)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def hexagon_points(cx, cy, r):
    points = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    return points


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    img = Image.new("RGBA", (HIGH_RES, HIGH_RES), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(HIGH_RES):
        t = y / (HIGH_RES - 1)
        color = lerp_color(BACKGROUND_CENTER, BACKGROUND_EDGE, t)
        draw.line([(0, y), (HIGH_RES, y)], fill=color)

    outer_r = RADIUS + BORDER_WIDTH
    outer_pts = hexagon_points(CENTER, CENTER, outer_r)
    draw.polygon(outer_pts, fill=HEX_BORDER)

    inner_pts = hexagon_points(CENTER, CENTER, RADIUS)
    draw.polygon(inner_pts, fill=HEX_FILL)

    icon_img = img.resize((SIZE, SIZE), Image.LANCZOS)

    ico_path = os.path.join(OUTPUT_DIR, "icon.ico")
    icon_img.save(ico_path, format="ICO", sizes=[(SIZE, SIZE)])

    png_path = os.path.join(OUTPUT_DIR, "icon.png")
    icon_img.save(png_path, format="PNG")

    print(f"Generated: {ico_path}")
    print(f"Generated: {png_path}")
    print("Done.")


if __name__ == "__main__":
    main()
