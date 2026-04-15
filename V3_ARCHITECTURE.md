I now have a thorough understanding of the entire codebase. Let me compile the comprehensive v3 architecture design.

---

## 構造変化レーダー v3 アーキテクチャ設計書

### 現状の全体像

現在のシステムは以下の4つのPythonスクリプトが直列パイプラインを構成している:
- `src/collect.py`: OpenAlex + HackerNews APIからエネルギー分野のデータを収集 -> `data/raw/YYYY-MM-DD.json`
- `src/score.py`: Claude Haiku 4.5でアイテム単位の5軸スコアリング -> `data/processed/YYYY-MM-DD.json`
- `src/aggregate.py`: テーマタグでグルーピング、軸スコア計算、デルタ計算 -> `data/themes/latest.json` + `history.json`
- `src/export_js.py`: latest.json -> `themes_data.js`（フロントエンド用グローバル変数）

主要な制約:
- `history.json`は1つ前のスナップショットのみ保持（N-1との差分しか取れない）
- キーワードは`collect.py`内にハードコードされている（`ENERGY_KEYWORDS`, `HN_KEYWORDS`）
- ドメインの概念はrun_pipeline.pyの`--domain`引数にあるが、実際にはenergyのみ対応
- themes_data.jsは1時点のスナップショットで、時系列は格納されていない

---

## 1. データベース構造の設計

### ファイル配置
```
data/radar.db  (SQLite 3)
```

`.gitignore`に`data/radar.db`を追加し、DBはローカル運用とする。GitHub Pages向けには引き続き`themes_data.js`をエクスポートする。

### テーブル定義

#### (1) domains -- ドメイン管理

```sql
CREATE TABLE domains (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT    NOT NULL UNIQUE,         -- 'energy', 'ai', 'biotech'
    name_ja       TEXT    NOT NULL,                -- '再生可能エネルギー'
    name_en       TEXT    NOT NULL,                -- 'Renewable Energy'
    description   TEXT    DEFAULT '',
    is_active     INTEGER NOT NULL DEFAULT 1,      -- 0=無効化
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
```

#### (2) domain_keywords -- ドメイン別キーワード

```sql
CREATE TABLE domain_keywords (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id     INTEGER NOT NULL REFERENCES domains(id),
    keyword       TEXT    NOT NULL,
    source_type   TEXT    NOT NULL DEFAULT 'all',   -- 'all', 'openalex', 'hackernews'
    is_active     INTEGER NOT NULL DEFAULT 1,
    UNIQUE(domain_id, keyword, source_type)
);
CREATE INDEX idx_domain_keywords_domain ON domain_keywords(domain_id);
```

現在の`ENERGY_KEYWORDS`(15個)と`HN_KEYWORDS`(12個)をそのまま初期データとして投入する。`source_type`で「OpenAlex専用」「HN専用」「両方」を区別する。

#### (3) sources -- データソース管理

```sql
CREATE TABLE sources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT    NOT NULL UNIQUE,          -- 'openalex', 'hackernews'
    name          TEXT    NOT NULL,
    source_type   TEXT    NOT NULL,                 -- 'academic', 'tech_media'
    base_url      TEXT    NOT NULL,
    credibility_weight REAL NOT NULL DEFAULT 0.5,   -- 現在: academic=1.0, tech_media=0.7
    is_active     INTEGER NOT NULL DEFAULT 1
);
```

初期データ: OpenAlex(academic, 1.0), HackerNews(tech_media, 0.7)

#### (4) raw_items -- 収集した生データ

