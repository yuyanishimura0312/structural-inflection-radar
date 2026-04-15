# Structural Inflection Radar

Structural Inflection Scorer の5軸フレームワークを「逆引き」し、構造的変化点に近づいている新興技術を能動的に発見するレーダーシステム。

## Overview

データソース（学術論文・技術メディア）から構造変化のシグナルを自動収集し、5つの学術理論軸でスコアリング。スコアの**加速度（Δスコア）**が高いテーマを「ホットな技術」として検出する。

**5つの評価軸:**
1. 閾値接近（Scheffer臨界遷移論）
2. 外圧/窓（Geels多層的視座）
3. 技術革命（Perez技術革命論）
4. 制度変化（North制度経済学）
5. 不確実性解消（Dixit-Pindyckリアルオプション理論）

## Quick Start

### Prerequisites

- Python 3.10+
- Anthropic API key (in macOS Keychain or `ANTHROPIC_API_KEY` env var)

### Setup

```bash
pip install -r requirements.txt
```

### Run (Weekly Update — 3 Steps)

```bash
# 1. Run the pipeline
python3 run_pipeline.py --domain energy

# 2. Commit and push
git add -A && git commit -m "update: weekly radar scan" && git push

# 3. Check the dashboard
open https://yuyanishimura0312.github.io/structural-inflection-radar/
```

### Options

```bash
# Skip data collection (use existing raw data)
python3 run_pipeline.py --domain energy --skip-collect

# Change lookback period
python3 run_pipeline.py --domain energy --days 14
```

## Architecture

```
[OpenAlex API] + [HackerNews API]
        ↓
    collect.py        → data/raw/YYYY-MM-DD.json
        ↓
    score.py          → data/processed/YYYY-MM-DD.json  (Claude API)
        ↓
    aggregate.py      → data/themes/latest.json
        ↓
    export_js.py      → themes_data.js
        ↓
    GitHub Pages      → index.html (dashboard)
```

## Data Sources

| Source | Type | Cost | Auth |
|--------|------|------|------|
| OpenAlex | Academic papers | Free | None |
| HackerNews | Tech community | Free | None |

## Related

- [Structural Inflection Scorer](https://yuyanishimura0312.github.io/structural-inflection-scorer/) — Interactive 5-axis scoring tool
- [Research Report](../../../writings/structural-inflection-point-research/reverse-engine-report.md) — Background research
