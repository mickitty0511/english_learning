#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_card.py
DashScope(Alibaba Cloud Model Studio) で背景画像を生成し、
Pillowでブランド統一のテキストオーバーレイを行い、
視認性スコアを算出して画像とメタ情報を保存します。

Usage (from GitHub Actions):
python3 .github/scripts/generate_card.py \
  --api-key "$DASHSCOPE_API_KEY" \
  --word "buy" \
  --index 1 \
  --concept "purchase" \
  --meaning "take mainly by using money" \
  --example "he buys milk" \
  --outdir "src/buy"
"""

import os
import re
import io
import json
import time
import argparse
import requests
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# =========================
# Utilities
# =========================

# 生成サイズのホワイトリスト（DashScopeの許可値）
ALLOWED_SIZES = ["1664*928","1472*1140","1328*1328","1140*1472","928*1664"]

# 横長が良ければ pick_size_by_ratio(1.3)、縦長なら pick_size_by_ratio(0.7) などに変えるだけです。
# 厳密に指定したい場合は、size="1472*1140" のように ALLOWED_SIZES のいずれかを直指定してもOK。
def pick_size_by_ratio(target_ratio: float = 1.0) -> str:
    # 目的の縦横比(=W/H)に最も近い許可サイズを選ぶ。デフォルトは正方形。
    def ratio(s):
        w, h = map(int, s.split("*"))
        return w / h
    return min(ALLOWED_SIZES, key=lambda s: abs(ratio(s) - target_ratio))


def slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", "-", s)
    return re.sub(r"[^a-z0-9\-_]", "", s) or "concept"

def font_try(paths: List[str], size: int) -> ImageFont.FreeTypeFont:
    """Try multiple font paths; fallback to default."""
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    # Fallback
    return ImageFont.load_default()

# =========================
# DashScope (Text-to-Image)
# =========================

DASHSCOPE_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"  # International region
T2I_ENDPOINT   = f"{DASHSCOPE_BASE}/services/aigc/text2image/image-synthesis"
TASK_ENDPOINT  = f"{DASHSCOPE_BASE}/tasks"

def _dashscope_headers(api_key: str, async_required: bool = True) -> dict:
    h = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if async_required:
        h["X-DashScope-Async"] = "enable"
    return h

def dashscope_bg(
    api_key: str,
    prompt: str,
    model: str = "qwen-image-plus",
    size: str = pick_size_by_ratio(1.3),
    n: int = 1,
    negative_prompt: str | None = None,
    poll_interval: float = 5.0,
    timeout_sec: int = 180
) -> Image.Image:
    """
    非同期API：タスク作成→task_idでポーリング→結果URLから画像取得
    """
    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"size": size, "n": n}
    }
    if negative_prompt:
        payload["input"]["negative_prompt"] = negative_prompt

    # Create task
    r = requests.post(
        T2I_ENDPOINT,
        headers=_dashscope_headers(api_key, async_required=True),
        json=payload,
        timeout=120
    )
    if r.status_code >= 400:
        raise RuntimeError(f"DashScope create-task error {r.status_code}: {r.text}")
    data = r.json()
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"DashScope response missing task_id: {data}")

    # Poll task
    deadline = time.time() + timeout_sec
    last_status = None
    while time.time() < deadline:
        g = requests.get(
            f"{TASK_ENDPOINT}/{task_id}",
            headers=_dashscope_headers(api_key, async_required=False),
            timeout=60
        )
        if g.status_code >= 400:
            raise RuntimeError(f"DashScope get-task error {g.status_code}: {g.text}")

        j = g.json()
        out = j.get("output") or {}
        status = out.get("task_status")
        if status != last_status:
            print(f"[DashScope] task {task_id} status: {status}")
            last_status = status

        if status == "SUCCEEDED":
            results = out.get("results") or []
            if not results:
                raise RuntimeError(f"DashScope SUCCEEDED but no results: {j}")
            url = results[0].get("url")
            if not url:
                raise RuntimeError(f"DashScope result missing url: {j}")

            img_resp = requests.get(url, timeout=120)
            img_resp.raise_for_status()
            return Image.open(io.BytesIO(img_resp.content)).convert("RGBA")

        if status in ("FAILED", "CANCELED"):
            code = out.get("code")
            msg  = out.get("message")
            raise RuntimeError(f"DashScope failed: {code} {msg}")

        time.sleep(poll_interval)

    raise TimeoutError(f"DashScope timeout waiting for task: {task_id}")

# =========================
# Text layout helpers
# =========================

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Simple greedy wrap by words"""
    words = text.split()
    lines: List[str] = []
    cur = ""
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

def text_block_height(lines: List[str], font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw) -> int:
    if not lines:
        return 0
    return sum(draw.textbbox((0, 0), l, font=font)[3] for l in lines) + 6 * (len(lines) - 1)

