"""Download the public Steam dataset (CC BY 4.0) into data/raw/."""
import sys
import urllib.request

from config import DATASET, ROOT

DEST = ROOT / "data" / "raw" / DATASET["file"]


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size == DATASET["bytes"]:
        print(f"{DEST} already present ({DEST.stat().st_size:,} bytes).")
        return 0
    print(f"Downloading {DATASET['file']} ({DATASET['bytes']:,} bytes) from Mendeley Data...")
    urllib.request.urlretrieve(DATASET["download_url"], DEST)
    size = DEST.stat().st_size
    if size != DATASET["bytes"]:
        print(f"Unexpected size {size:,}; expected {DATASET['bytes']:,}.", file=sys.stderr)
        return 1
    print(f"Saved {DEST} ({size:,} bytes).")
    print(f"Dataset: {DATASET['title']} by {DATASET['author']}, {DATASET['license']}, doi:{DATASET['doi']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