```sql
CREATE TABLE raw_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id   TEXT    NOT NULL,                 -- OpenAlex ID or 'hn-{objectID}'
    domain_id     INTEGER NOT NULL REFERENCES domains(id),
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    title         TEXT    NOT NULL DEFAULT '',
    abstract      TEXT    DEFAULT '',
    url           TEXT    DEFAULT '',
    publication_date TEXT,
    cited_by_count INTEGER DEFAULT 0,
    query_keyword TEXT,
    collected_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    run_id        INTEGER REFERENCES pipeline_runs(id),
    UNIQUE(external_id, domain_id)                 -- 重複収集を防止
);
CREATE INDEX idx_raw_items_domain     ON raw_items(domain_id);
CREATE INDEX idx_raw_items_source     ON raw_items(source_id);
CREATE INDEX idx_raw_items_collected  ON raw_items(collected_at);
CREATE INDEX idx_raw_items_run        ON raw_items(run_id);
```

`UNIQUE(external_id, domain_id)`により、同一アイテムの重複挿入を`INSERT OR IGNORE`で自然に防げる。現在の`seen_ids`セット処理をDB制約に置き換える。

#### (5) scored_items -- スコアリング済みデータ

```sql
CREATE TABLE scored_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_item_id      INTEGER NOT NULL REFERENCES raw_items(id),
    model            TEXT    NOT NULL,              -- 'claude-haiku-4-5-20251001'
    credibility_weight REAL  NOT NULL,
    -- 5軸のsignal (boolean) と evidence (text)
    threshold_proximity_signal   INTEGER NOT NULL DEFAULT 0,
    threshold_proximity_evidence TEXT    DEFAULT '',
    external_pressure_signal     INTEGER NOT NULL DEFAULT 0,
    external_pressure_evidence   TEXT    DEFAULT '',
    tech_cycle_position_signal   INTEGER NOT NULL DEFAULT 0,
    tech_cycle_position_evidence TEXT    DEFAULT '',
    institutional_change_signal  INTEGER NOT NULL DEFAULT 0,
    institutional_change_evidence TEXT   DEFAULT '',
    uncertainty_resolution_signal INTEGER NOT NULL DEFAULT 0,
    uncertainty_resolution_evidence TEXT DEFAULT '',
    error            TEXT    DEFAULT NULL,           -- スコアリング失敗時のエラー
    scored_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    run_id           INTEGER REFERENCES pipeline_runs(id),
    UNIQUE(raw_item_id)                             -- 1アイテム1スコア
);
CREATE INDEX idx_scored_items_raw    ON scored_items(raw_item_id);
CREATE INDEX idx_scored_items_run    ON scored_items(run_id);
```

#### (6) scored_item_tags -- スコアリングで付与されたテーマタグ

```sql
CREATE TABLE scored_item_tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scored_item_id  INTEGER NOT NULL REFERENCES scored_items(id),
    tag             TEXT    NOT NULL,               -- 'perovskite_solar_cells' etc.
    UNIQUE(scored_item_id, tag)
);
CREATE INDEX idx_scored_item_tags_tag ON scored_item_tags(tag);
CREATE INDEX idx_scored_item_tags_scored ON scored_item_tags(scored_item_id);
```

現在の`theme_tags`配列をリレーショナルに分解する。これにより「あるタグに関連する全アイテムを効率的に検索」が可能になる。

#### (7) themes -- テーママスター

```sql
CREATE TABLE themes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id     INTEGER NOT NULL REFERENCES domains(id),
    tag           TEXT    NOT NULL,                 -- 'perovskite_solar_cells'
    name_ja       TEXT    DEFAULT NULL,             -- '太陽電池'（後で手動設定可能）
    first_seen_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    UNIQUE(domain_id, tag)
);
CREATE INDEX idx_themes_domain ON themes(domain_id);
```

テーマは`aggregate`ステップで自動生成される。`name_ja`は現在index.html内の`THEME_NAMES_JA`辞書のデータをDBに移行する。

#### (8) theme_scores -- テーマ別スコアの時系列

