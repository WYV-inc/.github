"""Compose Wyven GitHub org hero banner from brand assets."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ASSETS = Path(__file__).resolve().parent
BG_CANDIDATES = [
    ASSETS / "hero-bg.jpg",
    Path(
        r"C:\Users\JJ\.cursor\projects\c-Users-JJ-Documents-GitHub-Wyven\assets\wyven-hero-bg-clean.jpg"
    ),
]
LOGO_CANDIDATES = [
    ASSETS / "wyven-dragon-source.png",
    Path(r"C:\Users\JJ\Documents\GitHub\Wyven\public\images\wyven-logo.png"),
]

NEAR_BLACK = (7, 11, 15)
DEEP_NAVY = (3, 29, 46)
OCEAN = (6, 59, 92)
ACCENT = (10, 132, 198)
SOFT = (220, 239, 248)
WHITE = (255, 255, 255)

W, H = 1280, 520


def load_font(names: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(paths)


def clean_silhouette(logo: Image.Image) -> Image.Image:
    """Threshold the original mark into a crisp transparent silhouette."""
    src = logo.convert("RGBA")
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    sp = src.load()
    op = out.load()
    assert sp is not None and op is not None
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = sp[x, y]
            lum = (r + g + b) / 3
            if lum < 160 and a > 20:
                op[x, y] = (255, 255, 255, 255)
            else:
                op[x, y] = (0, 0, 0, 0)

    # Drop accidental full-height edge stripes from palette PNGs.
    for x in range(out.width):
        opaque = sum(1 for y in range(out.height) if op[x, y][3] > 200)
        if opaque >= out.height - 2:
            for y in range(out.height):
                op[x, y] = (0, 0, 0, 0)

    bbox = out.getbbox()
    if not bbox:
        return out
    pad = 12
    cropped = out.crop(
        (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(out.width, bbox[2] + pad),
            min(out.height, bbox[3] + pad),
        )
    )
    side = max(cropped.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(
        cropped,
        ((side - cropped.width) // 2, (side - cropped.height) // 2),
        cropped,
    )
    return square


def as_dark_mark(white: Image.Image) -> Image.Image:
    dark = Image.new("RGBA", white.size, (0, 0, 0, 0))
    wp = white.load()
    dp = dark.load()
    assert wp is not None and dp is not None
    for y in range(white.height):
        for x in range(white.width):
            _r, _g, _b, a = wp[x, y]
            if a > 10:
                dp[x, y] = (*NEAR_BLACK, a)
    return dark


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    bg_path = first_existing(BG_CANDIDATES)
    logo_path = first_existing(LOGO_CANDIDATES)

    source = Image.open(logo_path).convert("RGBA")
    # Keep a cleaned source in-repo; avoid reintroducing palette edge stripes.
    if logo_path != ASSETS / "wyven-dragon-source.png":
        source.save(ASSETS / "wyven-dragon-source.png", optimize=True)

    white_logo = clean_silhouette(source).resize((256, 256), Image.Resampling.LANCZOS)
    dark_logo = as_dark_mark(white_logo)
    white_logo.save(ASSETS / "wyven-dragon.png", optimize=True)
    dark_logo.save(ASSETS / "wyven-dragon-mark.png", optimize=True)

    bg = Image.open(bg_path).convert("RGB")
    bw, bh = bg.size
    target_ratio = W / H
    src_ratio = bw / bh
    if src_ratio > target_ratio:
        new_w = int(bh * target_ratio)
        left = (bw - new_w) // 2
        bg = bg.crop((left, 0, left + new_w, bh))
    else:
        new_h = int(bw / target_ratio)
        top = (bh - new_h) // 3
        bg = bg.crop((0, top, bw, top + new_h))
    bg = bg.resize((W, H), Image.Resampling.LANCZOS)

    overlay = Image.new("RGB", (W, H), DEEP_NAVY)
    vignette = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vignette)
    cx, cy = W // 2, int(H * 0.42)
    for r in range(max(W, H), 0, -8):
        t = r / max(W, H)
        val = int(40 + 180 * (1 - t) ** 1.6)
        vd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=val)
    vignette = vignette.filter(ImageFilter.GaussianBlur(48))

    bg_f = Image.blend(bg, overlay, 0.35)
    edge = Image.new("RGB", (W, H), NEAR_BLACK)
    bg_f = Image.composite(bg_f, edge, vignette)

    bloom = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (x, y, radius, alpha) in enumerate(
        [
            (int(W * 0.50), int(H * 0.20), 280, 50),
            (int(W * 0.35), int(H * 0.45), 200, 30),
            (int(W * 0.65), int(H * 0.50), 200, 30),
        ]
    ):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        col = (*ACCENT, alpha) if i == 0 else (*OCEAN, alpha)
        ld.ellipse([x - radius, y - radius, x + radius, y + radius], fill=col)
        bloom = Image.alpha_composite(bloom, layer.filter(ImageFilter.GaussianBlur(80)))

    canvas = Image.alpha_composite(bg_f.convert("RGBA"), bloom)

    logo = white_logo.resize((140, 140), Image.Resampling.LANCZOS)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy = W // 2, int(H * 0.28)
    gd.ellipse([gx - 85, gy - 65, gx + 85, gy + 65], fill=(*ACCENT, 40))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(32)))

    logo_x = (W - logo.width) // 2
    logo_y = int(H * 0.12)
    canvas.paste(logo, (logo_x, logo_y), logo)

    draw = ImageDraw.Draw(canvas)
    font_brand = load_font(
        [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
        54,
    )
    font_tag = load_font(
        [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
        22,
    )
    font_sub = load_font(
        [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
        16,
    )
    font_label = load_font(
        [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
        12,
    )

    label = "WYVEN GROUP"
    bbox = draw.textbbox((0, 0), label, font=font_label)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 24), label, font=font_label, fill=ACCENT)

    brand = "WYVEN"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    ty = logo_y + logo.height + 8
    draw.text((tx, ty), brand, font=font_brand, fill=WHITE)

    ubox = draw.textbbox((tx, ty), brand, font=font_brand)
    underline_y = ubox[3] + 12
    draw.rounded_rectangle(
        [W // 2 - 28, underline_y, W // 2 + 28, underline_y + 3],
        radius=2,
        fill=ACCENT,
    )

    tag = "Building what's next, together."
    bbox = draw.textbbox((0, 0), tag, font=font_tag)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    ty = underline_y + 22
    draw.text((tx, ty), tag, font=font_tag, fill=SOFT)

    pos = "Technology group  ·  Harare  ·  Building products & ventures"
    bbox = draw.textbbox((0, 0), pos, font=font_sub)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, ty + 36), pos, font=font_sub, fill=(160, 190, 210))

    out = canvas.convert("RGB")
    out = ImageEnhance.Contrast(out).enhance(1.04)
    out = ImageEnhance.Color(out).enhance(1.05)

    png_path = ASSETS / "hero-banner.png"
    out.save(png_path, optimize=True)
    print(f"PNG {png_path} ({png_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
