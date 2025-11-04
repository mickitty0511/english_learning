# --- 置換: DeepAI部分をDashScopeに変更 ---

import time
import requests

DASHSCOPE_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"  # Singapore
T2I_ENDPOINT = f"{DASHSCOPE_BASE}/services/aigc/text2image/image-synthesis"
TASK_ENDPOINT = f"{DASHSCOPE_BASE}/tasks"

def _dashscope_headers(api_key: str, async_required: bool = True):
    h = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if async_required:
        h["X-DashScope-Async"] = "enable"
    return h

def dashscope_bg(api_key: str, prompt: str, model: str = "qwen-image-plus",
                 size: str = "1024*1024", n: int = 1,
                 negative_prompt: str | None = None, poll_interval: float = 5.0, timeout_sec: int = 180):
    """
    画像生成（非同期）：タスク作成→task_idでポーリング→画像URL→PIL.Image
    """
    payload = {
        "model": model,  # 例: "qwen-image-plus" / Wan系なら "wan2.2-t2i-flash" など
        "input": {"prompt": prompt},
        "parameters": {"size": size, "n": n}
    }
    if negative_prompt:
        payload["input"]["negative_prompt"] = negative_prompt

    # Step1: create task
    r = requests.post(T2I_ENDPOINT, headers=_dashscope_headers(api_key, async_required=True),
                      json=payload, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"DashScope create-task error {r.status_code}: {r.text}")
    data = r.json()
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"DashScope response missing task_id: {data}")

    # Step2: poll task result
    deadline = time.time() + timeout_sec
    last_status = None
    while time.time() < deadline:
        g = requests.get(f"{TASK_ENDPOINT}/{task_id}",
                         headers=_dashscope_headers(api_key, async_required=False),
                         timeout=60)
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
            # ダウンロード
            img_resp = requests.get(url, timeout=120)
            img_resp.raise_for_status()
            from PIL import Image
            import io
            return Image.open(io.BytesIO(img_resp.content)).convert("RGBA")
        if status in ("FAILED", "CANCELED"):
            code = out.get("code")
            msg = out.get("message")
            raise RuntimeError(f"DashScope failed: {code} {msg}")
        time.sleep(poll_interval)

    raise TimeoutError(f"DashScope timeout waiting for task: {task_id}")

# ---- 既存 main() 内の呼び出し置換 ----
# bg = deepai_bg(args.api_key, args.example)
# ↓
# プロンプトは “動作×対象物の相互作用 + 例文” を重視（あなたの方針を反映）
bg = dashscope_bg(
    args.api_key,
    prompt=(
        "Cinematic illustration that reflects the interaction between subject and object in the sentence. "
        "No text. Balanced lighting. Detailed, realistic background. "
        f"Sentence: '{args.example}'"
    ),
    model="qwen-image-plus",      # 同期が必要ならQwen-Image。速度重視は wan2.2/2.5 に差替え可
    size="1024*1024",
    n=1,
    negative_prompt=None          # 人物回避等が必要なら 'people' などを入れる
)

def main():
    import argparse, os, json
    from PIL import Image

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

    # DeepAI呼び出しは削除し、DashScopeをここで呼ぶ
    bg = dashscope_bg(
        args.api_key,
        prompt=(
            "Cinematic illustration that reflects the interaction between subject and object in the sentence. "
            "No text. Balanced lighting. Detailed, realistic background. "
            f"Sentence: '{args.example}'"
        ),
        model="qwen-image-plus",
        size="1024*1024",
        n=1,
        negative_prompt=None
    )

    # 既存のオーバーレイ関数を呼ぶ（あなたのファイルにあるものを使用）
    img, score = overlay_image(bg, args.word, args.meaning, args.example, tuple(args.input_size))

    # 保存名は既存仕様に合わせて
    def slug(s):
        import re
        s = s.lower().strip()
        s = re.sub(r"\s+", "-", s)
        return re.sub(r"[^a-z0-9\-_]", "", s) or "concept"

    safe_concept = slug(args.concept)
    outpath = os.path.join(args.outdir, f"{args.index}_{safe_concept}.jpg")
    img.save(outpath, "JPEG", quality=95)

    # メタ情報（既存の書き方に合わせて）
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