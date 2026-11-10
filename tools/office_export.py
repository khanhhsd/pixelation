"""Export .pptx / .docx to PDF (and slide PNGs) with the installed Microsoft Office.

    python tools/office_export.py docs/out/Slide.pptx [--png out_dir]
    python tools/office_export.py docs/out/BaoCao.docx
"""

from __future__ import annotations

import argparse
from pathlib import Path

import win32com.client  # pywin32, shipped with Anaconda / `pip install pywin32`

PPT_PDF, WORD_PDF = 32, 17


def export_pptx(path: Path, png_dir: Path | None) -> Path:
    app = win32com.client.DispatchEx("PowerPoint.Application")
    pdf = path.with_suffix(".pdf")
    try:
        deck = app.Presentations.Open(str(path), ReadOnly=True, Untitled=False, WithWindow=False)
        try:
            deck.SaveAs(str(pdf), PPT_PDF)
            if png_dir:
                png_dir.mkdir(parents=True, exist_ok=True)
                for slide in deck.Slides:
                    slide.Export(str(png_dir / f"slide-{slide.SlideIndex:02d}.png"), "PNG", 1600, 900)
        finally:
            deck.Close()
    finally:
        app.Quit()
    return pdf


def export_docx(path: Path) -> Path:
    app = win32com.client.DispatchEx("Word.Application")
    app.Visible = False
    pdf = path.with_suffix(".pdf")
    try:
        doc = app.Documents.Open(str(path), ReadOnly=True, AddToRecentFiles=False)
        try:
            doc.Fields.Update()
            doc.SaveAs2(str(pdf), FileFormat=WORD_PDF)
            pages = doc.ComputeStatistics(2)  # wdStatisticPages
            print(f"{path.name}: {pages} pages")
        finally:
            doc.Close(False)
    finally:
        app.Quit()
    return pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--png", type=Path, help="also export slide images (pptx only)")
    args = parser.parse_args()
    path = args.file.resolve()
    pdf = export_pptx(path, args.png) if path.suffix == ".pptx" else export_docx(path)
    print("Wrote", pdf)


if __name__ == "__main__":
    main()
