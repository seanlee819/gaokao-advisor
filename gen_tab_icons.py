from PIL import Image, ImageDraw, ImageFont
import os, math

OUT_DIR = r"F:\Hermes model\gaokao_advisor\miniapp\images"
os.makedirs(OUT_DIR, exist_ok=True)

def make_tab_icon(name, icon_char, color):
    """Generate 81x81 tab bar icon"""
    SIZE = 81
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Simple circular background
    cx, cy = SIZE // 2, SIZE // 2
    r = SIZE // 2 - 4
    
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x - cx, y - cy
            if math.sqrt(dx*dx + dy*dy) <= r:
                img.putpixel((x, y), color + (255,))
    
    # Draw icon character
    font_path = None
    for fp in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        if os.path.exists(fp):
            font_path = fp
            break
    
    if font_path:
        font = ImageFont.truetype(font_path, 42)
        bbox = draw.textbbox((0, 0), icon_char, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = cx - tw // 2
        ty = cy - th // 2 - 2
        draw.text((tx, ty), icon_char, font=font, fill=(255, 255, 255, 255))
    
    path = os.path.join(OUT_DIR, name)
    img.save(path, "PNG")
    print(f"Saved: {path}")

# Tab icons
make_tab_icon("tab-search.png", "荐", (26, 115, 232))       # blue - recommend
make_tab_icon("tab-search-active.png", "荐", (16, 80, 180))  # darker blue
make_tab_icon("tab-mine.png", "我", (160, 160, 160))         # gray - profile
make_tab_icon("tab-mine-active.png", "我", (26, 115, 232))   # blue active

print("All icons generated!")
print(f"Files: {os.listdir(OUT_DIR)}")
