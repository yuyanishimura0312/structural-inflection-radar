必要な情報が揃いました。包括的な調査結果をまとめます。

---

# 構造変化レーダー（Structural Inflection Radar）領域拡張リサーチ報告

## はじめに：現在の設計の把握

collect.pyを精読した上で、設計の全体像を確認しました。現在のシステムはOpenAlexとHackerNewsの2ソースのみを対象とし、キーワードリストはスクリプトの冒頭に`ENERGY_KEYWORDS`と`HN_KEYWORDS`というグローバル変数として直接埋め込まれています。`fetch_openalex()`と`fetch_hackernews()`の2つの関数はそれぞれハードコードされたキーワードリストを参照しており、新しい技術領域を追加しようとすると関数そのものを書き換えなければならない構造です。score.pyのClaudeによる分析プロンプトも現状は「技術予測と構造変化分析」という汎用的な枠組みで書かれており、領域拡張自体はスコアリング側への影響が少ない、という整理になります。

---

## 1. 追加すべき技術領域の提案

### 領域A：AI・エージェント技術（Artificial Intelligence / Agentic Systems）

構造変化レーダーへの適性は非常に高いと判断します。理由は、LLMの性能曲線（コスト/トークン比）が指数的に改善しており「閾値接近」シグナルが頻繁に発生していること、VC投資の集中と規制整備（EU AI Act施行）が「外圧/窓」と「制度変化」の両軸に同時に働いていること、そして自律エージェントへの移行という「技術革命フェーズ転換」が観測されていることが挙げられます。変化の速度が速く、かつ変化点が明確に記録されているため、デルタスコアの検出精度が高い領域です。

OpenAlex検索キーワード（10〜15語）:
```
"large language model", "autonomous agent", "AI reasoning",
"foundation model", "multimodal AI", "AI inference",
"AI chip architecture", "neural scaling law", "AI alignment",
"retrieval augmented generation", "AI benchmark",
"machine learning efficiency", "transformer architecture",
"agentic AI", "AI deployment"
```

HackerNews検索キーワード（5〜10語）:
```
"LLM", "GPT", "Claude", "AI agent", "inference",
"foundation model", "AI chip", "reasoning model", "benchmark"
```

---

### 領域B：バイオテクノロジー・合成生物学（Biotechnology / Synthetic Biology）

CRISPRの臨床応用承認（2023年のCasgevy承認）、GLP-1医薬品市場の爆発的拡大、合成生物学によるバイオマニュファクチャリングの台頭が重なっており、「閾値接近」と「不確実性解消」の両シグナルが高い領域です。mRNAプラットフォームのCOVID後の転用（がんワクチン等）も「技術革命フェーズ転換」の典型例です。学術論文の発表速度が速く、OpenAlexとの相性が特に良い領域です。

OpenAlex検索キーワード:
```
"CRISPR gene editing", "mRNA therapeutics", "synthetic biology",
"cell therapy", "gene drive", "protein engineering",
"biosynthesis pathway", "metabolic engineering",
"precision medicine", "longevity biology",
"GLP-1 receptor agonist", "base editing",
"organoid", "biofoundry", "directed evolution"
```

HackerNews検索キーワード:
```
"CRISPR", "gene therapy", "synthetic biology", "mRNA",
"longevity", "biotech", "protein folding", "cell therapy"
```

---

### 領域C：量子技術（Quantum Technologies）

量子コンピュータは2025年現在、「エラー訂正の実用化」という具体的な閾値に向けた加速段階にあります。GoogleのWillow、IBMのCondorなど各社のロードマップが具体化しており、VC投資と政府プログラム（米欧日中の国家量子イニシアチブ）が重なる「外圧/窓」が明確です。量子通信（QKD）の商業展開も進んでおり、「制度変化」シグナルが検出しやすい領域です。

OpenAlex検索キーワード:
```
"quantum error correction", "quantum advantage",
"fault tolerant quantum computing", "qubit coherence time",
"quantum key distribution", "quantum networking",
"superconducting qubit", "photonic quantum computing",
"quantum simulation", "topological qubit",
"quantum sensing", "quantum algorithm",
"neutral atom quantum", "quantum memory", "post quantum cryptography"
```

HackerNews検索キーワード:
```
"quantum computing", "qubit", "quantum error correction",
"quantum supremacy", "quantum chip", "post-quantum"
```

---

### 領域D：宇宙商業技術（Commercial Space Technology）

SpaceXのStarshipによる再使用型大型ロケットの量産化、Starlink等の衛星コンステレーションの商業化、LEO軌道の「インフラ化」という構造変化が進行中です。打ち上げコストの急落（コスト曲線の変曲点）は「閾値接近」の典型であり、また軌道デブリ規制や周波数割り当てという「制度変化」の進行も検出対象として明確です。

