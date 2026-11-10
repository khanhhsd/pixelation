"""Download the BSDS300 benchmark images (Berkeley Segmentation Dataset).

    python code/download_data.py            # -> data/BSDS300/images/{train,test}

The evaluation uses the 100-image test split. Source:
https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/
"""

from __future__ import annotations

import argparse
import tarfile
import urllib.request
from pathlib import Path

URL = "https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS300-images.tgz"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", type=Path, default=Path("data"))
    args = parser.parse_args()

    args.dest.mkdir(parents=True, exist_ok=True)
    archive = args.dest / "BSDS300-images.tgz"
    if not archive.exists():
        print(f"Downloading {URL} (~22 MB) ...")
        urllib.request.urlretrieve(URL, archive)
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.name.startswith("BSDS300/") and ".." not in m.name]
        tar.extractall(args.dest, members=members)
    test_dir = args.dest / "BSDS300" / "images" / "test"
    print(f"Done: {len(list(test_dir.glob('*.jpg')))} test images in {test_dir}")


if __name__ == "__main__":
    main()
