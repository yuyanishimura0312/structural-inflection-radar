#!/usr/bin/env python3
"""
Aggregate scored items into themes and calculate delta scores (acceleration).
Groups items by theme tags, computes per-axis scores, and tracks score changes.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
DATA_THEMES = Path(__file__).parent.parent / "data" / "themes"

AXES = [
    "threshold_proximity",
    "external_pressure",
    "tech_cycle_position",
    "institutional_change",
    "uncertainty_resolution",
]

AXIS_LABELS = {
    "threshold_proximity": "閾値接近",
    "external_pressure": "外圧/窓",
    "tech_cycle_position": "技術革命",
    "institutional_change": "制度変化",
    "uncertainty_resolution": "不確実性解消",
}


def load_processed_data() -> list[dict]:
    """Load all processed data files."""
    all_items = []
    for f in sorted(DATA_PROCESSED.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
            all_items.extend(data.get("items", []))
    return all_items


def load_previous_themes() -> dict:
    """Load the previous themes snapshot for delta calculation."""
    history_file = DATA_THEMES / "history.json"
    if history_file.exists():
        with open(history_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(themes_by_name: dict):
    """Save current theme scores as history for next delta calculation."""
    history_file = DATA_THEMES / "history.json"
    snapshot = {
        "snapshot_at": datetime.now().isoformat(),
        "themes": {
            name: {axis: t["axes"][axis]["score"] for axis in AXES}
            for name, t in themes_by_name.items()
        },
    }
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def aggregate_themes(items: list[dict]) -> dict:
    """Group items by theme tags and compute per-axis scores."""
    theme_items = defaultdict(list)

    for item in items:
        tags = item.get("theme_tags", [])
        # Normalize tags to lowercase
        tags = [t.lower().strip() for t in tags if t.strip()]
        if not tags:
            tags = ["unclassified"]
        for tag in tags:
            theme_items[tag].append(item)

    themes = {}
    for tag, tag_items in theme_items.items():
        if tag == "unclassified":
            continue
        # Filter out themes with too few items (noise reduction)
        if len(tag_items) < 2:
            continue

        axes_data = {}
        total_weight = sum(it.get("credibility_weight", 0.4) for it in tag_items)

        for axis in AXES:
            signal_weight = sum(
                it.get("credibility_weight", 0.4)
                for it in tag_items
                if it.get("axes", {}).get(axis, {}).get("signal", False)
            )
            score = signal_weight / total_weight if total_weight > 0 else 0

            # Collect evidence
            evidence = [
                it["axes"][axis]["evidence"]
                for it in tag_items
                if it.get("axes", {}).get(axis, {}).get("evidence")
            ]

            axes_data[axis] = {
                "score": round(score, 3),
                "signal_count": sum(
                    1 for it in tag_items
                    if it.get("axes", {}).get(axis, {}).get("signal", False)
                ),
                "evidence": evidence[:3],  # Top 3 evidence items
                "label": AXIS_LABELS[axis],
            }

        # Composite score: weighted average (threshold_proximity weighted 25%, others 18.75%)
        composite = (
            axes_data["threshold_proximity"]["score"] * 0.25 +
            axes_data["external_pressure"]["score"] * 0.1875 +
            axes_data["tech_cycle_position"]["score"] * 0.1875 +
            axes_data["institutional_change"]["score"] * 0.1875 +
            axes_data["uncertainty_resolution"]["score"] * 0.1875
        )

        # Collect source items for display
        source_items = [
            {
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "source": it.get("source", ""),
                "date": it.get("publication_date", ""),
            }
            for it in tag_items[:10]  # Max 10 per theme
        ]

        themes[tag] = {
            "name": tag,
            "item_count": len(tag_items),
            "composite_score": round(composite, 3),
            "axes": axes_data,
            "source_items": source_items,
        }

    return themes


def calculate_deltas(current_themes: dict, previous_history: dict) -> dict:
    """Calculate delta scores (acceleration) compared to previous snapshot."""
    prev_themes = previous_history.get("themes", {})

    for name, theme in current_themes.items():
        prev = prev_themes.get(name, {})
        delta_axes = {}
        for axis in AXES:
            current_score = theme["axes"][axis]["score"]
            prev_score = prev.get(axis, 0)
            delta_axes[axis] = round(current_score - prev_score, 3)

        # Composite delta
        prev_composite = sum(prev.get(a, 0) for a in AXES) / len(AXES)
        current_composite = theme["composite_score"]
        composite_delta = round(current_composite - prev_composite, 3)

        theme["delta"] = {
            "composite": composite_delta,
            "axes": delta_axes,
        }

    return current_themes


def run() -> Path:
    """Run aggregation pipeline."""
    DATA_THEMES.mkdir(parents=True, exist_ok=True)

    items = load_processed_data()
    if not items:
        print("エラー: 処理済みデータがありません。先に score.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    print(f"Aggregating {len(items)} scored items into themes...")

    themes = aggregate_themes(items)
    previous = load_previous_themes()
    themes = calculate_deltas(themes, previous)

    # Sort by composite delta (descending) for ranking
    sorted_themes = sorted(
        themes.values(),
        key=lambda t: t.get("delta", {}).get("composite", 0),
        reverse=True,
    )

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_themes": len(sorted_themes),
        "total_source_items": len(items),
        "themes": sorted_themes,
    }

    output_path = DATA_THEMES / "latest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Save current as history for next run
    save_history(themes)

    # Print summary
    print(f"  {len(sorted_themes)} themes generated")
    print(f"\n  Top 3 by acceleration (Δ score):")
    for t in sorted_themes[:3]:
        delta = t.get("delta", {}).get("composite", 0)
        direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        print(f"    {direction} {t['name']} (Δ={delta:+.3f}, score={t['composite_score']:.3f}, {t['item_count']} items)")

    return output_path


if __name__ == "__main__":
    run()
