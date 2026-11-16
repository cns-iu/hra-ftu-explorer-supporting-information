"""Download every input listed under `downloads` in config.yaml into raw-data/.

Files already present are skipped; delete one from raw-data/ to fetch it again.
"""
import requests

from shared import DOWNLOADS, download_path

for key, entry in DOWNLOADS.items():
    out_path = download_path(key)
    if out_path.exists():
        print(f"{entry['label']}: already at {out_path.name}, skipping")
        continue

    print(f"{entry['label']}: downloading {entry['url']}")
    response = requests.get(entry["url"], headers={"Accept": entry["accept"]}, timeout=120)
    response.raise_for_status()

    # Write to a temp file first so an interrupted download never leaves a partial file that later runs would skip
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    tmp_path.write_bytes(response.content)
    tmp_path.rename(out_path)
    print(f"  saved {out_path.name} ({len(response.content):,} bytes)")
