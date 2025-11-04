import os, csv, json, argparse

p = argparse.ArgumentParser()
p.add_argument("--word", required=True)
p.add_argument("--slug", required=True)
args = p.parse_args()

meta_dir = f"src/{args.slug}/.meta"
report_dir = "reports/layout_scores"
os.makedirs(report_dir, exist_ok=True)
out_path = os.path.join(report_dir, f"{args.slug}.csv")

rows = []
if os.path.exists(meta_dir):
    for f in sorted(os.listdir(meta_dir)):
        if not f.endswith(".json"):
            continue
        data = json.load(open(os.path.join(meta_dir, f)))
        rows.append([
            data["index"],
            data["concept"],
            data.get("score", ""),
            data.get("status", ""),
            f"{data['index']}_{data['concept']}.jpg",
        ])

with open(out_path, "w", newline="", encoding="utf-8") as fw:
    writer = csv.writer(fw)
    writer.writerow(["index", "concept", "score", "status", "image"])
    writer.writerows(rows)

print(f"✅ report saved: {out_path}")
