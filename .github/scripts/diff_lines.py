import json, os, re, sys, shutil, datetime

event = json.loads(sys.argv[1])
word_display = event.get("issue", {}).get("title", "").strip()

new_body = event["issue"]["body"] or ""
old_body = (event.get("changes", {}) or {}).get("body", {}).get("from", "")

LINE_RE = re.compile(r"^\s*(\d+)\.\s*([^,|]+)[,|]\s*([^,|]+)[,|]\s*(.+)$")

def parse_lines(block: str):
    out = {}
    for raw in block.splitlines():
        s = raw.strip()
        if not s:
            continue
        m = LINE_RE.match(s)
        if not m:
            continue
        idx = int(m.group(1))
        concept, meaning, example = [m.group(i).strip() for i in range(2, 5)]
        out[idx] = (concept, meaning, example)
    return out

def slugify(s):
    s = s.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-_]", "", s)
    return s or "word"

def extract_section(body):
    return body

new_map = parse_lines(extract_section(new_body))
old_map = parse_lines(extract_section(old_body))

changed, removed = [], []

for idx, tup in new_map.items():
    if idx not in old_map or old_map[idx] != tup:
        changed.append(idx)

for idx in old_map:
    if idx not in new_map:
        removed.append(idx)

word_slug = slugify(word_display)

# 削除画像アーカイブ
if removed and word_slug:
    arch_dir = os.path.join("src", word_slug, ".archive", datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(arch_dir, exist_ok=True)
    for idx in removed:
        old_c = old_map[idx][0]
        fname = f"{idx}_{old_c}.jpg"
        src = os.path.join("src", word_slug, fname)
        if os.path.exists(src):
            shutil.move(src, os.path.join(arch_dir, fname))
            print(f"archived {src} → {arch_dir}/")

# 出力
with open(os.environ["GITHUB_OUTPUT"], "a") as o:
    o.write(f"word_display={word_display}\n")
    o.write(f"word_slug={word_slug}\n")
    o.write(f"changed_indices={','.join(map(str, changed))}\n")

for idx in changed:
    c, m, e = new_map[idx]
    with open(os.environ["GITHUB_ENV"], "a") as env:
        env.write(f"CONCEPT_{idx}={c}\n")
        env.write(f"MEANING_{idx}={m}\n")
        env.write(f"EXAMPLE_{idx}={e}\n")
