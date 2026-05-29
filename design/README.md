# ご案内資料（女性整体院・ナチュラルデザイン）

元の Canva 製 PDF（全4ページ・A4横）を **女性整体院向け** に再デザインしたものです。
配色は **ベージュ × ブラウン（ナチュラル／落ち着き）** で統一しています。

## ページ構成
1. **本日の流れ** … ①〜⑥の手順リスト ＋ 写真2枚（差し替え枠）
2. **身体が歪む理由** … 3ステップのカード解説 ＋ まとめバナー
3. **最善の通い方** … 改善期間／施術回数 ＋ 「全12回 姿勢改善プログラム」帯
4. **姿勢改善プログラム** … 改善カーブのグラフ

## ビルド方法
```bash
python3 design/build.py              # PDF + プレビューPNG を出力
python3 design/build.py --no-preview # PDF のみ
```
- 出力 PDF : `design/out/and_me_guide.pdf`
- プレビュー : `design/out/preview-1〜4.png`

必要環境（Ubuntu の例）:
```bash
sudo apt-get install -y fonts-noto-cjk poppler-utils
pip install weasyprint Pillow
```

## 写真の差し替え（1ページ目）
`design/assets/` に画像を置くだけで自動的に埋め込まれます（再ビルド要）。

| ファイル名 | 配置場所 | 推奨 |
|---|---|---|
| `photo1.jpg`（.png/.webp 可） | P1 上：施術風景（女性施術者） | 横長。中央が主役だと綺麗（`cover`＝枠いっぱい表示） |
| `photo2.jpg`（.png/.webp 可） | P1 下：BEFORE / AFTER 姿勢 | 全体表示（`contain`）。文字が切れません |

- 画像が無いスロットは「差し替え枠」プレースホルダーが表示されます。
- 表示方法（cover / contain）やキャプション文言は `design/build.py` の `SLOTS` で調整できます。

## ファイル
- `guide.html` … 4ページのマークアップ（`{{PHOTO1}}` `{{PHOTO2}}` が写真スロット）
- `style.css`  … 配色・レイアウト（`:root` のカラー変数で色を一括変更可）
- `build.py`   … HTML→PDF 生成＋写真差し込み＋プレビュー出力
- `assets/`    … 差し替え写真の置き場
- `out/`       … 生成された PDF / プレビュー

## 配色（`style.css` の `:root`）
| 変数 | 用途 | 色 |
|---|---|---|
| `--cream` | ページ背景 | `#FAF5EE` |
| `--brown` / `--brown-d` | 見出し・帯 | `#7C6049` / `#5C4634` |
| `--gold` | アクセント | `#B5946A` |
| `--beige` | ベージュ塗り | `#E7D8C4` |
| `--terra` | 強調（旧・赤の置換） | `#BC6A4E` |