```sql
CREATE TABLE theme_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_id        INTEGER NOT NULL REFERENCES themes(id),
    run_id          INTEGER NOT NULL REFERENCES pipeline_runs(id),
    scan_date       TEXT    NOT NULL,               -- 'YYYY-MM-DD'
    item_count      INTEGER NOT NULL DEFAULT 0,
    composite_score REAL    NOT NULL DEFAULT 0,
    composite_delta REAL    DEFAULT NULL,            -- 前回との差分
    UNIQUE(theme_id, scan_date)
);
CREATE INDEX idx_theme_scores_theme ON theme_scores(theme_id);
CREATE INDEX idx_theme_scores_date  ON theme_scores(scan_date);
```

これが`history.json`の代替となるコアテーブル。`scan_date`を主キーの一部とすることで、同一テーマの時系列を自然に蓄積する。

#### (9) theme_axes -- テーマ x 5軸の時系列スコア

```sql
CREATE TABLE theme_axes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_score_id  INTEGER NOT NULL REFERENCES theme_scores(id),
    axis            TEXT    NOT NULL,               -- 'threshold_proximity' etc.
    score           REAL    NOT NULL DEFAULT 0,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    delta           REAL    DEFAULT NULL,
    UNIQUE(theme_score_id, axis)
);
CREATE INDEX idx_theme_axes_score ON theme_axes(theme_score_id);
```

#### (10) theme_evidence -- テーマ x 軸ごとのエビデンス

```sql
CREATE TABLE theme_evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_score_id  INTEGER NOT NULL REFERENCES theme_scores(id),
    axis            TEXT    NOT NULL,
    evidence_text   TEXT    NOT NULL,
    source_item_id  INTEGER REFERENCES raw_items(id)
);
CREATE INDEX idx_theme_evidence_score ON theme_evidence(theme_score_id);
```

#### (11) pipeline_runs -- パイプライン実行履歴

```sql
CREATE TABLE pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id       INTEGER NOT NULL REFERENCES domains(id),
    started_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    completed_at    TEXT    DEFAULT NULL,
    status          TEXT    NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'failed'
    -- ステップ別の進捗
    collect_count   INTEGER DEFAULT NULL,
    score_count     INTEGER DEFAULT NULL,
    score_error_count INTEGER DEFAULT NULL,
    theme_count     INTEGER DEFAULT NULL,
    -- メタ情報
    days_back       INTEGER DEFAULT 30,
    model           TEXT    DEFAULT NULL,
    error_message   TEXT    DEFAULT NULL,
    -- コスト推計
    api_calls       INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0
);
CREATE INDEX idx_pipeline_runs_domain ON pipeline_runs(domain_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
```

### ER関係の要約

```
domains 1--* domain_keywords
domains 1--* raw_items
domains 1--* themes
sources 1--* raw_items
raw_items 1--1 scored_items
scored_items 1--* scored_item_tags
themes 1--* theme_scores
theme_scores 1--* theme_axes
theme_scores 1--* theme_evidence
pipeline_runs 1--* raw_items
pipeline_runs 1--* scored_items
pipeline_runs 1--* theme_scores
```

### マイグレーション戦略

新規ファイル `src/db.py` にDB初期化・マイグレーション関数を集約する。`db.py`が`import`されるたびにテーブルの存在を確認し、なければCREATEする（`CREATE TABLE IF NOT EXISTS`パターン）。既存JSONデータのインポート用に `src/migrate_json_to_db.py` を別途用意する。

---

## 2. パイプラインの改修計画

### 2.1 新規ファイル: `src/db.py` (データベースレイヤー)

責務:
- `get_connection()`: `data/radar.db`へのSQLite接続を返す（WALモード有効）
- `init_db()`: 全テーブルのCREATE IF NOT EXISTS
- `seed_data()`: 初期ドメイン・ソース・キーワードの投入
- 各テーブルへのCRUD関数群

重要な設計判断: パイプライン各ステップは「既存JSONフローを維持しつつDBにも書き込む」デュアルライト方式とする。これにより:
- 移行期間中はJSON出力も継続でき、動作検証が可能
- GitHub Pagesのthemes_data.jsフローは一切影響を受けない
- 将来的にJSON出力を完全に廃止可能