def fit_text_blocks(
    draw: ImageDraw.ImageDraw,
    W: int,
    H: int,
    word: str,
    meaning: str,
    example: str,
    fonts: Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]
):
    """
    オーバーフロー防止のためフォントを段階的に縮小して3ブロックを収める
    """
    word_font, mean_font, ex_font = fonts
    scale = 1.0
    for _ in range(8):
        f1 = word_font.font_variant(size=max(12, int(word_font.size * scale)))
        f2 = mean_font.font_variant(size=max(10, int(mean_font.size * scale)))
        f3 = ex_font.font_variant(size=max(10, int(ex_font.size * scale)))

        wrap_w = int(W * 0.88)
        w_lines = wrap_text(word,    f1, wrap_w, draw)
        m_lines = wrap_text(meaning, f2, wrap_w, draw)
        e_lines = wrap_text(example, f3, wrap_w, draw)

        total_h = (
            text_block_height(w_lines, f1, draw) +
            text_block_height(m_lines, f2, draw) +
            text_block_height(e_lines, f3, draw) + 200  # margin budget
        )
        if total_h <= int(H * 0.9):
            return scale, (w_lines, f1), (m_lines, f2), (e_lines, f3)
        scale *= 0.9

    # Last try (might overflow slightly)
    return scale, (w_lines, f1), (m_lines, f2), (e_lines, f3)

def compute_legibility_score(draw: ImageDraw.ImageDraw, W: int, H: int, blocks: List[dict]) -> int:
    """
    余白率とオーバーフロー有無から0–100のスコアを算出
    """
    used_h = sum(b["height"] for b in blocks)
    margin = H - used_h
    base = 100 * max(0, min(1, margin / (H * 0.1)))  # 余白がHの10%なら満点
    penalties = sum(10 for b in blocks if b.get("overflow"))
    return max(0, int(base - penalties))

# =========================
# Overlay renderer
# =========================

def overlay_image(
    bg: Image.Image,
    word: str,
    meaning: str,
    example: str,
    size: Tuple[int, int] = (512, 512)
) -> Tuple[Image.Image, int]:
    W, H = size
    im = bg.resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.1)
    im = ImageEnhance.Color(im).enhance(1.05)
    draw = ImageDraw.Draw(im)

    # Base fonts (will be scaled)
    font_b = font_try(
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
        max(W // 12, 36)
    )
    font_r = font_try(
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"],
        max(W // 18, 24)
    )
    font_i = font_try(
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", "C:/Windows/Fonts/ariali.ttf"],
        max(W // 24, 20)
    )

    scale, (wl, f1), (ml, f2), (el, f3) = fit_text_blocks(draw, W, H, word, meaning, example, (font_b, font_r, font_i))

    def band(y: int, h: int):
        o = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(o).rectangle([int(W * 0.06), y, int(W * 0.94), y + h], fill=(0, 0, 0, 140))
        im.alpha_composite(o)

    def draw_block(lines: List[str], font: ImageFont.FreeTypeFont, y: int, align: str = "center") -> int:
        yy = y
        for t in lines:
            w = draw.textbbox((0, 0), t, font=font)[2]
            h = draw.textbbox((0, 0), t, font=font)[3]
            x = (W - w) // 2 if align == "center" else int(W * 0.06)
            # subtle shadow
            draw.text((x + 1, yy + 1), t, font=font, fill=(0, 0, 0, 180))
            draw.text((x, yy), t, font=font, fill=(255, 255, 255, 255))
            yy += h + 6
        return yy

    # Layout
    max_w = int(W * 0.88)
    bh1 = text_block_height(wl, f1, draw)
    y = int(H * 0.12)
    band(y - 10, bh1 + 20)
    y = draw_block(wl, f1, y, align="center")

    bh2 = text_block_height(ml, f2, draw)
    band(y - 6, bh2 + 20)
    y = draw_block(ml, f2, y + 6, align="center")

    ex_top = int(H * 0.72)
    bh3 = text_block_height(el, f3, draw)
    band(ex_top - 10, bh3 + 20)
    draw_block(el, f3, ex_top, align="left")

    # Score (mark overflow if example block too tall)
    blocks = [
        {"height": bh1, "overflow": False},
        {"height": bh2, "overflow": False},
        {"height": bh3, "overflow": bh3 > H * 0.3},
    ]
    score = compute_legibility_score(draw, W, H, blocks)
    return im.convert("RGB"), score

# =========================
# Main
# =========================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--word", required=True)
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--concept", required=True)
    ap.add_argument("--meaning", required=True)
    ap.add_argument("--example", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--input-size", nargs=2, type=int, default=[512, 512])
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # 画像生成（DashScope 非同期）
    prompt = (
        "Cinematic illustration that reflects the interaction between subject and object in the sentence. "
        "No text. Balanced lighting. Detailed, realistic background. "
        f"Sentence: '{args.example}'"
    )
    bg = dashscope_bg(
        api_key=args.api_key,
        prompt=prompt,
        model="qwen-image-plus",
        size="1024*1024",
        n=1,
        negative_prompt=None
    )

    # オーバーレイ + スコア
    img, score = overlay_image(
        bg,
        word=args.word,
        meaning=args.meaning,
        example=args.example,
        size=tuple(args.input_size)
    )

    safe_concept = slug(args.concept)
    outpath = os.path.join(args.outdir, f"{args.index}_{safe_concept}.jpg")
    img.save(outpath, "JPEG", quality=95)

    # メタ保存（.meta/<index>_<concept>.json）
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