OpenAlex検索キーワード:
```
"reusable launch vehicle", "satellite constellation",
"small satellite", "space debris mitigation",
"in-situ resource utilization", "lunar economy",
"space manufacturing", "orbital refueling",
"earth observation satellite", "direct to cell satellite",
"launch cost reduction", "commercial space station",
"CubeSat", "mega constellation", "space sustainability"
```

HackerNews検索キーワード:
```
"Starship", "Starlink", "rocket launch", "satellite internet",
"space station", "lunar", "small sat"
```

---

### 領域E：半導体・先端製造（Advanced Semiconductors / Manufacturing）

2nmプロセスノード、チップレット（UCIe標準）、EUV/High-NA EUVという製造技術革新が「閾値接近」を構成しています。米中の輸出規制と地政学的サプライチェーン再編が強力な「外圧/窓」として機能しており、CHIPS法等の産業政策が「制度変化」シグナルを生み出しています。この領域はHackerNewsの技術コミュニティでの言及量が特に多く、HNシグナルの感度が高い点も推薦の理由です。

OpenAlex検索キーワード:
```
"2nm semiconductor", "chiplet architecture",
"EUV lithography", "advanced packaging",
"3D IC integration", "silicon photonics",
"TSMC leading edge", "gate all around transistor",
"semiconductor supply chain", "AI accelerator chip",
"wafer bonding", "UCIe standard",
"power delivery network", "memory bandwidth", "HBM memory"
```

HackerNews検索キーワード:
```
"TSMC", "chiplet", "EUV", "semiconductor", "AI chip",
"NVIDIA", "HBM", "advanced packaging", "fab"
```

---

### 優先度まとめ

5領域の中で、構造変化レーダーへの適合度として最も高いのはAI・エージェント技術と半導体です。変化点が明確で、OpenAlexとHackerNewsの両方からシグナルが取れるためです。バイオテクノロジーは学術論文量が多く、OpenAlex単独でも高密度のデータが得られます。量子技術と宇宙商業はシグナルが明確なものの、変化の時間スケールが長めのため、30日単位のデルタ検出には若干のノイズが混じる可能性があります。

---

## 2. データソース拡張の提案

### arXiv API（最優先推薦）

認証不要、APIキー不要、Python requestsで直接アクセス可能という条件をすべて満たす最良のデータソースです。リクエスト間隔3秒以上というポリシーさえ守れば安定して使えます。エンドポイントは`http://export.arxiv.org/api/query`で、`search_query`パラメータでキーワード指定し、`max_results`で件数を制限します。レスポンスはAtom XML形式のため`xml.etree.ElementTree`で解析します。OpenAlexと比較してプレプリント（査読前論文）を拾える点が強みで、速報性において数週間〜数ヶ月早くシグナルを検出できます。クレジビリティウェイトはOpenAlex（重み1.0）より低い0.8程度が適切です。

### Crossref API（準推薦）

認証不要（mailtoヘッダー付与で高速プールに入れる）、1秒50リクエストという高いレート上限を持つ学術メタデータAPIです。OpenAlexのカバレッジを補完する役割として使えますが、abstractが含まれないケースが多く、score.pyのClaudeスコアリングがタイトルのみになる場合があります。このため、まずarXivを優先し、Crossrefは必要に応じてDOI解決用の補助ソースとして位置づけることを推薦します。

### Reddit API（条件付き推薦）

技術コミュニティ（r/MachineLearning、r/QuantumComputing、r/SpaceXなど）の熱量を検出できるHackerNewsの補完ソースとして有力です。無料利用は個人・学術用途に限定されており、OAuth認証（クライアントID・シークレット取得）が必要です。PRAWライブラリで扱いやすいものの、APIキー取得の手間があるため、まずHackerNews拡張で対応し、後続フェーズでRedditを追加する段階的アプローチを推薦します。

### GitHub Trending（非推薦）

公式APIが存在せず、スクレイピングのみ対応です。GitHubの利用規約上スクレイピングはグレーゾーンであり、HTMLの構造変更により突然壊れるリスクがあります。技術トレンドの補完として魅力的ではありますが、安定性の観点から本番パイプラインへの組み込みは推薦しません。

### PatentsView API（将来的推薦）

新しいPatentSearch API（`search.patentsview.org`）はAPIキーが必要ですが、無料で取得可能です。特許データは「不確実性解消」軸（大型投資・不可逆的コミットメント）の強力なシグナルになります。ただし、特許公開から実態の変化までのタイムラグが長い（1〜2年）ため、30日デルタ検出への貢献は限定的です。将来のバッチ分析用として位置づけるのが適切です。