### 2.2 collect.py の改修

変更点:
1. キーワードのハードコードを廃止し、`domain_keywords`テーブルから取得
2. 収集結果を`raw_items`テーブルにINSERT (`INSERT OR IGNORE`で重複回避)
3. `pipeline_runs`テーブルの`collect_count`を更新
4. **互換性維持**: 既存のJSON出力(`data/raw/YYYY-MM-DD.json`)も引き続き生成

具体的な改修箇所:
- `ENERGY_KEYWORDS`定数 -> `db.get_keywords(domain_id, source_type='openalex')`
- `HN_KEYWORDS`定数 -> `db.get_keywords(domain_id, source_type='hackernews')`
- `run()`関数の末尾にDB書き込みを追加
- `run()`関数のシグネチャに`domain_slug: str`パラメータを追加

### 2.3 score.py の改修

変更点:
1. 入力を`raw_items`テーブルから取得（`scored_items`に既にある項目はスキップ）
2. スコアリング結果を`scored_items`テーブルと`scored_item_tags`テーブルに書き込み
3. `pipeline_runs`の`score_count`, `score_error_count`, `api_calls`, `estimated_cost_usd`を更新
4. **互換性維持**: 既存のJSON出力も引き続き生成

増分スコアリング対応が大きな改善点。現在は毎回全アイテムをスコアリングしているが、DB化により「未スコアリングのアイテムのみ処理」が可能になる。これによりAPIコストが大幅に削減される。

```python
# 改修後のロジック概要
unscored = db.get_unscored_items(domain_id)  # raw_items LEFT JOIN scored_items WHERE scored_items.id IS NULL
for item in unscored:
    result = score_item(client, item)
    db.insert_scored_item(item['id'], result, run_id)
```

### 2.4 aggregate.py の改修

変更点:
1. 入力を`scored_items` + `scored_item_tags`テーブルから取得
2. テーマ集約ロジック自体は現在の`aggregate_themes()`をほぼそのまま維持
3. 集約結果を`themes`, `theme_scores`, `theme_axes`, `theme_evidence`テーブルに書き込み
4. デルタ計算: `history.json`の代わりに`theme_scores`テーブルの前回レコードから差分を計算
5. **互換性維持**: `data/themes/latest.json`と`data/themes/history.json`も引き続き生成

デルタ計算の改善:
```sql
-- 前回のスコアを取得
SELECT ts.composite_score, ta.axis, ta.score
FROM theme_scores ts
JOIN theme_axes ta ON ta.theme_score_id = ts.id
WHERE ts.theme_id = ? AND ts.scan_date < ?
ORDER BY ts.scan_date DESC
LIMIT 1
```

これにより、N-1だけでなくN-2, N-3...との比較も可能になり、トレンド分析の幅が広がる。

### 2.5 export_js.py の改修

変更点:
1. 入力をDBから取得（`themes`, `theme_scores`, `theme_axes`, `theme_evidence`を結合）
2. **時系列データの追加**: `themes_data.js`のデータ構造に`history`配列を追加

改修後のthemes_data.jsの構造:
```javascript
const THEMES_DATA = {
  generated_at: "2026-04-15T...",
  total_themes: 83,
  total_source_items: 178,
  domains: ["energy"],  // 新規
  themes: [
    {
      name: "geothermal_energy",
      domain: "energy",  // 新規
      item_count: 2,
      composite_score: 1.0,
      axes: { ... },  // 既存と同一構造
      source_items: [ ... ],
      delta: { ... },
      history: [  // 新規: 時系列データ
        { date: "2026-04-08", composite_score: 0.85, axes: { ... } },
        { date: "2026-04-15", composite_score: 1.0, axes: { ... } },
      ]
    }
  ],
  pipeline_stats: {  // 新規: ダッシュボード用
    last_run: "2026-04-15T19:25:55",
    total_runs: 3,
    last_collect_count: 178,
    last_score_count: 178,
    last_score_error_count: 0,
    estimated_total_cost_usd: 0.45
  }
};
```

