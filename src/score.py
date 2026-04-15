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

SCORING_PROMPT = """あなたは技術予測と構造変化分析の厳格な審査官です。
以下のアイテムを分析し、構造的変曲点の5軸に関連する**具体的で明確な**シグナルが含まれているか判定してください。

重要な判定基準:
- signalはデフォルトでfalseにしてください。明確な根拠がある場合のみtrueにしてください
- 一般的な技術動向の記述や、単なる研究発表はシグナルではありません
- 具体的な数値（コスト削減率、投資額、採用率）、固有名詞（企業名、法規制名）、時期の特定がある場合のみシグナルと判定してください
- 学術論文のサーベイ・レビュー・メタ分析は、それ自体はシグナルではありません
- 5軸のうち該当するのは通常0〜2軸です。3軸以上にシグナルがあるケースは稀です

5軸の定義:
1. THRESHOLD_PROXIMITY（臨界閾値接近）: コスト曲線の変曲点到達（具体的な数値あり）、性能ベンチマークの突破（何が何を超えたか明示）、技術指標の臨界閾値への接近
2. EXTERNAL_PRESSURE（外圧・機会の窓）: 特定の地政学的イベント、具体的な規制措置、サプライチェーンの具体的混乱、社会運動による政策変更
3. TECH_CYCLE_POSITION（技術サイクル位置）: 具体的なVC投資ラウンド・金額、特定企業の大型買収、政府の具体的政策決定、研究段階から商用展開への移行事例
4. INSTITUTIONAL_CHANGE（制度変化）: 具体的な規制の確定・施行、特定の標準の策定・採択、認証制度の創設、規制サンドボックスの設置
5. UNCERTAINTY_RESOLUTION（不確実性解消）: 特定の大型契約締結、政府方針の確定、不可逆的投資の実行（具体的金額）、競合技術の市場からの排除

アイテム:
タイトル: {title}
概要: {abstract}
ソース: {source} ({source_type})
日付: {date}

theme_tagsは英語の短いタグ（snake_case）で、このアイテムの技術テーマを1〜3個返してください。
evidenceは必ず日本語で記述してください。シグナルなしの場合は空文字にしてください。
JSONフォーマットのみで回答してください:
{{
  "theme_tags": ["tag1", "tag2"],
  "axes": {{
    "threshold_proximity": {{"signal": true/false, "evidence": "具体的根拠を日本語で1文、またはシグナルなしなら空文字"}},
    "external_pressure": {{"signal": true/false, "evidence": "具体的根拠を日本語で1文、またはシグナルなしなら空文字"}},
    "tech_cycle_position": {{"signal": true/false, "evidence": "具体的根拠を日本語で1文、またはシグナルなしなら空文字"}},
    "institutional_change": {{"signal": true/false, "evidence": "具体的根拠を日本語で1文、またはシグナルなしなら空文字"}},
    "uncertainty_resolution": {{"signal": true/false, "evidence": "具体的根拠を日本語で1文、またはシグナルなしなら空文字"}}
  }}
}}"""


def get_api_key() -> str:
    """Retrieve API key from environment or macOS keychain."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "ANTHROPIC_API_KEY", "-w"],
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
    """Score all items in the latest raw data file. Supports resume from checkpoint."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    if input_path is None:
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

    # Use input file's date stem for output/checkpoint (survives midnight)
    date_stem = input_path.stem  # e.g. "2026-04-15"
    output_path = DATA_PROCESSED / f"{date_stem}.json"
    checkpoint_path = DATA_PROCESSED / f"{date_stem}.checkpoint.json"

    # Resume from checkpoint if available
    scored_items = []
    scored_ids = set()
    if checkpoint_path.exists():
        with open(checkpoint_path, encoding="utf-8") as f:
            checkpoint = json.load(f)
        scored_items = checkpoint.get("items", [])
        scored_ids = {item["id"] for item in scored_items}
        print(f"  チェックポイントから再開: {len(scored_items)}/{len(items)}件完了済み")

    client = anthropic.Anthropic(api_key=get_api_key())

    for i, item in enumerate(items):
        if item["id"] in scored_ids:
            continue  # Already scored

        title = item.get('title') or '(no title)'
        print(f"  [{i + 1}/{len(items)}] {title[:60]}...")
        score_result = score_item(client, item)

        credibility = CREDIBILITY_WEIGHTS.get(item.get("source_type", ""), 0.4)

        scored_items.append({
            **item,
            "credibility_weight": credibility,
            "theme_tags": score_result.get("theme_tags", []),
            "axes": score_result.get("axes", {}),
            "scored_at": datetime.now().isoformat(),
        })
        scored_ids.add(item["id"])

        # Save checkpoint every 50 items
        if len(scored_items) % 50 == 0:
            _save_checkpoint(checkpoint_path, scored_items)
            print(f"    [checkpoint] {len(scored_items)}/{len(items)}件保存")

        time.sleep(0.3)

    # Final output
    output = {
        "scored_at": datetime.now().isoformat(),
        "model": MODEL,
        "total_items": len(scored_items),
        "items": scored_items,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Remove checkpoint after successful completion
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    print(f"  {len(scored_items)} items scored and saved to {output_path}")
    return output_path


def _save_checkpoint(path: Path, items: list):
    """Save intermediate progress to a checkpoint file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"items": items, "saved_at": datetime.now().isoformat()}, f, ensure_ascii=False)


if __name__ == "__main__":
    run()
