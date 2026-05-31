# MEO・サイテーション対策 半自動ツール

`business.yaml`（店舗マスタ＝NAPの単一の真実のソース）を起点に、MEO（Googleマップ対策）と
サイテーション（NAP掲載）の運用素材をワンコマンドで生成します。
**実際の公開（投稿・登録）は手動**で行う「半自動」構成です（API審査不要・すぐ使える）。

## なぜ半自動か
- Googleビジネスプロフィールへの自動投稿はAPI審査が必要で、ハードルが高い。
- エキテン・ホットペッパー等の各ポータルは公開APIが無く、自動登録は規約違反になりがち。
- → **「文案・掲載文を自動生成し、NAPを一元管理＋掲載状況を追跡」** が実務で最も効きます。

## セットアップ
```bash
pip install pyyaml          # 必要なのはこれだけ
```

## 使い方
```bash
python3 meo/generate.py all                 # 全部まとめて生成（おすすめ）
python3 meo/generate.py posts --month 2026-06 --count 5
python3 meo/generate.py replies --stars 5
python3 meo/generate.py citations
python3 meo/generate.py tracker             # 掲載状況の表を更新
python3 meo/generate.py schema              # 構造化データ(JSON-LD)
python3 meo/generate.py check <掲載文.txt>  # 既存掲載のNAP一致チェック
```

## まず最初にやること
1. **`business.yaml` の `★` の付いた項目を実際の店舗情報に書き換える**（ここが全ての元データ）。
2. `python3 meo/generate.py all` を実行。
3. `meo/out/` に生成物が出ます。下記の順で活用してください。

## 生成物（`meo/out/`）
| ファイル | 用途 |
|---|---|
| `nap.md` | 全媒体に**同じ表記でコピペ**する統一NAP（最重要） |
| `google_posts_YYYY-MM.md` | Googleビジネスプロフィールの月間投稿案（コピペ可・CTA/写真メモ付き） |
| `review_replies.md` | 口コミ返信テンプレート（星・内容別） |
| `citations/<媒体>.md` | 各ポータルの登録フォームにコピペする項目別テキスト |
| `citations_index.md` | 媒体一覧（優先度・費用つき） |
| `citation_tracker.md` | 掲載状況トラッカー（進捗％・次にやること） |
| `localbusiness.jsonld` / `_snippet.html` | 公式サイトに貼る構造化データ（ローカルSEO強化） |

## 運用フロー（おすすめ）
- **MEO**: 週1回 `posts` の文案をGoogleビジネスプロフィールに投稿。口コミが来たら `review_replies.md` を元に24〜48時間以内に返信。
- **サイテーション**: `citations_index.md` の優先度順に、各 `citations/<媒体>.md` をコピペして登録。登録したら `data/citation_status.csv` の `status` を `登録済`・`listing_url` を記入 → `tracker` を再実行。
- **NAPチェック**: 既存の掲載文をテキスト保存して `check` にかけ、表記ゆれ（`×`）を統一。

## カスタマイズ
- 投稿のネタ追加: `templates/posts.yaml`
- 返信パターン追加: `templates/replies.yaml`
- 登録先の追加/削除: `templates/citations.yaml`

## ファイル構成
```
meo/
  business.yaml          # ★店舗マスタ(ここだけ編集すればOK)
  generate.py            # 生成スクリプト(CLI)
  templates/             # 投稿/返信/登録先のテンプレート
  data/citation_status.csv  # 掲載状況の保存先(編集可)
  out/                   # 生成物
```

## 今後の拡張（必要になったら）
- GitHub Actions で毎週 `posts` を自動生成しコミット／通知。
- Claude API 連携で、より多彩な投稿文・口コミ個別返信を自動生成。
- Google Business Profile API 連携での自動投稿（要GCP・OAuth・アクセス審査）。