`history`配列は直近12回分に制限する（3ヶ月分、容量制約）。

### 2.6 run_pipeline.py の改修

変更点:
1. `--domain`引数を実質的に機能させる（DBからドメイン設定を取得）
2. パイプライン開始時に`pipeline_runs`レコードを作成
3. 各ステップの結果で`pipeline_runs`を更新
4. 完了/失敗ステータスの記録
5. 新規引数`--init-db`でDB初期化を実行

```python
# 改修後のフロー
run_id = db.create_pipeline_run(domain_id, days_back)
try:
    collect_count = collect_run(domain_id=domain_id, days_back=args.days, run_id=run_id)
    score_count, error_count = score_run(domain_id=domain_id, run_id=run_id)
    theme_count = aggregate_run(domain_id=domain_id, run_id=run_id)
    export_run(domain_id=domain_id)
    db.complete_pipeline_run(run_id, status='completed')
except Exception as e:
    db.complete_pipeline_run(run_id, status='failed', error=str(e))
    raise
```

### 2.7 新規ファイル: `src/migrate_json_to_db.py`

既存のJSONデータをDBにインポートするワンタイムスクリプト。

処理内容:
1. `data/raw/2026-04-15.json` -> `raw_items`テーブル
2. `data/processed/2026-04-15.json` -> `scored_items` + `scored_item_tags`テーブル
3. `data/themes/latest.json` -> `themes` + `theme_scores` + `theme_axes` + `theme_evidence`テーブル
4. `data/themes/history.json` -> `theme_scores`テーブル（過去スナップショット）
5. index.html内の`THEME_NAMES_JA`辞書 -> `themes.name_ja`カラム

---

## 3. 管理ダッシュボードの設計

### 3.1 技術選定

GitHub Pagesで公開するため、静的HTML+JSのアプローチを維持する。DBはローカルのSQLiteであり、ブラウザから直接アクセスできない。そのため:

- **データ供給方式**: `export_js.py`が`themes_data.js`に加えて`dashboard_data.js`を出力
- **チャートライブラリ**: 既にindex.htmlで使用しているECharts 5（CDN）をそのまま活用
- **ルーティング**: 単一HTMLファイル内のタブ切替（既存のindex.htmlのパターンを踏襲）

### 3.2 ファイル構成

```
dashboard.html          -- 管理ダッシュボード
dashboard_data.js       -- DB→JSエクスポート（export_js.pyが生成）
```

`dashboard.html`は`index.html`と同一のesse-senseダークブラウンテーマを共有する。CSSカスタムプロパティ(`--color-bg-page: #3A2A20` 等)をそのまま再利用する。

### 3.3 dashboard_data.js の構造

```javascript
const DASHBOARD_DATA = {
  generated_at: "2026-04-15T20:00:00",
  
  // 概要
  overview: {
    total_domains: 1,
    total_themes: 83,
    total_source_items: 178,
    total_pipeline_runs: 3,
    last_updated: "2026-04-15T19:25:55"
  },
  
  // ドメイン一覧
  domains: [
    {
      slug: "energy",
      name_ja: "再生可能エネルギー",
      keyword_count: 15,
      theme_count: 83,
      item_count: 178,
      avg_composite_score: 0.52,
      last_run: "2026-04-15T19:25:55"
    }
  ],
  
  // パイプライン実行履歴（直近20回）
  pipeline_runs: [
    {
      id: 1,
      domain: "energy",
      started_at: "2026-04-15T18:00:00",
      completed_at: "2026-04-15T19:25:55",
      status: "completed",
      collect_count: 178,
      score_count: 178,
      score_error_count: 0,
      theme_count: 83,
      api_calls: 178,
      estimated_cost_usd: 0.15
    }
  ],
  
  // テーマ時系列データ（全テーマ、直近12回分）
  theme_timeseries: {
    dates: ["2026-04-01", "2026-04-08", "2026-04-15"],
    themes: {
      "geothermal_energy": {
        name_ja: "地熱エネルギー",
        scores: [null, 0.85, 1.0],
        axes: {
          threshold_proximity: [null, 0.8, 1.0],
          external_pressure: [null, 0.9, 1.0],
          // ...
        }
      }
    }
  },
  
  // データ品質メトリクス
  quality: {
    score_success_rate: 0.98,
    avg_theme_item_count: 2.14,
    themes_with_single_item: 0,  // 2件未満フィルタ後
    total_api_calls: 178,
    total_estimated_cost_usd: 0.15,
    model: "claude-haiku-4-5-20251001"
  }
};
```