---

## 3. collect.pyの改修設計案

現在のcollect.pyは「エネルギー専用」のシングルドメイン設計ですが、以下の方針でマルチドメイン対応に改修します。

### 設計方針：ドメイン設定ファイルの外部化

キーワードをコードに直接書くのをやめ、`domains/`ディレクトリ以下のYAMLファイルに移します。これにより、エンジニアでなくても新しい領域を追加でき、コードを一切触らずに設定のみで拡張できます。

```
src/
  collect.py          # 改修後（ドメイン設定を読み込む汎用コア）
  sources/
    openalex.py       # OpenAlexフェッチャー（プラグイン）
    hackernews.py     # HackerNewsフェッチャー（プラグイン）
    arxiv.py          # arXivフェッチャー（新規追加）
domains/
  energy.yaml         # 既存のエネルギー領域
  ai_agents.yaml      # AI/エージェント領域（新規）
  biotech.yaml        # バイオテク領域（新規）
  quantum.yaml        # 量子技術領域（新規）
  space.yaml          # 宇宙商業領域（新規）
  semiconductors.yaml # 半導体領域（新規）
```

### ドメインYAMLの構造例（`domains/ai_agents.yaml`）

```yaml
domain_id: ai_agents
domain_name_ja: "AI・エージェント技術"
domain_name_en: "Artificial Intelligence / Agentic Systems"
enabled: true
credibility_override: {}  # ソースタイプごとの信頼度上書き（省略時はデフォルト）

sources:
  openalex:
    keywords:
      - "large language model"
      - "autonomous agent"
      - "AI reasoning"
      - "foundation model"
      - "multimodal AI"
      - "AI inference"
      - "AI chip architecture"
      - "neural scaling law"
      - "AI alignment"
      - "retrieval augmented generation"
      - "AI benchmark"
      - "machine learning efficiency"
      - "transformer architecture"
      - "agentic AI"
      - "AI deployment"
    per_keyword_limit: 10

  hackernews:
    keywords:
      - "LLM"
      - "GPT"
      - "Claude"
      - "AI agent"
      - "inference"
      - "foundation model"
      - "AI chip"
      - "reasoning model"
      - "benchmark"
    per_keyword_limit: 10

  arxiv:
    keywords:
      - "large language model"
      - "autonomous agent"
      - "AI reasoning"
      - "multimodal AI"
      - "AI alignment"
      - "neural scaling"
      - "retrieval augmented"
    categories:
      - "cs.AI"
      - "cs.LG"
      - "cs.CL"
    per_keyword_limit: 8
```

### collect.pyのコア構造（改修案）

```python
# collect.py（改修案：概念レベルの設計）

import yaml
from pathlib import Path

DOMAINS_DIR = Path(__file__).parent.parent / "domains"

def load_domains(domain_filter: list[str] = None) -> list[dict]:
    """domains/ 以下の有効なYAMLをすべて読み込む。
    domain_filterが指定された場合は対象domain_idのみ読む。"""
    domains = []
    for yaml_path in sorted(DOMAINS_DIR.glob("*.yaml")):
        with open(yaml_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if not cfg.get("enabled", True):
            continue
        if domain_filter and cfg["domain_id"] not in domain_filter:
            continue
        domains.append(cfg)
    return domains


def run(days_back: int = 30, domains: list[str] = None) -> Path:
    """全ドメインのデータを収集してまとめて保存。"""
    domain_configs = load_domains(domain_filter=domains)

    all_items = []
    for domain_cfg in domain_configs:
        domain_id = domain_cfg["domain_id"]
        print(f"\n[{domain_id}] 収集開始...")

        # OpenAlex
        oa_items = fetch_openalex(
            keywords=domain_cfg["sources"]["openalex"]["keywords"],
            per_keyword_limit=domain_cfg["sources"]["openalex"]["per_keyword_limit"],
            days_back=days_back,
            domain_id=domain_id,
        )
        all_items.extend(oa_items)

        # HackerNews
        hn_items = fetch_hackernews(
            keywords=domain_cfg["sources"]["hackernews"]["keywords"],
            per_keyword_limit=domain_cfg["sources"]["hackernews"]["per_keyword_limit"],
            days_back=days_back,
            domain_id=domain_id,
        )
        all_items.extend(hn_items)

        # arXiv（sources.arxivキーが存在する場合のみ）
        if "arxiv" in domain_cfg.get("sources", {}):
            ax_items = fetch_arxiv(
                keywords=domain_cfg["sources"]["arxiv"]["keywords"],
                categories=domain_cfg["sources"]["arxiv"].get("categories", []),
                per_keyword_limit=domain_cfg["sources"]["arxiv"]["per_keyword_limit"],
                days_back=days_back,
                domain_id=domain_id,
            )
            all_items.extend(ax_items)

    # 保存（既存と同形式を維持）
    ...
```

