"""
Compose the Open Graph / iMessage link preview image.

The helmet source is portrait (328x1000). Open Graph previews are landscape
(1200x630, 1.91:1) — cropping a slab out of the source would decapitate the
helmet, so the image is COMPOSED instead:

  - 1200x630 black canvas matching the site background (#000 / --coal #0A0A0C)
  - helmet placed on the left, scaled to full bleed height, feathered on its
    right edge so it dissolves into the canvas with no hard seam
  - purple aura bloom behind the helmet edge, matching the landing page --purple
  - title type on the right in Anton (same as the site headline)
  - a subtle vignette + film grain so it reads like the site, not a slide

Also produces:
  - og-square.png  1200x1200 for WhatsApp / some Slack unfurls
  - favicon set    32/180 from the helmet eye region
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import random
import os

SRC = "/home/ubuntu/joinlegion/assets/armorfigure.png"
OUT_DIR = "/home/ubuntu/joinlegion/assets"
FONTS = "/home/ubuntu/legion_audit/fonts"

# Brand tokens lifted from index.html :root
PURPLE = (153, 51, 255)
PURPLE2 = (138, 43, 226)
PURPLE3 = (192, 132, 252)
DUST = (185, 168, 224)
METAL = (224, 224, 224)
COAL = (10, 10, 12)

W, H = 1200, 630


def load_font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def feather_right(img, fade_px):
    """Fade the right edge of an RGBA image to transparent."""
    a = img.split()[3]
    grad = Image.new("L", (img.width, 1), 255)
    gp = grad.load()
    start = img.width - fade_px
    for x in range(img.width):
        if x >= start:
            t = (x - start) / max(1, fade_px)
            # ease-out so the dissolve is soft rather than linear
            gp[x, 0] = int(255 * (1 - t) ** 1.6)
    grad = grad.resize((img.width, img.height))
    img.putalpha(ImageChops.multiply(a, grad))
    return img


def grain(size, amount=9):
    n = Image.new("L", (size[0] // 2, size[1] // 2))
    px = n.load()
    for y in range(n.height):
        for x in range(n.width):
            px[x, y] = random.randint(0, amount)
    return n.resize(size, Image.BILINEAR)


def build_og(title_lines, sub, out_name, size=(W, H), helmet_frac=0.46):
    cw, ch = size
    canvas = Image.new("RGB", (cw, ch), COAL)

    # ---- helmet ----------------------------------------------------------
    helmet = Image.open(SRC).convert("RGBA")
    # scale so height fills the canvas with a little overshoot for bleed.
    # 1.28 crops slightly into crown and chin but renders the helmet large
    # enough to be recognisable at iMessage thumbnail size.
    target_h = int(ch * 1.28)
    scale = target_h / helmet.height
    hw = int(helmet.width * scale)
    helmet = helmet.resize((hw, target_h), Image.LANCZOS)

    # crop the helmet to the region we want on the left of the canvas
    want_w = int(cw * helmet_frac)
    if hw > want_w:
        # keep the left side (crown + eye), drop the smoky right tail
        helmet = helmet.crop((0, 0, want_w, target_h))
    hw = helmet.width

    helmet = feather_right(helmet, int(hw * 0.42))

    # ---- purple bloom behind the helmet edge ------------------------------
    bloom = Image.new("RGB", (cw, ch), (0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    # main glow roughly where the eye sits
    ex, ey = int(hw * 0.42), int(ch * 0.50)
    bd.ellipse([ex - 190, ey - 190, ex + 190, ey + 190], fill=(70, 20, 130))
    # secondary rim light down the helmet edge
    bd.ellipse([hw - 120, int(ch * 0.20), hw + 240, int(ch * 0.95)],
               fill=(46, 12, 92))
    bloom = bloom.filter(ImageFilter.GaussianBlur(120))
    canvas = ImageChops.add(canvas, bloom)

    canvas.paste(helmet, (0, int((ch - target_h) / 2)), helmet)

    # ---- type ------------------------------------------------------------
    d = ImageDraw.Draw(canvas)
    text_x = int(cw * 0.47)
    avail = cw - text_x - 70

    # eyebrow
    eb = load_font("Oswald.ttf", 25)
    d.text((text_x, int(ch * 0.20)), "L E G I O N   A I", font=eb, fill=PURPLE3)

    # headline in Anton, auto-fit to the available width
    size_px = 96
    while size_px > 40:
        f = load_font("Anton.ttf", size_px)
        widest = max(d.textlength(l, font=f) for l in title_lines)
        if widest <= avail:
            break
        size_px -= 2
    f = load_font("Anton.ttf", size_px)

    line_h = int(size_px * 1.06)
    total_h = line_h * len(title_lines)
    ty = int(ch * 0.30)

    for i, line in enumerate(title_lines):
        y = ty + i * line_h
        # soft purple glow under the type so it lifts off the black
        glow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.text((text_x, y), line, font=f, fill=(153, 51, 255, 130))
        glow = glow.filter(ImageFilter.GaussianBlur(18))
        canvas.paste(Image.alpha_composite(
            canvas.convert("RGBA"), glow).convert("RGB"), (0, 0))
        d = ImageDraw.Draw(canvas)
        # the last line takes the light purple accent, matching --numgrad
        fill = METAL if i < len(title_lines) - 1 else PURPLE3
        d.text((text_x, y), line, font=f, fill=fill)

    # gradient rule
    ry = ty + total_h + 26
    for i in range(avail):
        t = i / avail
        if t < 0.75:
            a = int(190 * (1 - t / 0.75))
            c = (int(PURPLE[0] * a / 190), int(PURPLE[1] * a / 190),
                 int(PURPLE[2] * a / 190))
            d.line([(text_x + i, ry), (text_x + i, ry + 2)], fill=c)

    # subline — wrap to the available width so it never runs off the canvas
    sf = load_font("Inter.ttf", 26)
    words = sub.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=sf) <= avail:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    for i, line in enumerate(lines):
        d.text((text_x, ry + 24 + i * 34), line, font=sf, fill=DUST)

    # domain, bottom right
    df = load_font("Oswald.ttf", 23)
    dw = d.textlength("joinlegion.ai", font=df)
    d.text((cw - 70 - dw, ch - 62), "joinlegion.ai", font=df, fill=(140, 130, 160))

    # ---- vignette + grain -------------------------------------------------
    vig = Image.new("L", (cw, ch), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-int(cw * 0.25), -int(ch * 0.45),
                int(cw * 1.25), int(ch * 1.45)], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(180))
    black = Image.new("RGB", (cw, ch), (0, 0, 0))
    canvas = Image.composite(canvas, black, vig.point(lambda v: 60 + v * 0.77 // 1))

    g = grain((cw, ch), amount=10).convert("RGB")
    canvas = ImageChops.add(canvas, g)

    out = os.path.join(OUT_DIR, out_name)
    # JPEG, not PNG: these are photographic and PNG lands at ~600KB-1.3MB, which
    # some scrapers refuse to fetch. Facebook recommends staying under 8MB but
    # iMessage in particular is happier with small files, and quality 88 is
    # visually indistinguishable here.
    canvas.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"  wrote {out}  {canvas.size}  {os.path.getsize(out)//1024} KB")
    return canvas


if __name__ == "__main__":
    random.seed(7)

    print("building link preview images...")

    # Primary 1200x630 landscape card (iMessage, Facebook, LinkedIn, Slack, X)
    build_og(
        ["THE POWER OF", "AI UNLEASHED"],
        "Find the role running your day. Then deploy what covers it.",
        "og-legion.jpg",
        size=(1200, 630),
        helmet_frac=0.46,
    )

    # Square variant for WhatsApp and some Slack unfurls
    build_og(
        ["THE POWER", "OF AI", "UNLEASHED"],
        "Find the role running your day.",
        "og-legion-square.jpg",
        size=(1200, 1200),
        helmet_frac=0.44,
    )

    # ---- favicons from the helmet eye ------------------------------------
    src = Image.open(SRC).convert("RGB")
    # the eye sits around 52% down, 35% across in the cropped asset
    cx, cy = int(src.width * 0.34), int(src.height * 0.52)
    half = 150
    eye = src.crop((max(0, cx - half), max(0, cy - half),
                    min(src.width, cx + half), min(src.height, cy + half)))
    for px in (32, 180, 512):
        ic = eye.resize((px, px), Image.LANCZOS)
        name = f"icon-{px}.png"
        ic.save(os.path.join(OUT_DIR, name), "PNG", optimize=True)
        print(f"  wrote {name}")

    print("done")