### 3.4 ページ構成

ダッシュボードは4つのタブで構成する。既存のindex.htmlの`.view-tabs`パターンを再利用する。

#### タブ1: 概要 (Overview)

レイアウト:
```
[KPIカード x 4]  ドメイン数 | テーマ数 | ソース件数 | 最終更新
[パイプライン実行履歴テーブル]  直近10回の実行状況（ステータス、件数、コスト）
[アクティビティタイムライン]  直近の実行をカード形式で表示
```

KPIカードのデザイン: `index.html`の`.theme-card`を小型化した`.kpi-card`。数値を大きく表示し、ラベルを小さく下部に配置する。

パイプライン実行履歴テーブル: HTMLテーブルで直近10回を表示。ステータスは色付きバッジ（completed=緑系, failed=赤系, running=アクセント色）。

#### タブ2: ドメイン管理 (Domains)

レイアウト:
```
[ドメインカード x N]
  各カード内:
    - ドメイン名（日英）
    - キーワード一覧（タグ形式）
    - 統計: テーマ数、アイテム数、平均スコア
    - 最終実行日時
```

注意: 管理ダッシュボードは静的HTMLなので、ドメインの追加・キーワードの編集はできない。あくまで「閲覧用」。設定変更は`python3 -c "from src.db import ...; ..."`やSQLiteクライアントで直接行う。将来的にはCLIツール（`python3 manage.py add-domain ai ...`）を追加する。

#### タブ3: テーマ時系列 (Theme Trends)

レイアウト:
```
[テーマ選択ドロップダウン] (複数選択、最大5件)
[メインチャート: 折れ線グラフ]  X軸=日付、Y軸=composite_score
[サブチャート: 5軸レーダー小さめ x 選択テーマ数]  各時点のレーダーを並列表示
```

EChartsの折れ線グラフ（`type: 'line'`）で実装。テーマ選択はindex.htmlのレーダー比較ビューの`.radar-selector`パターンを再利用する。

#### タブ4: データ品質 (Data Quality)

レイアウト:
```
[KPIカード x 4]  成功率 | エラー率 | 平均テーマアイテム数 | 累計APIコスト
[スコアリングモデル情報]  使用モデル、パラメータ
[エラーログ]  直近のスコアリングエラー一覧（あれば）
[コスト推移グラフ]  パイプライン実行ごとの推定コスト推移
```

APIコスト推計: Haiku 4.5のトークン単価(入力$0.80/Mトークン, 出力$4.00/Mトークン)をベースに、`score.py`の`max_tokens=512`設定とプロンプト長から概算する。1アイテムあたり約$0.0008と推定。

### 3.5 デザイン仕様

既存のindex.htmlのCSSカスタムプロパティをそのまま複製する:
- `--color-bg-page: #3A2A20` (ダークブラウン背景)
- `--color-bg-card: #FFFAF6` (カード背景)
- `--color-accent: #7A4033` (アクセント)
- フォント: `-apple-system, BlinkMacSystemFont, "Hiragino Sans" ...`

ヘッダーに「← レーダーに戻る」リンクを配置し、index.htmlとdashboard.htmlの相互ナビゲーションを提供する。

