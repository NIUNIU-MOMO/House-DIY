#!/usr/bin/env python3
"""根据 catalog.json 为每件家具生成占位 box GLB（CC0 占位，可后续替换）"""

import json
from pathlib import Path

import trimesh

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "assets" / "furniture" / "catalog.json"
OUTPUT_DIR = REPO_ROOT / "assets" / "furniture"


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for item in catalog["items"]:
        glb_name = Path(item["glb_path"]).name
        target = OUTPUT_DIR / glb_name
        box = trimesh.creation.box(extents=[item["width"], item["depth"], item["height"]])
        box.export(str(target))
        print(f"Wrote {target.name}")

    print(f"Generated {len(catalog['items'])} GLB files")


if __name__ == "__main__":
    main()
