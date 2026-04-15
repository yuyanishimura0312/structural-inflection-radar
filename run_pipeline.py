#!/usr/bin/env python3
"""
Structural Inflection Radar — Pipeline Runner

Usage:
  python3 run_pipeline.py --domain energy
  python3 run_pipeline.py --domain energy --skip-collect  # Use existing raw data

Runs the full pipeline: collect → score → aggregate → export
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from collect import run as collect_run
from score import run as score_run
from aggregate import run as aggregate_run
from export_js import run as export_run


def main():
    parser = argparse.ArgumentParser(
        description="Structural Inflection Radar パイプライン実行"
    )
    parser.add_argument(
        "--domain", default="energy",
        help="分析対象分野 (default: energy)"
    )
    parser.add_argument(
        "--skip-collect", action="store_true",
        help="データ収集をスキップして既存データを使用"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="何日前までのデータを収集するか (default: 30)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Structural Inflection Radar")
    print(f"  分野: {args.domain}")
    print(f"  実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    start = time.time()

    # Step 1: Collect
    if not args.skip_collect:
        print(f"\n[1/4] データ収集 (過去{args.days}日間)...")
        raw_path = collect_run(days_back=args.days)
    else:
        print("\n[1/4] データ収集: スキップ（既存データを使用）")

    # Step 2: Score
    print("\n[2/4] LLMスコアリング (Claude API)...")
    processed_path = score_run()

    # Step 3: Aggregate
    print("\n[3/4] テーマ集約 + Δスコア計算...")
    themes_path = aggregate_run()

    # Step 4: Export
    print("\n[4/4] JS エクスポート...")
    export_run()

    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"  完了！ (所要時間: {elapsed:.0f}秒)")
    print(f"  次のステップ:")
    print(f"    git add -A && git commit -m 'update: weekly radar scan' && git push")
    print("=" * 60)


if __name__ == "__main__":
    main()