---

## 4. 実装優先度とステップ

### Phase 1: DB基盤 + マイグレーション (推定: 半日)

**目標**: DBスキーマを確立し、既存データをインポートする

1. `src/db.py` を新規作成（テーブル定義、init_db(), seed_data()）
2. `src/migrate_json_to_db.py` を新規作成（JSON -> DB インポート）
3. `.gitignore` に `data/radar.db` を追加
4. `requirements.txt` は変更不要（sqlite3はPython標準ライブラリ）
5. テスト: DBが正しく作成され、既存データがインポートされることを確認

### Phase 2: パイプラインのDB対応 (推定: 1日)

**目標**: 4スクリプトがDBに読み書きしつつ、既存JSONフローも維持する

1. `src/collect.py` の改修（キーワードDB取得 + raw_items書き込み）
2. `src/score.py` の改修（増分スコアリング + scored_items書き込み）
3. `src/aggregate.py` の改修（DB入力 + theme_scores時系列書き込み）
4. `src/export_js.py` の改修（DB入力 + themes_data.jsに時系列追加）
5. `run_pipeline.py` の改修（pipeline_runs記録）
6. テスト: `python3 run_pipeline.py --domain energy` が正常に完走し、DB・JSON両方に出力されることを確認

### Phase 3: themes_data.js 時系列対応 + index.html改修 (推定: 半日)

**目標**: フロントエンドで時系列データを表示可能にする

1. `export_js.py`で`history`配列を`themes_data.js`に追加
2. `index.html`のモーダル内にスコア推移折れ線グラフを追加（ECharts）
3. テスト: 複数回パイプラインを実行した後、モーダルでグラフが表示されることを確認

### Phase 4: 管理ダッシュボード (推定: 1日)

**目標**: パイプライン状態の可視化

1. `dashboard_data.js` のエクスポートを`export_js.py`に追加
2. `dashboard.html` を新規作成（4タブ構成）
3. テスト: ダッシュボードの各タブでデータが正しく表示されることを確認

### Phase 5: マルチドメイン対応 (推定: 半日)

**目標**: energy以外のドメインを追加可能にする

1. `db.py`にドメイン追加用のCLI関数を追加
2. 全パイプラインスクリプトの`domain_id`パラメータが正しく機能することを確認
3. テスト用に`ai`ドメインを追加してパイプラインを実行
4. `index.html`にドメイン切替UIを追加（将来タスク）

---

## 5. 技術的な注意事項

**SQLite WALモード**: `PRAGMA journal_mode=WAL;`を接続時に設定する。これにより読み取りと書き込みが並行可能になり、パイプライン実行中のダッシュボード確認でロックが発生しない。

**DB容量の目安**: 1回のパイプライン実行で約200アイテム、52週/年で約10,400行/年。5ドメインでも年間約50,000行程度。SQLiteは数百万行まで問題なく扱えるため、容量は懸念事項にならない。

**テーマ名の日本語化**: 現在の`THEME_NAMES_JA`辞書（index.html内、約80エントリ）を`themes.name_ja`カラムに移行する。`export_js.py`でDBから取得し、`themes_data.js`に含める。これによりindex.html内のハードコードを削減できる。

**既存のGitHub Pagesデプロイフローへの影響**: `themes_data.js`の構造に`history`と`pipeline_stats`が追加されるが、既存のフロントエンドコードは未知のプロパティを無視するため、後方互換性は維持される。

---

### Critical Files for Implementation
- `/Users/nishimura+/projects/research/structural-inflection-radar/src/collect.py`
- `/Users/nishimura+/projects/research/structural-inflection-radar/src/aggregate.py`
- `/Users/nishimura+/projects/research/structural-inflection-radar/src/export_js.py`
- `/Users/nishimura+/projects/research/structural-inflection-radar/run_pipeline.py`
- `/Users/nishimura+/projects/research/structural-inflection-radar/index.html`