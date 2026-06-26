
from PIL import Image, ImageDraw, ImageFont
import os, math, random

SIZE = 1024
OUT = r"F:\Hermes model\gaokao_advisor\miniapp\images\icon_hd.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
cx, cy = SIZE // 2, SIZE // 2
r = SIZE // 2 - 4

# Background: vibrant purple→coral gradient
for y in range(SIZE):
    for x in range(SIZE):
        dx, dy = x - cx, y - cy
        if math.sqrt(dx*dx + dy*dy) <= r:
            t = y / SIZE
            af = (x/SIZE + y/SIZE) / 2
            rv = int(130 - t*30 + af*70)
            gv = int(35 + t*35 + af*25)
            bv = int(190 - t*110 + af*15)
            img.putpixel((x, y), (rv, gv, bv, 255))

# White ring
for y in range(SIZE):
    for x in range(SIZE):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if r-4 <= dist <= r:
            img.putpixel((x, y), (255,255,255,180))

# Inner glow
ir = r - 130
for y in range(SIZE):
    for x in range(SIZE):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist <= ir:
            ratio = dist / ir
            a = int(25 * (1 - ratio))
            img.putpixel((x, y), (255,255,255,a))

# Fonts
font_paths = ["C:/Windows/Fonts/msyhbd.ttf","C:/Windows/Fonts/msyh.ttc","C:/Windows/Fonts/simhei.ttf"]
def load_font(size):
    for fp in font_paths:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

font_main = load_font(580)
font_top = load_font(180)

# "榜"
text = "榜"
bbox = draw.textbbox((0,0), text, font=font_main)
tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
tx, ty = cx-tw//2, cy-th//2 - 40
draw.text((tx+5,ty+5), text, font=font_main, fill=(0,0,0,80))
draw.text((tx,ty), text, font=font_main, fill=(255,245,215,255))
draw.text((tx,ty-2), text, font=font_main, fill=(255,255,250,100))

# "看金"
text_top = "看金"
bbox2 = draw.textbbox((0,0), text_top, font=font_top)
tw2, th2 = bbox2[2]-bbox2[0], bbox2[3]-bbox2[1]
tx2, ty2 = cx-tw2//2, ty-200
draw.text((tx2+3,ty2+3), text_top, font=font_top, fill=(0,0,0,60))
draw.text((tx2,ty2), text_top, font=font_top, fill=(255,220,100,255))

# Decorative dots
for dy_pos in [60, SIZE-80]:
    for i in range(5):
        dx = (i-2)*90
        px, py = cx+dx, dy_pos
        for d2y in range(-8,9):
            for d2x in range(-8,9):
                if d2x*d2x+d2y*d2y <= 64:
                    pp = (px+d2x, py+d2y)
                    if 0<=pp[0]<SIZE and 0<=pp[1]<SIZE:
                        img.putpixel(pp, (255,225,120,160))

# Sparkles
random.seed(7)
for _ in range(20):
    a = random.uniform(0.3, 2.8)
    d = random.uniform(ir+10, r-150)
    sx = int(cx + d*math.cos(a))
    sy = int(cy + d*math.sin(a))
    for dr in range(-4,5):
        for dc in range(-4,5):
            if abs(dr)+abs(dc)<=4:
                px, py = sx+dc, sy+dr
                if 0<=px<SIZE and 0<=py<SIZE:
                    if math.sqrt((px-cx)**2+(py-cy)**2)<=r:
                        img.putpixel((px,py), (255,255,240,180))

img.save(OUT, "PNG")
print(f"HD Icon: {OUT} ({os.path.getsize(OUT)} bytes, {SIZE}x{SIZE})")
