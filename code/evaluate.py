"""Benchmark the proposed pipeline against baseline methods on an image folder.

Example (BSDS300 test split, 100 images):

    python code/evaluate.py --data data/BSDS300/images/test --out results/eval

Outputs in --out:
    metrics_per_image.csv   one row per (image, method, setting)
    summary.md              mean +/- std tables, win rates, ablation, K/pixel sweeps
    fig_*.png               comparison grids, pipeline stages, metric charts
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pixel_art_studio import metrics  # noqa: E402
from pixel_art_studio.pipeline import PipelineConfig, normalize_size, run_pipeline  # noqa: E402
from pixel_art_studio.processing import discover_images, process_image  # noqa: E402

# (key, label, kind) - kind "baseline" uses processing.METHODS, otherwise a pipeline config.
BASELINES = [
    ("nearest", "Nearest neighbor (đối chứng)"),
    ("box-average", "Box average"),
    ("palette", "Median-cut palette (đối chứng)"),
    ("kmeans", "K-means RGB"),
    ("ordered", "Ordered dithering"),
    ("floyd-steinberg", "Floyd–Steinberg"),
]
VARIANTS = {
    "proposed": ("Proposed (đầy đủ)", {}),
    "abl-no-denoise": ("Proposed − khử nhiễu", {"denoise": False}),
    "abl-rgb": ("Proposed − Lab (dùng RGB)", {"color_space": "rgb"}),
    "abl-no-cleanup": ("Proposed − lọc đa số", {"cleanup": False}),
}
LABELS = dict(BASELINES) | {key: label for key, (label, _) in VARIANTS.items()}
MAIN_METHODS = [key for key, _ in BASELINES] + ["proposed"]
ABLATION_METHODS = ["palette", "proposed", "abl-no-denoise", "abl-rgb", "abl-no-cleanup"]
SWEEP_METHODS = ["palette", "kmeans", "proposed"]
METRIC_COLUMNS = ["psnr", "ssim", "delta_e", "colors", "isolated_pct", "time_ms"]


def render(image: Image.Image, method: str, pixel_size: int, colors: int) -> Image.Image:
    if method in VARIANTS:
        config = replace(
            PipelineConfig(pixel_size=pixel_size, color_count=colors), **VARIANTS[method][1]
        )
        return run_pipeline(image, config).image
    return process_image(image, method, pixel_size, colors)


def load_reference(path: Path, pixel_size: int, max_side: int | None) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    return normalize_size(image, pixel_size, max_side=max_side, crop_to_grid=True)


def evaluate_image(task: tuple) -> list[dict]:
    path, jobs, max_side = task
    rows = []
    references: dict[int, Image.Image] = {}
    for method, pixel_size, colors in jobs:
        if pixel_size not in references:
            references[pixel_size] = load_reference(path, pixel_size, max_side)
        reference = references[pixel_size]
        start = time.perf_counter()
        result = render(reference, method, pixel_size, colors)
        elapsed = (time.perf_counter() - start) * 1000
        row = {"image": path.name, "method": method, "pixel_size": pixel_size, "colors_k": colors}
        row |= metrics.evaluate(reference, result, pixel_size)
        row["time_ms"] = elapsed
        rows.append(row)
    return rows


def build_jobs(pixel_size: int, colors: int, sweep: bool) -> list[tuple[str, int, int]]:
    jobs = {(m, pixel_size, colors) for m in MAIN_METHODS + ABLATION_METHODS}
    if sweep:
        for k in (8, 16, 32, 64):
            jobs |= {(m, pixel_size, k) for m in SWEEP_METHODS}
        for p in (2, 4, 8, 16):
            jobs |= {(m, p, colors) for m in SWEEP_METHODS}
    return sorted(jobs)


# ----------------------------------------------------------------- reporting
def _select(rows, method, pixel_size, colors):
    return [r for r in rows if r["method"] == method and r["pixel_size"] == pixel_size and r["colors_k"] == colors]


def _mean_std(values) -> str:
    values = [v for v in values if math.isfinite(v)]
    if not values:
        return "–"
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    digits = 3 if abs(mean) < 10 else 2
    return f"{mean:.{digits}f} ± {std:.{digits}f}"


def _table(rows, methods, pixel_size, colors) -> list[str]:
    lines = [
        "| Phương pháp | PSNR (dB) ↑ | SSIM ↑ | ΔE2000 ↓ | Số màu | Pixel lẻ (%) ↓ | Thời gian (ms) |",
        "|---|---|---|---|---|---|---|",
    ]
    for method in methods:
        selected = _select(rows, method, pixel_size, colors)
        cells = [_mean_std([r[c] for r in selected]) for c in METRIC_COLUMNS]
        name = f"**{LABELS[method]}**" if method == "proposed" else LABELS[method]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return lines


def _win_rate(rows, method, baseline, pixel_size, colors) -> list[str]:
    ours = {r["image"]: r for r in _select(rows, method, pixel_size, colors)}
    theirs = {r["image"]: r for r in _select(rows, baseline, pixel_size, colors)}
    common = sorted(set(ours) & set(theirs))
    lines = ["| Độ đo | Proposed tốt hơn | Hòa | Kém hơn |", "|---|---|---|---|"]
    for metric, higher_better in (("psnr", True), ("ssim", True), ("delta_e", False), ("isolated_pct", False)):
        better = worse = 0
        for image in common:
            a, b = ours[image][metric], theirs[image][metric]
            if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9):
                continue
            if (a > b) == higher_better:
                better += 1
            else:
                worse += 1
        ties = len(common) - better - worse
        lines.append(f"| {metric} | {better}/{len(common)} | {ties} | {worse} |")
    return lines


def write_summary(rows, out: Path, pixel_size: int, colors: int, n_images: int, sweep: bool) -> None:
    lines = [
        "# Kết quả đánh giá định lượng",
        "",
        f"- Số ảnh đánh giá: **{n_images}**; kích thước pixel = **{pixel_size}**, số màu K = **{colors}**.",
        "- Ảnh tham chiếu: ảnh gốc đã chuẩn hóa (cắt về bội số của kích thước pixel).",
        "- Giá trị: trung bình ± độ lệch chuẩn trên toàn bộ ảnh. ↑ càng cao càng tốt, ↓ càng thấp càng tốt.",
        "- Nearest/Box average không giới hạn số màu và dithering dùng 4 mức/kênh (cố định), nên",
        "  không cùng ngân sách màu với các phương pháp bảng màu K màu.",
        "",
        "## 1. So sánh với các phương pháp đối chứng",
        "",
        *_table(rows, MAIN_METHODS, pixel_size, colors),
        "",
        "## 2. Proposed so với Median-cut (đối chứng chính) trên từng ảnh",
        "",
        *_win_rate(rows, "proposed", "palette", pixel_size, colors),
        "",
        "## 3. Ablation – bỏ từng bước của pipeline",
        "",
        *_table(rows, ABLATION_METHODS, pixel_size, colors),
        "",
    ]
    if sweep:
        lines += ["## 4. Ảnh hưởng của số màu K (kích thước pixel = %d)" % pixel_size, ""]
        lines += ["| K | " + " | ".join(f"{LABELS[m]} ΔE / pixel lẻ %" for m in SWEEP_METHODS) + " |"]
        lines += ["|---|" + "---|" * len(SWEEP_METHODS)]
        for k in (8, 16, 32, 64):
            cells = []
            for m in SWEEP_METHODS:
                sel = _select(rows, m, pixel_size, k)
                cells.append(
                    f"{statistics.fmean(r['delta_e'] for r in sel):.2f} / "
                    f"{statistics.fmean(r['isolated_pct'] for r in sel):.2f}"
                )
            lines.append(f"| {k} | " + " | ".join(cells) + " |")
        lines += ["", "## 5. Ảnh hưởng của kích thước pixel (K = %d)" % colors, ""]
        lines += ["| Pixel | " + " | ".join(f"{LABELS[m]} SSIM / pixel lẻ %" for m in SWEEP_METHODS) + " |"]
        lines += ["|---|" + "---|" * len(SWEEP_METHODS)]
        for p in (2, 4, 8, 16):
            cells = []
            for m in SWEEP_METHODS:
                sel = _select(rows, m, p, colors)
                cells.append(
                    f"{statistics.fmean(r['ssim'] for r in sel):.3f} / "
                    f"{statistics.fmean(r['isolated_pct'] for r in sel):.2f}"
                )
            lines.append(f"| {p} | " + " | ".join(cells) + " |")
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_figures(rows, images: list[Path], out: Path, pixel_size: int, colors: int, max_side, sweep: bool) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Visual comparison on a few images (same input for every method).
    shown = ["nearest", "palette", "kmeans", "floyd-steinberg", "proposed"]
    picks = images[:3]
    first = load_reference(picks[0], pixel_size, max_side)
    cell_w = 1.9
    cell_h = cell_w * first.height / first.width + 0.3  # room for the panel title
    fig, axes = plt.subplots(
        len(picks), len(shown) + 1, figsize=(cell_w * (len(shown) + 1), cell_h * len(picks) + 0.4), squeeze=False
    )
    for row, path in enumerate(picks):
        reference = load_reference(path, pixel_size, max_side)
        panels = [("Ảnh gốc", reference)] + [(LABELS[m], render(reference, m, pixel_size, colors)) for m in shown]
        for col, (title, image) in enumerate(panels):
            axes[row, col].imshow(image, interpolation="nearest")
            axes[row, col].set_title(title, fontsize=8)
            axes[row, col].axis("off")
    fig.suptitle(f"So sánh trên cùng ảnh đầu vào (pixel = {pixel_size}, K = {colors})")
    fig.tight_layout()
    fig.savefig(out / "fig_comparison.png", dpi=130)
    plt.close(fig)

    # Zoomed crop: makes stray pixels visible.
    reference = load_reference(picks[0], pixel_size, max_side)
    box = (reference.width // 4, reference.height // 4, reference.width // 4 + 160, reference.height // 4 + 120)
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.2))
    for ax, (title, method) in zip(
        axes, [("Ảnh gốc", None), ("Median-cut", "palette"), ("K-means RGB", "kmeans"), ("Proposed", "proposed")]
    ):
        image = reference if method is None else render(reference, method, pixel_size, colors)
        ax.imshow(image.crop(box), interpolation="nearest")
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    fig.suptitle("Phóng to một vùng: pixel lẻ (nhiễu) bị loại bỏ ở pipeline đề xuất")
    fig.tight_layout()
    fig.savefig(out / "fig_zoom.png", dpi=130)
    plt.close(fig)

    # Every stage of the proposed pipeline.
    result = run_pipeline(reference, PipelineConfig(pixel_size=pixel_size, color_count=colors), keep_stages=True)
    names = {
        "1_input": "1. Đầu vào (chuẩn hóa)",
        "2_denoised": "2. Lọc trung vị 3x3",
        "3_downsampled": "3. Lấy mẫu xuống (box)",
        "4_quantized": f"4. K-means Lab (K={colors})",
        "5_cleaned": "5. Lọc đa số (hậu xử lý)",
        "6_output": "6. Kết quả",
    }
    fig, axes = plt.subplots(2, 3, figsize=(12, 5.6))
    for ax, (key, image) in zip(axes.flat, result.stages.items()):
        ax.imshow(image.crop(box), interpolation="nearest")
        ax.set_title(names[key], fontsize=9)
        ax.axis("off")
    fig.suptitle("Các bước của pipeline (vùng phóng to)")
    fig.tight_layout()
    fig.savefig(out / "fig_pipeline_stages.png", dpi=130)
    plt.close(fig)

    # Bar charts of the main metrics.
    methods = MAIN_METHODS
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, (metric, title) in zip(
        axes, [("ssim", "SSIM ↑"), ("delta_e", "ΔE2000 ↓"), ("isolated_pct", "Pixel lẻ (%) ↓")]
    ):
        means = [statistics.fmean(r[metric] for r in _select(rows, m, pixel_size, colors)) for m in methods]
        colors_bar = ["#c0392b" if m == "proposed" else "#95a5a6" for m in methods]
        ax.barh([LABELS[m] for m in methods], means, color=colors_bar)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_metrics.png", dpi=130)
    plt.close(fig)

    if sweep:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        ks = (8, 16, 32, 64)
        for m in SWEEP_METHODS:
            axes[0].plot(ks, [statistics.fmean(r["delta_e"] for r in _select(rows, m, pixel_size, k)) for k in ks], marker="o", label=LABELS[m])
            axes[1].plot(ks, [statistics.fmean(r["isolated_pct"] for r in _select(rows, m, pixel_size, k)) for k in ks], marker="o", label=LABELS[m])
        for ax, title in zip(axes, ("ΔE2000 theo K ↓", "Pixel lẻ (%) theo K ↓")):
            ax.set_xscale("log", base=2)
            ax.set_xticks(ks, [str(k) for k in ks])
            ax.set_xlabel("Số màu K")
            ax.set_title(title)
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / "fig_sweep_k.png", dpi=130)
        plt.close(fig)


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["pixel_size"], row["colors_k"] = int(row["pixel_size"]), int(row["colors_k"])
        for column in METRIC_COLUMNS:
            row[column] = float(row[column])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True, help="folder of evaluation images")
    parser.add_argument("--out", type=Path, default=Path("results/eval"))
    parser.add_argument("--pixel-size", type=int, default=4)
    parser.add_argument("--colors", type=int, default=16)
    parser.add_argument("--max-side", type=int, default=None, help="optionally shrink large images first")
    parser.add_argument("--limit", type=int, default=None, help="evaluate only the first N images")
    parser.add_argument("--no-sweep", action="store_true", help="skip the K / pixel-size sweeps")
    parser.add_argument("--workers", type=int, default=None, help="parallel processes (default: CPU count)")
    parser.add_argument("--figures-only", action="store_true", help="redraw summary/figures from an existing CSV")
    args = parser.parse_args()

    images = discover_images(args.data)[: args.limit]
    if not images:
        raise SystemExit(f"No images found in {args.data}")
    args.out.mkdir(parents=True, exist_ok=True)
    sweep = not args.no_sweep
    jobs = build_jobs(args.pixel_size, args.colors, sweep)

    csv_path = args.out / "metrics_per_image.csv"
    if args.figures_only:
        rows = load_rows(csv_path)
    else:
        print(f"Evaluating {len(images)} images x {len(jobs)} runs ...", flush=True)
        rows = []
        tasks = [(path, jobs, args.max_side) for path in images]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for index, image_rows in enumerate(pool.map(evaluate_image, tasks), start=1):
                rows.extend(image_rows)
                if index % 10 == 0 or index == len(images):
                    print(f"  {index}/{len(images)} images done", flush=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write_summary(rows, args.out, args.pixel_size, args.colors, len(images), sweep)
    write_figures(rows, images, args.out, args.pixel_size, args.colors, args.max_side, sweep)
    print(f"Done. See {args.out / 'summary.md'}")


if __name__ == "__main__":
    main()
