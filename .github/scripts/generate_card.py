#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepAI + Pillow vocabulary image generator
-------------------------------------------
Features:
- Calls DeepAI Text2Img for background
- Adds branded text overlay (word, meaning, example)
- Automatic overflow prevention & font scaling
- Computes legibility score (0–100)
- Saves metadata (.meta/<index>_<concept>.json)
"""

import os, re, io, json, argparse, requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ========== Utility ==========

def slug(s):
    s = s.lower().strip()
    s = re.sub(r"\s+", "-", s)
    return re.sub(r"[^a-z0-9\-_]", "", s) or "concept"

def font_try(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

# ========== DeepAI API ==========

def deepai_bg(api_key, example):
    """Generate a background image with DeepAI Text2Img"""
    resp = requests.post(
        "https://api.deepai.org/api/text2img",
        headers={"api-key": api_key},
        data={
            "text": (
                "Create a cinematic illustration that reflects the interaction "
                "between the subject and the object in the following sentence. "
                "No text, logo, or watermark. Balanced lighting, detailed background. "
                f"Sentence: '{example}'"
            )
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    url = data.get("output_url") or data.get("id")
    if not url:
        raise RuntimeError(f"DeepAI response missing output URL: {data}")
    img = requests.get(url, timeout=120)
    img.raise_for_status()
    return Image.open(io.BytesIO(img.content)).convert("RGBA")

# ========== Layout Helpers ==========

def wrap_text(text, font, max_w, draw):
    """Wrap text to fit width."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        w_width = draw.textbbox((0, 0), test, font=font)[2]
        if w_width <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def text_block_height(lines, font, draw):
    if not lines:
        return 0
    return sum(draw.textbbox((0, 0), l, font=font)[3] for l in lines) + 6 * (len(lines) - 1)

def fit_text_blocks(draw, W, H, word, meaning, example, fonts):
    """Auto-scale fonts to avoid overflow."""
    word_font, mean_font, ex_font = fonts
    scale = 1.0
    for _ in range(8):
        f1 = word_font.font_variant(size=int(word_font.size * scale))
        f2 = mean_font.font_variant(size=int(mean_font.size * scale))
        f3 = ex_font.font_variant(size=int(ex_font.size * scale))
        wrap_w = int(W * 0.88)
        w_lines = wrap_text(word, f1, wrap_w, draw)
        m_lines = wrap_text(meaning, f2, wrap_w, draw)
        e_lines = wrap_text(example, f3, wrap_w, draw)
        total_h = (
            text_block_height(w_lines, f1, draw)
            + text_block_height(m_lines, f2, draw)
            + text_block_height(e_lines, f3, draw)
            + 200
        )
        if total_h <= H * 0.9:
            return scale, (w_lines, f1), (m_lines, f2), (e_lines, f3)
        scale *= 0.9
    return scale, (w_lines, f1), (m_lines, f2), (e_lines, f3)

def compute_legibility_score(draw, W, H, blocks):
    used_h = sum(b["height"] for b in blocks)
    margin = H - used_h
    base = 100 * max(0, min(1, margin / (H * 0.1)))
    penalties = sum(10 for b in blocks if b.get("overflow"))
    return max(0, int(base - penalties))

# ========== Overlay ==========

def overlay_image(img, word, meaning, example, size=(512, 512)):
    W, H = size
    im = img.resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.1)
    im = ImageEnhance.Color(im).enhance(1.05)
    draw = ImageDraw.Draw(im)

    font_b = font_try(
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
        max(W // 12, 36),
    )
    font_r = font_try(
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"],
        max(W // 18, 24),
    )
    font_i = font_try(
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", "C:/Windows/Fonts/ariali.ttf"],
        max(W // 24, 20),
    )

    scale, (wl, f1), (ml, f2), (el, f3) = fit_text_blocks(draw, W, H, word, meaning, example, (font_b, font_r, font_i))
    max_w = int(W * 0.88)
    block_info = []

    def band(y, h):
        o = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(o).rectangle([int(W * 0.06), y, int(W * 0.94), y + h], fill=(0, 0, 0, 140))
        im.alpha_composite(o)

    def draw_block(lines, font, y, align="center"):
        yy = y
        for t in lines:
            w = draw.textbbox((0, 0), t, font=font)[2]
            h = draw.textbbox((0, 0), t, font=font)[3]
            if align == "center":
                x = (W - w) // 2
            else:
                x = int(W * 0.06)
            draw.text((x + 1, yy + 1), t, font=font, fill=(0, 0, 0, 180))
            draw.text((x, yy), t, font=font, fill=(255, 255, 255, 255))
            yy += h + 6
        return yy

    # --- Placement ---
    y = int(H * 0.12)
    bh1 = text_block_height(wl, f1, draw)
    band(y - 10, bh1 + 20)
    y = draw_block(wl, f1, y)
    block_info.append({"height": bh1, "overflow": False})

    bh2 = text_block_height(ml, f2, draw)
    band(y - 6, bh2 + 20)
    y = draw_block(ml, f2, y + 6)
    block_info.append({"height": bh2, "overflow": False})

    ex_top = int(H * 0.72)
    bh3 = text_block_height(el, f3, draw)
    band(ex_top - 10, bh3 + 20)
    draw_block(el, f3, ex_top, align="left")
    block_info.append({"height": bh3, "overflow": bh3 > H * 0.3})

    score = compute_legibility_score(draw, W, H, block_info)
    return im.convert("RGB"), score

# ========== Main ==========

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--word", required=True)
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--concept", required=True)
    ap.add_argument("--meaning", required=True)
    ap.add_argument("--example", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    bg = deepai_bg(args.api_key, args.example)
    img, score = overlay_image(bg, args.word, args.meaning, args.example)

    safe_concept = slug(args.concept)
    outpath = os.path.join(args.outdir, f"{args.index}_{safe_concept}.jpg")
    img.save(outpath, "JPEG", quality=95)

    # --- Meta save ---
    meta_dir = os.path.join(args.outdir, ".meta")
    os.makedirs(meta_dir, exist_ok=True)
    meta_path = os.path.join(meta_dir, f"{args.index}_{safe_concept}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "index": args.index,
                "concept": safe_concept,
                "meaning": args.meaning,
                "example": args.example,
                "score": score,
                "status": "✅ good" if score >= 80 else "⚠️ overflow",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"✅ saved: {outpath} | legibility={score}")

if __name__ == "__main__":
    main()
