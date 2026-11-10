"""Convert images to pixel art from the command line.

Examples:

    # proposed pipeline on the bundled samples, outputs in results/samples/
    python code/run_pipeline.py --input samples --output results/samples

    # one file, chunkier pixels, 8 colours, with outlines and stage images
    python code/run_pipeline.py --input samples/42049.jpg --pixel-size 8 --colors 8 --outline --save-stages

    # any baseline method instead of the proposed pipeline
    python code/run_pipeline.py --input samples --method palette
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pixel_art_studio import metrics  # noqa: E402
from pixel_art_studio.pipeline import PipelineConfig, normalize_size, run_pipeline  # noqa: E402
from pixel_art_studio.processing import (  # noqa: E402
    METHOD_BY_KEY,
    SUPPORTED_EXTENSIONS,
    discover_images,
    process_image,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True, help="image file or folder")
    parser.add_argument("--output", type=Path, default=Path("results/output"))
    parser.add_argument("--method", default="pipeline", choices=sorted(METHOD_BY_KEY))
    parser.add_argument("--pixel-size", type=int, default=4)
    parser.add_argument("--colors", type=int, default=16)
    parser.add_argument("--max-side", type=int, default=None, help="shrink large photos first (e.g. 640)")
    parser.add_argument("--no-denoise", action="store_true", help="pipeline: skip the median filter")
    parser.add_argument("--rgb", action="store_true", help="pipeline: cluster in RGB instead of Lab")
    parser.add_argument("--no-cleanup", action="store_true", help="pipeline: keep isolated pixels")
    parser.add_argument("--outline", action="store_true", help="pipeline: add dark Sobel outlines")
    parser.add_argument("--save-stages", action="store_true", help="pipeline: also save every step")
    args = parser.parse_args()

    if args.input.is_dir():
        paths = discover_images(args.input)
    elif args.input.suffix.lower() in SUPPORTED_EXTENSIONS and args.input.is_file():
        paths = [args.input]
    else:
        raise SystemExit(f"Not an image or folder: {args.input}")
    if not paths:
        raise SystemExit(f"No images found in {args.input}")

    config = PipelineConfig(
        pixel_size=args.pixel_size,
        color_count=args.colors,
        denoise=not args.no_denoise,
        color_space="rgb" if args.rgb else "lab",
        cleanup=not args.no_cleanup,
        outline=args.outline,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"{'image':<24}{'PSNR':>8}{'SSIM':>8}{'dE2000':>8}{'colors':>8}{'isol%':>8}{'ms':>8}")
    for path in paths:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        reference = normalize_size(image, args.pixel_size, args.max_side, crop_to_grid=True)
        start = time.perf_counter()
        if args.method == "pipeline":
            result = run_pipeline(reference, config, keep_stages=args.save_stages)
            output = result.image
            for name, stage in result.stages.items():
                stage.save(args.output / f"{path.stem}_stage{name}.png")
        else:
            output = process_image(reference, args.method, args.pixel_size, args.colors)
        elapsed = (time.perf_counter() - start) * 1000
        output.save(args.output / f"{path.stem}_{args.method}.png")
        scores = metrics.evaluate(reference, output, args.pixel_size)
        print(
            f"{path.name[:23]:<24}{scores['psnr']:>8.2f}{scores['ssim']:>8.3f}{scores['delta_e']:>8.2f}"
            f"{scores['colors']:>8}{scores['isolated_pct']:>8.2f}{elapsed:>8.0f}"
        )
    print(f"Saved {len(paths)} result(s) to {args.output.resolve()}")


if __name__ == "__main__":
    main()
