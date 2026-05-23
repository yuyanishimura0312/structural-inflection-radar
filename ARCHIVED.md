# structural-inflection-radar — ARCHIVED

**Archived: 2026-05-23** (DUA Wave B Step 0b)

## 廃止理由
- SQLite 中核 4 テーブル全空 (themes/raw_items/scored_items/theme_scores)
- pipeline_runs=0、2026-04-25 以降稼働停止 = dormant
- signal-db (7,668 シグナル日次更新中) と対象ドメイン完全重複
- Phase 2B 診断 15/100

## 救出資産の統合先
- 5 学術理論軸 (Scheffer/Geels/Perez/North/Dixit-Pindyck): `signal-db.sir_meta_scoring_axes`
- 323 domain_keywords + KEYWORD_RESEARCH.md: 別途人手で signal-db 拡張時に参照

## 復元
```bash
git checkout archived-2026-05-23
```
