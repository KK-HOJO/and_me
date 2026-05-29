#!/usr/bin/env python3
"""ご案内資料(女性整体院・ナチュラル配色) を HTML から PDF へ書き出す。

使い方:
    python3 design/build.py              # PDF + プレビューPNG を生成
    python3 design/build.py --no-preview # PDF のみ

写真の差し替え:
    design/assets/ に photo1 / photo2 を置くだけ（.jpg/.jpeg/.png/.webp 可）。
      photo1 … 1ページ目 上の写真（施術風景／女性施術者）
      photo2 … 1ページ目 下の写真（BEFORE / AFTER 姿勢の変化）
    ファイルが無いスロットは「差し替え枠」プレースホルダーが表示される。
"""
import subprocess, sys
from pathlib import Path
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
OUT  = ROOT / "out"
ASSETS = ROOT / "assets"
OUT.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)
PDF  = OUT / "and_me_guide.pdf"

EXTS = (".jpg", ".jpeg", ".png", ".webp")

# 各写真スロットの設定（label/note はプレースホルダー文言、caption は写真上の帯）
SLOTS = {
    "PHOTO1": dict(stem="photo1", label="写真① 施術風景",
                   note="女性施術者の写真をここに配置", caption="施術風景", fit="cover"),
    "PHOTO2": dict(stem="photo2", label="写真② BEFORE / AFTER",
                   note="姿勢変化の写真をここに配置", caption="", fit="contain"),
}

def find_image(stem):
    for ext in EXTS:
        p = ASSETS / f"{stem}{ext}"
        if p.exists():
            return p
    return None

def placeholder(cfg):
    return (
        '<div class="photo ph">'
        '<svg class="cam" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 7h3l2-2h8l2 2h3v12H3z"/><circle cx="12" cy="13" r="3.6"/></svg>'
        f'<div class="pt">{cfg["label"]}</div>'
        f'<div class="ps">{cfg["note"]}</div>'
        '</div>'
    )

def image(path, cfg):
    cap = f'<div class="cap">{cfg["caption"]}</div>' if cfg["caption"] else ""
    cls = "photo contain" if cfg.get("fit") == "contain" else "photo"
    return f'<div class="{cls}"><img src="assets/{path.name}" alt="">{cap}</div>'

def render_html():
    html = (ROOT / "guide.html").read_text(encoding="utf-8")
    for token, cfg in SLOTS.items():
        img = find_image(cfg["stem"])
        markup = image(img, cfg) if img else placeholder(cfg)
        html = html.replace("{{" + token + "}}", markup)
        print(f"  - {cfg['stem']}: {'写真 ' + img.name if img else 'プレースホルダー'}")
    return html

def build():
    print("[render] 写真スロット:")
    html = render_html()
    HTML(string=html, base_url=str(ROOT) + "/").write_pdf(str(PDF))
    print(f"[ok] PDF -> {PDF}  ({PDF.stat().st_size/1024:.0f} KB)")

def preview(dpi=120):
    for old in OUT.glob("preview*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(PDF), str(OUT / "preview")], check=True)
    print("[ok] previews:", sorted(p.name for p in OUT.glob("preview*.png")))

if __name__ == "__main__":
    build()
    if "--no-preview" not in sys.argv:
        preview()