各フェッチャー関数はキーワードリストと`domain_id`を引数として受け取り、取得したアイテムに`"domain": domain_id`フィールドを付与します。これにより、score.pyとaggregate.pyはドメインをフィルタリングしたり、ドメイン別に集計したりできるようになります。

### arXivフェッチャーの基本構造

```python
# sources/arxiv.py（新規追加）
import time
import xml.etree.ElementTree as ET
import requests

ARXIV_BASE = "http://export.arxiv.org/api/query"
ARXIV_NS = "http://www.w3.org/2005/Atom"

def fetch_arxiv(keywords, categories, per_keyword_limit, days_back, domain_id):
    """arXiv APIから論文を取得。3秒間隔ポリシーを厳守。"""
    results = []
    seen_ids = set()

    for kw in keywords:
        # カテゴリ指定がある場合は cat: フィルタを追加
        cat_filter = " OR ".join(f"cat:{c}" for c in categories)
        query = f'all:"{kw}"'
        if cat_filter:
            query = f'({query}) AND ({cat_filter})'

        params = {
            "search_query": query,
            "max_results": per_keyword_limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            resp = requests.get(ARXIV_BASE, params=params, timeout=20)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)

            for entry in root.findall(f"{{{ARXIV_NS}}}entry"):
                arxiv_id = entry.find(f"{{{ARXIV_NS}}}id").text.strip()
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)

                results.append({
                    "id": arxiv_id,
                    "title": entry.find(f"{{{ARXIV_NS}}}title").text.strip(),
                    "abstract": (entry.find(f"{{{ARXIV_NS}}}summary").text or "")[:500],
                    "url": arxiv_id,
                    "publication_date": entry.find(f"{{{ARXIV_NS}}}published").text[:10],
                    "cited_by_count": 0,  # arXivは被引用数を提供しない
                    "source": "arxiv",
                    "source_type": "academic_preprint",
                    "query_keyword": kw,
                    "domain": domain_id,
                })
        except Exception as e:
            print(f"  [WARNING] arXiv query '{kw}' failed: {e}")

        time.sleep(3)  # arXiv APIポリシー: 3秒間隔

    return results
```

### score.pyへの最小限の変更

`academic_preprint`というsource_typeを追加し、クレジビリティウェイトを0.85（査読ありのOpenAlex=1.0と技術メディア=0.7の中間）に設定します。スコアリングプロンプト自体は汎用的に書かれているため変更不要です。

```python
# score.py の CREDIBILITY_WEIGHTS に追記するだけ
CREDIBILITY_WEIGHTS = {
    "academic": 1.0,
    "academic_preprint": 0.85,   # 追加: arXiv（査読前）
    "tech_media": 0.7,
    "general_media": 0.4,
}
```

---

## 実装ロードマップの推薦

段階的に進めることを推薦します。まず**第1フェーズ**として、collect.pyのドメイン設定をYAMLに外部化し、既存のエネルギー領域を`domains/energy.yaml`に移行します（動作確認のための最小変更）。次に**第2フェーズ**として、AI・エージェント技術と半導体の2領域を追加します。この2領域はHackerNewsのシグナル密度が最も高く、既存パイプラインへの影響を最小限に抑えながら価値を確認できます。**第3フェーズ**でarXivフェッチャーを追加し、学術先行指標の検出精度を上げます。バイオテクノロジー・量子・宇宙はその後の**第4フェーズ**で順次追加する構成が現実的です。

---

Sources:
- [arXiv API Access - arXiv info](https://info.arxiv.org/help/api/index.html)
- [arXiv API User's Manual - arXiv info](https://info.arxiv.org/help/api/user-manual.html)
- [Access and authentication - Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)
- [Announcing changes to REST API rate limits - Crossref](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)
- [Reddit API: Features, Pricing & Set-ups](https://apidog.com/blog/reddit-api-guide/)
- [Reddit API Cost 2025](https://rankvise.com/blog/reddit-api-cost-guide/)
- [REST API Endpoints for /explore and /trending - GitHub Community](https://github.com/orgs/community/discussions/161519)
- [PatentSearch API Updates - PatentsView](https://search.patentsview.org/docs/)
- [PatentsView December 2025 Update](https://patentsview.org/data-in-action/whats-new-patentsview-december-2025)