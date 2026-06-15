"""Download and verify all 7 public datasets required for CHRONOS training."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "datasets"
MANIFEST_PATH = Path(__file__).parent / "manifest.json"


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _download_file(url: str, dest: Path, desc: str = "") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    with open(dest, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, desc=desc or dest.name
    ) as bar:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            f.write(chunk)
            bar.update(len(chunk))


def _verify_checksums(dest_dir: Path, expected: dict[str, str]) -> bool:
    if not expected:
        logger.warning("No checksums provided for %s — skipping verification", dest_dir)
        return True
    ok = True
    for filename, expected_hash in expected.items():
        path = dest_dir / filename
        if not path.exists():
            logger.error("File missing: %s", path)
            ok = False
            continue
        actual = _sha256(path)
        if actual != expected_hash:
            logger.error("Checksum mismatch for %s: got %s, expected %s", path, actual, expected_hash)
            ok = False
    return ok


def download_mbd_mini(dest_dir: Path, dry_run: bool = False) -> None:
    """Download MBD-mini from HuggingFace."""
    from huggingface_hub import snapshot_download  # type: ignore[import]

    dest_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        logger.info("[dry-run] Would download ai-lab/MBD-mini → %s", dest_dir)
        return
    logger.info("Downloading MBD-mini from HuggingFace...")
    snapshot_download(repo_id="ai-lab/MBD-mini", local_dir=str(dest_dir), repo_type="dataset")
    logger.info("MBD-mini downloaded to %s", dest_dir)


def download_kaggle(dataset: str, dest_dir: Path, dry_run: bool = False) -> None:
    """Download a Kaggle dataset using the Kaggle API."""
    import kaggle  # type: ignore[import]  # noqa: F401

    dest_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        logger.info("[dry-run] Would download kaggle:%s → %s", dataset, dest_dir)
        return
    logger.info("Downloading Kaggle dataset %s...", dataset)
    os.system(f"kaggle datasets download -d {dataset} -p {dest_dir} --unzip")
    logger.info("Kaggle dataset %s downloaded to %s", dataset, dest_dir)


def download_scikit_uplift(function_name: str, dest_dir: Path, dry_run: bool = False) -> None:
    """Download a dataset via scikit-uplift fetch function."""
    import pandas as pd

    dest_dir.mkdir(parents=True, exist_ok=True)
    if function_name == "fetch_hillstrom":
        from sklift.datasets import fetch_hillstrom  # type: ignore[import]

        out_path = dest_dir / "hillstrom.parquet"
        if dry_run:
            logger.info("[dry-run] Would fetch Hillstrom → %s", out_path)
            return
        logger.info("Fetching Hillstrom dataset via scikit-uplift...")
        bunch = fetch_hillstrom()
        df = pd.DataFrame(bunch.data, columns=bunch.feature_names)
        df["target"] = bunch.target
        df["treatment"] = bunch.treatment
        df.to_parquet(out_path, index=False)
        logger.info("Hillstrom saved to %s (%d rows)", out_path, len(df))

    elif function_name == "fetch_criteo":
        from sklift.datasets import fetch_criteo  # type: ignore[import]

        out_path = dest_dir / "criteo_uplift.parquet"
        if dry_run:
            logger.info("[dry-run] Would fetch Criteo Uplift → %s", out_path)
            return
        logger.info("Fetching Criteo Uplift dataset (large — ~25M rows)...")
        bunch = fetch_criteo()
        df = pd.DataFrame(bunch.data, columns=bunch.feature_names)
        df["target"] = bunch.target
        df["treatment"] = bunch.treatment
        df.to_parquet(out_path, index=False)
        logger.info("Criteo Uplift saved to %s (%d rows)", out_path, len(df))


def download_uci_bank_marketing(dest_dir: Path, dry_run: bool = False) -> None:
    """Download UCI Bank Marketing dataset."""
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank-additional.zip"
    zip_path = dest_dir / "bank-additional.zip"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        logger.info("[dry-run] Would download UCI Bank Marketing → %s", dest_dir)
        return
    logger.info("Downloading UCI Bank Marketing dataset...")
    _download_file(url, zip_path, desc="uci-bank-marketing")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()
    logger.info("UCI Bank Marketing extracted to %s", dest_dir)


def download_all(dry_run: bool = False) -> dict[str, bool]:
    """Download all datasets and return per-dataset success flags."""
    manifest: dict[str, Any] = json.loads(MANIFEST_PATH.read_text())
    results: dict[str, bool] = {}

    for ds in manifest["datasets"]:
        name: str = ds["name"]
        dest_dir = ROOT / ds["subdirectory"]
        expected_checksums: dict[str, str] = ds.get("sha256", {})

        try:
            source = ds["source"]
            if source == "huggingface":
                download_mbd_mini(dest_dir, dry_run=dry_run)
            elif source == "kaggle":
                download_kaggle(ds["dataset"], dest_dir, dry_run=dry_run)
            elif source == "scikit-uplift":
                download_scikit_uplift(ds["function"], dest_dir, dry_run=dry_run)
            elif source == "uci":
                download_uci_bank_marketing(dest_dir, dry_run=dry_run)
            else:
                raise ValueError(f"Unknown source: {source}")

            if not dry_run:
                ok = _verify_checksums(dest_dir, expected_checksums)
                results[name] = ok
                if ok:
                    logger.info("[OK] %s verified", name)
                else:
                    logger.error("[FAIL] %s checksum mismatch", name)
            else:
                results[name] = True

        except Exception:
            logger.exception("Failed to download %s", name)
            results[name] = False

    return results


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )
    parser = argparse.ArgumentParser(description="Download CHRONOS training datasets")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without downloading")
    parser.add_argument("--dataset", help="Download only a specific dataset by name")
    args = parser.parse_args()

    manifest: dict[str, Any] = json.loads(MANIFEST_PATH.read_text())
    if args.dataset:
        manifest["datasets"] = [d for d in manifest["datasets"] if d["name"] == args.dataset]
        if not manifest["datasets"]:
            logger.error("Dataset '%s' not found in manifest", args.dataset)
            raise SystemExit(1)

    results = download_all(dry_run=args.dry_run)

    failed = [k for k, v in results.items() if not v]
    if failed:
        logger.error("Failed datasets: %s", failed)
        raise SystemExit(1)
    logger.info("All datasets downloaded and verified successfully.")


if __name__ == "__main__":
    main()
