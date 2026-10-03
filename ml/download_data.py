"""Download the UCI Bank Marketing dataset and extract bank-full.csv."""
import io
import urllib.request
import zipfile

from ml.config import DATASET_URL, RAW_CSV, RAW_DIR


def _find_and_extract(zf: zipfile.ZipFile, target_name: str) -> bytes | None:
    """Search a zip (recursing into nested zips) for a file by basename."""
    for name in zf.namelist():
        if name.rsplit("/", 1)[-1] == target_name:
            return zf.read(name)
    for name in zf.namelist():
        if name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(zf.read(name))) as inner:
                found = _find_and_extract(inner, target_name)
                if found is not None:
                    return found
    return None


def download(force: bool = False) -> None:
    if RAW_CSV.exists() and not force:
        print(f"Dataset already present at {RAW_CSV}")
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DATASET_URL} ...")
    with urllib.request.urlopen(DATASET_URL, timeout=120) as resp:
        payload = resp.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        data = _find_and_extract(zf, RAW_CSV.name)
    if data is None:
        raise RuntimeError(f"{RAW_CSV.name} not found in downloaded archive")
    RAW_CSV.write_bytes(data)
    print(f"Saved {RAW_CSV} ({len(data) / 1024:.0f} KB)")


if __name__ == "__main__":
    download()
