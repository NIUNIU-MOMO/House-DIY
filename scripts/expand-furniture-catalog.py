#!/usr/bin/env python3
"""将家具 catalog 扩展至 80+ SKU（占位 box GLB）"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "assets" / "furniture" / "catalog.json"

BASE_ITEMS = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["items"]

VARIANTS = [
    ("sofa", "沙发", ["corner", "sectional", "minimal", "linen", "leather", "modular", "recliner"], (2.0, 1.0, 0.85)),
    ("bed", "床", ["single", "bunk", "platform", "storage", "kids", "daybed", "fold"], (1.5, 2.0, 0.55)),
    ("chair", "椅", ["accent", "lounge", "bar", "stool", "bench", "rocking", "office"], (0.5, 0.5, 0.85)),
    ("table", "桌", ["side", "console", "study", "extend", "nest", "coffee", "dining"], (1.0, 0.6, 0.75)),
    ("cabinet", "柜", ["low", "display", "shoe", "entry", "media", "tall", "corner"], (1.2, 0.45, 0.9)),
    ("desk", "书桌", ["standing", "compact", "l_shape", "kids", "gaming", "writing", "corner"], (1.4, 0.7, 0.75)),
    ("light", "灯", ["table", "wall", "track", "spot", "strip", "chandelier", "sconce"], (0.3, 0.3, 0.5)),
    ("decor", "装饰", ["plant", "mirror", "art", "vase", "shelf", "clock", "screen"], (0.6, 0.3, 1.2)),
    ("kitchen", "厨电", ["hood", "fridge", "oven", "sink", "wall_cab", "pantry", "dishwasher"], (0.9, 0.6, 0.9)),
    ("bathroom", "卫浴", ["tub", "basin", "mirror_cab", "towel_rack", "bidet", "shower_tray", "laundry"], (0.7, 0.5, 0.85)),
]


def main() -> None:
    items = list(BASE_ITEMS)
    seen = {item["sku"] for item in items}
    index = 1
    for category, label, names, (width, depth, height) in VARIANTS:
        for name in names:
            sku = f"{category}_{name}_v{index:02d}"
            if sku in seen:
                continue
            items.append(
                {
                    "sku": sku,
                    "name": f"{label}·{name}",
                    "category": category,
                    "width": round(width + (index % 5) * 0.05, 2),
                    "depth": round(depth + (index % 3) * 0.04, 2),
                    "height": round(height + (index % 4) * 0.03, 2),
                    "anchor": "floor_center",
                    "glb_path": f"furniture/{sku}.glb",
                }
            )
            seen.add(sku)
            index += 1
            if len(items) >= 85:
                break
        if len(items) >= 85:
            break

    CATALOG_PATH.write_text(
        json.dumps({"version": 1, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Catalog expanded to {len(items)} SKUs")


if __name__ == "__main__":
    main()
