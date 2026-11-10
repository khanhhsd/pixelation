"""Build report/slide assets from the evaluation results and the sample images.

    python tools/make_assets.py

Reads  results/eval/metrics_per_image.csv  and  samples/*.jpg
Writes docs/assets/numbers.json  (every figure quoted in the report and slides)
       docs/assets/*.png         (crops and image grids used by the report and slides)
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from pixel_art_studio.pipeline import PipelineConfig, normalize_size, run_pipeline  # noqa: E402
from pixel_art_studio.processing import process_image  # noqa: E402

EVAL = ROOT / "results" / "eval"
OUT = ROOT / "docs" / "assets"
SAMPLES = ROOT / "samples"
P, K = 4, 16
METRICS = ("psnr", "ssim", "delta_e", "colors", "isolated_pct", "time_ms")
METHODS = (
    "nearest", "box-average", "palette", "kmeans", "ordered", "floyd-steinberg",
    "proposed", "abl-no-denoise", "abl-rgb", "abl-no-cleanup",
)


def numbers() -> dict:
    with open(EVAL / "metrics_per_image.csv", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["pixel_size"], row["colors_k"] = int(row["pixel_size"]), int(row["colors_k"])
        for metric in METRICS:
            row[metric] = float(row[metric])

    def select(method, p=P, k=K):
        return [r for r in rows if r["method"] == method and r["pixel_size"] == p and r["colors_k"] == k]

    def mean(method, metric, p=P, k=K):
        values = [r[metric] for r in select(method, p, k)]
        return round(statistics.fmean(values), 4) if values else None

    def std(method, metric):
        return round(statistics.stdev(r[metric] for r in select(method)), 4)

    proposed = {r["image"]: r for r in select("proposed")}
    palette = {r["image"]: r for r in select("palette")}
    wins = {}
    for metric, higher in (("psnr", True), ("ssim", True), ("delta_e", False), ("isolated_pct", False)):
        wins[metric] = sum(
            (proposed[i][metric] > palette[i][metric]) == higher
            and proposed[i][metric] != palette[i][metric]
            for i in proposed
        )
    return {
        "n_images": len(proposed),
        "pixel_size": P,
        "colors": K,
        "main": {m: {x: mean(m, x) for x in METRICS} for m in METHODS},
        "std": {m: {x: std(m, x) for x in METRICS} for m in METHODS},
        "wins_vs_palette": wins,
        "sweep_k": {
            m: {k: {"delta_e": mean(m, "delta_e", k=k), "isolated_pct": mean(m, "isolated_pct", k=k)} for k in (8, 16, 32, 64)}
            for m in ("palette", "kmeans", "proposed")
        },
        "sweep_p": {
            m: {p: {"ssim": mean(m, "ssim", p=p), "isolated_pct": mean(m, "isolated_pct", p=p)} for p in (2, 4, 8, 16)}
            for m in ("palette", "kmeans", "proposed")
        },
    }


def load(name: str) -> Image.Image:
    with Image.open(SAMPLES / name) as image:
        return normalize_size(image.convert("RGB"), P, crop_to_grid=True)


def crop_scaled(image: Image.Image, box, scale=3) -> Image.Image:
    region = image.crop(box)
    return region.resize((region.width * scale, region.height * scale), Image.Resampling.NEAREST)


def save(image: Image.Image, name: str) -> None:
    image.save(OUT / name, optimize=True)


def assets() -> None:
    # Hero: original | proposed
    hero = load("42049.jpg")
    save(hero, "hero_original.png")
    save(run_pipeline(hero, PipelineConfig(pixel_size=P, color_count=K)).image, "hero_proposed.png")
    save(run_pipeline(hero, PipelineConfig(pixel_size=8, color_count=8, outline=True)).image, "hero_p8k8_outline.png")

    # Zoomed comparison and pipeline stages on the statue image
    statue = load("101085.jpg")
    box = (statue.width // 4, statue.height // 4, statue.width // 4 + 160, statue.height // 4 + 120)
    save(crop_scaled(statue, box), "zoom_original.png")
    for method in ("palette", "kmeans"):
        save(crop_scaled(process_image(statue, method, P, K), box), f"zoom_{method}.png")
    result = run_pipeline(statue, PipelineConfig(pixel_size=P, color_count=K), keep_stages=True)
    save(crop_scaled(result.image, box), "zoom_proposed.png")
    for key, stage in result.stages.items():
        save(crop_scaled(stage, box), f"stage_{key}.png")
    no_cleanup = run_pipeline(statue, PipelineConfig(pixel_size=P, color_count=K, cleanup=False)).image
    save(crop_scaled(no_cleanup, box), "zoom_no_cleanup.png")

    # Colour example: median-cut drops the yellow skirt, Lab K-means keeps it
    dancer = load("101087.jpg")
    save(dancer, "dancer_original.png")
    save(process_image(dancer, "palette", P, K), "dancer_palette.png")
    save(run_pipeline(dancer, PipelineConfig(pixel_size=P, color_count=K)).image, "dancer_proposed.png")

    # Thumbnail grid of the sample images
    names = sorted(p.name for p in SAMPLES.glob("*.jpg"))
    thumb_w, thumb_h, gap, cols = 240, 160, 8, 3
    rows_n = (len(names) + cols - 1) // cols
    grid = Image.new("RGB", (cols * thumb_w + (cols - 1) * gap, rows_n * thumb_h + (rows_n - 1) * gap), "white")
    for index, name in enumerate(names):
        with Image.open(SAMPLES / name) as image:
            thumb = image.convert("RGB")
            thumb = ImageOps.fit(thumb, (thumb_w, thumb_h), Image.Resampling.LANCZOS)  # centre-crop, keep aspect
        grid.paste(thumb, ((index % cols) * (thumb_w + gap), (index // cols) * (thumb_h + gap)))
    save(grid, "samples_grid.png")

    # Small illustration of an isolated cell for the metric definition
    cell = 40
    demo = Image.new("RGB", (5 * cell, 5 * cell), (70, 110, 70))
    draw = ImageDraw.Draw(demo)
    draw.rectangle((2 * cell, 2 * cell, 3 * cell - 1, 3 * cell - 1), fill=(220, 200, 60))
    for i in range(6):
        draw.line((i * cell, 0, i * cell, 5 * cell), fill=(40, 60, 40))
        draw.line((0, i * cell, 5 * cell, i * cell), fill=(40, 60, 40))
    save(demo, "isolated_demo.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "numbers.json").write_text(json.dumps(numbers(), indent=1, ensure_ascii=False), encoding="utf-8")
    assets()
    print(f"Assets written to {OUT}")


if __name__ == "__main__":
    main()
