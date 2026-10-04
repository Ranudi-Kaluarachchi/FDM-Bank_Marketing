"""Download the UCI Bank Marketing dataset and extract bank-full.csv.

Run with:  python -m ml.download_data
"""
import io
import urllib.request
import zipfile

from ml.config import DATASET_URL, RAW_CSV, RAW_DIR


def _find_and_extract(zf: zipfile.ZipFile, target_name: str) -> bytes | None:
    """Search a zip (recursing into nested zips) for a file by basename.

    The UCI archive contains bank.zip and bank-additional.zip inside it, so the
    CSV we want is one level down.
    """
    # First look for the file directly in this archive.
    for name in zf.namelist():
        if name.rsplit("/", 1)[-1] == target_name:
            return zf.read(name)
    # Otherwise open each inner .zip in memory and search it.
    for name in zf.namelist():
        if name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(zf.read(name))) as inner:
                found = _find_and_extract(inner, target_name)
                if found is not None:
                    return found
    return None


def download(force: bool = False) -> None:
    """Download the dataset into data/raw/ (skipped if it is already there, unless force=True)."""
    if RAW_CSV.exists() and not force:
        print(f"Dataset already present at {RAW_CSV}")
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DATASET_URL} ...")
    with urllib.request.urlopen(DATASET_URL, timeout=120) as resp:
        payload = resp.read()  # whole archive (~1 MB) held in memory
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        data = _find_and_extract(zf, RAW_CSV.name)
    if data is None:
        raise RuntimeError(f"{RAW_CSV.name} not found in downloaded archive")
    RAW_CSV.write_bytes(data)
    print(f"Saved {RAW_CSV} ({len(data) / 1024:.0f} KB)")


if __name__ == "__main__":
    download()
