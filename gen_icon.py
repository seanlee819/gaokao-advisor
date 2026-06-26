from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, math, random

SIZE = 144
OUT = r"F:\Hermes model\gaokao_advisor\miniapp\images\icon.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
cx, cy = SIZE // 2, SIZE // 2
r = SIZE // 2 - 2

# ═══════════════════════════════════════
# 1. BACKGROUND: Bold modern gradient (purple→coral)
# ═══════════════════════════════════════
for y in range(SIZE):
    for x in range(SIZE):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist <= r:
            t = y / SIZE
            # Vivid purple-to-coral diagonal gradient
            angle_factor = (x / SIZE + y / SIZE) / 2
            r_val = int(120 - t*20 + angle_factor*80)    # 120→200ish
            g_val = int(30 + t*30 + angle_factor*30)     # 30→90ish
            b_val = int(180 - t*100 + angle_factor*20)   # 180→100ish
            img.putpixel((x, y), (r_val, g_val, b_val, 255))

# ═══════════════════════════════════════
# 2. Outer ring — white with glow
# ═══════════════════════════════════════
ring_r = r - 1
ring_w = 3
for y in range(SIZE):
    for x in range(SIZE):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if ring_r - ring_w <= dist <= ring_r:
            edge = 1 - abs(dist - (ring_r - ring_w/2)) / (ring_w/2)
            a = int(200 * (0.5 + 0.5 * edge))
            img.putpixel((x, y), (255, 255, 255, a))

# ═══════════════════════════════════════
# 3. Inner glow circle (behind text)
# ═══════════════════════════════════════
inner_r = r - 18
for y in range(SIZE):
    for x in range(SIZE):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist <= inner_r:
            ratio = dist / inner_r
            a = int(30 * (1 - ratio))
            img.putpixel((x, y), (255, 255, 255, a))

# ═══════════════════════════════════════
# 4. FONTS
# ═══════════════════════════════════════
font_paths = [
    "C:/Windows/Fonts/msyhbd.ttf",   # 微软雅黑 Bold
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]
def load_font(size):
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

font_main = load_font(80)   # "榜"
font_top = load_font(28)    # "看金"

# ═══════════════════════════════════════
# 5. MAIN TEXT "榜" — white with gold shadow
# ═══════════════════════════════════════
text = "榜"
bbox = draw.textbbox((0, 0), text, font=font_main)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = cx - tw // 2
ty = cy - th // 2 - 6

# Shadow
draw.text((tx+2, ty+2), text, font=font_main, fill=(0,0,0,100))
# Main: bright gold-white gradient feel (white with warm tint)
draw.text((tx, ty), text, font=font_main, fill=(255, 245, 220, 255))
# Subtle top highlight
draw.text((tx, ty-1), text, font=font_main, fill=(255, 255, 250, 120))

# ═══════════════════════════════════════
# 6. TOP TEXT "看金"  
# ═══════════════════════════════════════
text_top = "看金"
bbox2 = draw.textbbox((0, 0), text_top, font=font_top)
tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
tx2 = cx - tw2 // 2
ty2 = ty - 30

draw.text((tx2+1, ty2+1), text_top, font=font_top, fill=(0,0,0,80))
draw.text((tx2, ty2), text_top, font=font_top, fill=(255, 220, 100, 255))

# ═══════════════════════════════════════
# 7. DECORATIVE DOTS (top and bottom)
# ═══════════════════════════════════════
for dot_y in [9, SIZE-12]:
    for i in range(3):
        dx = (i - 1) * 16
        px, py = cx + dx, dot_y
        for dy2 in range(-2, 3):
            for dx2 in range(-2, 3):
                if dx2*dx2 + dy2*dy2 <= 4:
                    ppx, ppy = px + dx2, py + dy2
                    if 0 <= ppx < SIZE and 0 <= ppy < SIZE:
                        img.putpixel((ppx, ppy), (255, 220, 100, 200))

# ═══════════════════════════════════════
# 8. SUBTLE SPARKLE PARTICLES
# ═══════════════════════════════════════
random.seed(7)
for _ in range(6):
    angle = random.uniform(0.3, 2.8)
    dist = random.uniform(inner_r - 5, r - 25)
    sx = int(cx + dist * math.cos(angle))
    sy = int(cy + dist * math.sin(angle))
    if 0 <= sx < SIZE and 0 <= sy < SIZE:
        # Tiny cross sparkle
        for dr, dc in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
            px, py = sx+dc, sy+dr
            if 0 <= px < SIZE and 0 <= py < SIZE:
                dx2, dy2 = px - cx, py - cy
                if math.sqrt(dx2*dx2 + dy2*dy2) <= r:
                    img.putpixel((px, py), (255, 255, 240, 200))

# ═══════════════════════════════════════
# 9. SAVE
# ═══════════════════════════════════════
img.save(OUT, "PNG")
fsize = os.path.getsize(OUT)
print(f"Icon: {OUT} ({fsize} bytes, {SIZE}x{SIZE})")
print("Design: purple-coral gradient + gold '看金榜' + sparkles")
