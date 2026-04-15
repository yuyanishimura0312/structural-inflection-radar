#!/usr/bin/env python3
"""
LLM-based signal extraction and 5-axis scoring using Claude API.
Classifies each collected item into the 5 structural inflection axes.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"

MODEL = "claude-haiku-4-5-20251001"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Source type credibility weights
CREDIBILITY_WEIGHTS = {
    "academic": 1.0,
    "tech_media": 0.7,
    "general_media": 0.4,
}

SCORING_PROMPT = """You are an expert in technology forecasting and structural change analysis.
Analyze the following item and determine if it contains signals related to these 5 axes of structural inflection points:

1. THRESHOLD_PROXIMITY (Scheffer Critical Transitions): Cost curves hitting inflection points, performance benchmarks being breached, technology metrics approaching critical thresholds
2. EXTERNAL_PRESSURE (Geels Multi-Level Perspective): Geopolitical events, regulatory pressure, supply chain disruptions, social movements creating windows of opportunity
3. TECH_CYCLE_POSITION (Perez Technological Revolutions): VC investment patterns, major acquisitions, shift from research to deployment phase, government policy inclusion
4. INSTITUTIONAL_CHANGE (North Institutional Economics): Regulations being finalized, standards being set, certification systems created, regulatory sandboxes
5. UNCERTAINTY_RESOLUTION (Dixit-Pindyck Real Options): Large contracts signed, government policies locked in, irreversible investments made, competing technologies eliminated

ITEM:
Title: {title}
Abstract: {abstract}
Source: {source} ({source_type})
Date: {date}

Respond in JSON format only:
{{
  "theme_tags": ["tag1", "tag2"],
  "axes": {{
    "threshold_proximity": {{"signal": true/false, "evidence": "one sentence or empty"}},
    "external_pressure": {{"signal": true/false, "evidence": "one sentence or empty"}},
    "tech_cycle_position": {{"signal": true/false, "evidence": "one sentence or empty"}},
    "institutional_change": {{"signal": true/false, "evidence": "one sentence or empty"}},
    "uncertainty_resolution": {{"signal": true/false, "evidence": "one sentence or empty"}}
  }}
}}"""


def get_api_key() -> str:
    """Retrieve API key from environment or macOS keychain."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "anthropic-api-key", "-w"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        print("エラー: ANTHROPIC_API_KEYが見つかりません。", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY='your-key' を設定するか、", file=sys.stderr)
        print("  macOSキーチェーンに 'anthropic-api-key' を登録してください。", file=sys.stderr)
        sys.exit(1)


def score_item(client: anthropic.Anthropic, item: dict) -> dict:
    """Score a single item using Claude API."""
    prompt = SCORING_PROMPT.format(
        title=item.get("title", ""),
        abstract=item.get("abstract", "")[:200],
        source=item.get("source", ""),
        source_type=item.get("source_type", ""),
        date=item.get("publication_date", ""),
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=512,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            # Extract JSON from response (handle markdown code blocks)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            result = json.loads(text)
            return result
        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES - 1:
                print(f"    レート制限。{RETRY_DELAY}秒待機中... (試行 {attempt + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
            else:
                raise
        except (json.JSONDecodeError, Exception) as e:
            if attempt < MAX_RETRIES - 1:
                print(f"    エラー: {e}。リトライ中... (試行 {attempt + 1}/{MAX_RETRIES})")
                time.sleep(2)
            else:
                return {
                    "theme_tags": [],
                    "axes": {
                        axis: {"signal": False, "evidence": ""}
                        for axis in ["threshold_proximity", "external_pressure",
                                     "tech_cycle_position", "institutional_change",
                                     "uncertainty_resolution"]
                    },
                    "error": str(e),
                }


def run(input_path: Path = None) -> Path:
    """Score all items in the latest raw data file."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    if input_path is None:
        # Find the latest raw data file
        raw_files = sorted(DATA_RAW.glob("*.json"), reverse=True)
        if not raw_files:
            print("エラー: data/raw/ にデータファイルがありません。先に collect.py を実行してください。", file=sys.stderr)
            sys.exit(1)
        input_path = raw_files[0]

    print(f"Scoring items from {input_path.name}...")
    with open(input_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    items = raw_data.get("items", [])
    if not items:
        print("エラー: アイテムが0件です。", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=get_api_key())
    scored_items = []

    for i, item in enumerate(items):
        print(f"  [{i + 1}/{len(items)}] {item.get('title', '')[:60]}...")
        score_result = score_item(client, item)

        credibility = CREDIBILITY_WEIGHTS.get(item.get("source_type", ""), 0.4)

        scored_items.append({
            **item,
            "credibility_weight": credibility,
            "theme_tags": score_result.get("theme_tags", []),
            "axes": score_result.get("axes", {}),
            "scored_at": datetime.now().isoformat(),
        })

        # Small delay to be polite to the API
        time.sleep(0.3)

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = DATA_PROCESSED / f"{today}.json"

    output = {
        "scored_at": datetime.now().isoformat(),
        "model": MODEL,
        "total_items": len(scored_items),
        "items": scored_items,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  {len(scored_items)} items scored and saved to {output_path}")
    return output_path


if __name__ == "__main__":
    run()
