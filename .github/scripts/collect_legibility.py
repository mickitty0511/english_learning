import argparse
import csv
import json
import os
import sys


def load_rows(meta_dir: str) -> list[dict]:
    rows: list[dict] = []
    if not os.path.isdir(meta_dir):
        return rows

    for filename in sorted(os.listdir(meta_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(meta_dir, filename)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)

        index = int(data.get("index", 0))
        concept = str(data.get("concept", ""))
        rows.append(
            {
                "index": index,
                "concept": concept,
                "score": data.get("score", ""),
                "status": data.get("status", ""),
                "image": f"{index}_{concept}.jpg",
            }
        )

    rows.sort(key=lambda row: row["index"])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--word")
    parser.add_argument("--slug")
    args = parser.parse_args()

    word = (
        args.word
        or os.environ.get("WORD_DISPLAY")
        or os.environ.get("WORD")
        or ""
    )
    slug = (
        args.slug
        or os.environ.get("WORD_SLUG")
        or os.environ.get("SLUG")
        or ""
    )

    if not word or not slug:
        raise SystemExit("missing --word/--slug (and no env fallback)")

    meta_dir = os.path.join("src", slug, ".meta")
    report_dir = os.path.join("reports", "layout_scores")
    os.makedirs(report_dir, exist_ok=True)
    csv_path = os.path.join(report_dir, f"{slug}.csv")

    rows = load_rows(meta_dir)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "concept", "score", "status", "image"])
        for row in rows:
            writer.writerow(
                [
                    row["index"],
                    row["concept"],
                    row["score"],
                    row["status"],
                    row["image"],
                ]
            )

    # Emit JSON to stdout so the workflow step can capture it, and log to stderr.
    json.dump(rows, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    print(f"report saved: {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
