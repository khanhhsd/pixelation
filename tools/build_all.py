"""Rebuild every deliverable and the submission zip in one go.

    python tools/build_all.py            # after editing docs/nhom.json

Steps: assets + numbers -> report (.docx/.pdf) -> slides (.pptx/.pdf) -> LopXX_NhomYY_TenDeTai.zip
Needs: Node.js (run `npm install` once inside tools/), Microsoft Word and PowerPoint for PDF export.
The evaluation itself is NOT re-run; run code/evaluate.py first if the code changed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "out"
TOOLS = ROOT / "tools"

# What goes into the zip (relative to the project root).
INCLUDE = ["README.md", "requirements.txt", "pyproject.toml", "code", "samples", "tests", "results/eval"]
SKIP_PARTS = {"__pycache__", ".ipynb_checkpoints", "node_modules", ".egg-info"}


def run(*cmd: str) -> None:
    print(">", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Vietnamese text on cp1252 consoles
    team = json.loads((ROOT / "docs" / "nhom.json").read_text(encoding="utf-8"))
    placeholders = [v for v in (team["lop"], team["nhom"]) if v in ("LopXX", "NhomYY")]
    placeholders += [f"tên '{m['ho_ten']}'" for m in team["thanh_vien"] if m["ho_ten"].startswith("Thành viên")]
    placeholders += [f"MSSV của {m['ho_ten']}" for m in team["thanh_vien"] if m["mssv"] in ("", "MSSV")]
    if placeholders:
        print(f"WARNING: docs/nhom.json still has placeholders: {', '.join(placeholders)}", flush=True)

    if not (TOOLS / "node_modules").is_dir():
        run("npm", "install", "--prefix", str(TOOLS))
    run(sys.executable, str(TOOLS / "make_assets.py"))
    run("node", str(TOOLS / "build_report.js"))
    run("node", str(TOOLS / "build_slides.js"))
    run(sys.executable, str(TOOLS / "office_export.py"), str(OUT / "BaoCao.docx"))
    run(sys.executable, str(TOOLS / "office_export.py"), str(OUT / "Slide.pptx"))

    group = f"Nhom{team['nhom']}" if team["nhom"].isdigit() else team["nhom"]
    name = f"{team['lop']}_{group}_{team['ten_de_tai_file']}"
    archive = ROOT / f"{name}.zip"
    count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE:
            source = ROOT / item
            files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
            for file in files:
                rel = file.relative_to(ROOT)
                if any(part in SKIP_PARTS or part.endswith(".egg-info") for part in rel.parts):
                    continue
                zf.write(file, f"{name}/{rel.as_posix()}")
                count += 1
        for file in ("BaoCao.pdf", "BaoCao.docx", "Slide.pptx", "Slide.pdf"):
            zf.write(OUT / file, f"{name}/{file}")
            count += 1
    size = archive.stat().st_size / 1e6
    print(f"\nDone: {archive.name} ({count} files, {size:.1f} MB)")
    print(f"Email to uyenvnb@ptit.edu.vn with subject: {name}")


if __name__ == "__main__":
    main()
