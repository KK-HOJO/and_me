#!/usr/bin/env python3
"""MEO・サイテーション対策 半自動ジェネレータ

business.yaml(店舗マスタ)を起点に、以下をワンコマンドで生成します。
  - Googleビジネスプロフィール投稿文案(月間)
  - 口コミ返信テンプレート
  - 各ポータル(サイテーション)掲載用テキスト
  - サイテーション掲載状況トラッカー
  - LocalBusiness 構造化データ(JSON-LD)
  - 全媒体で統一する NAP ブロック

使い方:
    python3 meo/generate.py all                 # 全部まとめて生成(おすすめ)
    python3 meo/generate.py nap                 # 統一NAPブロック
    python3 meo/generate.py posts [--month 2026-06] [--count 5]
    python3 meo/generate.py replies [--stars 5]
    python3 meo/generate.py citations           # 各ポータル掲載文
    python3 meo/generate.py tracker             # 掲載状況一覧(初回はCSVを自動作成)
    python3 meo/generate.py schema              # JSON-LD構造化データ
    python3 meo/generate.py check <file>        # 既存掲載文のNAP一致チェック

出力先: meo/out/
"""
from __future__ import annotations
import argparse, calendar, csv, datetime, json, random, re, sys, unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML が必要です。`pip install pyyaml` を実行してください。")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DATA = ROOT / "data"
TPL = ROOT / "templates"
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
(OUT / "citations").mkdir(exist_ok=True)

WD = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WD_JA = {"mon": "月", "tue": "火", "wed": "水", "thu": "木",
         "fri": "金", "sat": "土", "sun": "日"}
WD_EN = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
         "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}


def load(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def biz():
    return load(ROOT / "business.yaml")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    print(f"[ok] {path.relative_to(ROOT)}  ({len(text)} 文字)")


# ----------------------------------------------------------- formatting
def full_address(b, postal=True, building=True) -> str:
    a = b["address"]
    s = ""
    if postal and a.get("postal_code"):
        s += f"〒{a['postal_code']} "
    s += f"{a.get('prefecture','')}{a.get('city','')}{a.get('street','')}"
    if building and a.get("building"):
        s += f" {a['building']}"
    return s.strip()


def price_yen(v) -> str:
    if isinstance(v, (int, float)):
        return f"{int(v):,}円"
    return str(v)


def hours_lines(b):
    out = []
    for d in WD:
        v = str(b.get("hours", {}).get(d, "") or "").strip()
        out.append((WD_JA[d], v if v else "—"))
    return out


def keywords_expanded(b):
    """施術キーワード × 地域 で検索キーワードを自動展開。"""
    kws = list(b.get("target_keywords", []) or [])
    areas = list(b.get("area_served", []) or [])
    combo = [f"{ar} {kw}" for ar in areas[:2] for kw in kws[:4]]
    seen, res = set(), []
    for k in kws + combo:
        if k not in seen:
            seen.add(k)
            res.append(k)
    return res


def context(b) -> dict:
    a = b["address"]
    stations = (b.get("access", {}) or {}).get("stations", []) or []
    if stations:
        st = stations[0]
        nearest = f"{st.get('name','')}駅 徒歩{st.get('minutes','')}分"
    else:
        nearest = ""
    areas = b.get("area_served", []) or []
    return {
        "name": b.get("name", ""),
        "name_kana": b.get("name_kana", ""),
        "phone": b.get("phone", ""),
        "website": b.get("website", ""),
        "booking_url": b.get("booking_url", "") or b.get("website", ""),
        "area": areas[0] if areas else a.get("city", ""),
        "city": a.get("city", ""),
        "prefecture": a.get("prefecture", ""),
        "nearest_station": nearest,
        "address": full_address(b),
        "price_range": b.get("price_range", ""),
    }


class _Safe(dict):
    def __missing__(self, k):
        return ""


def fill(text: str, ctx: dict) -> str:
    return text.format_map(_Safe(ctx)).strip()


# ----------------------------------------------------------- nap
def render_nap(b) -> str:
    one = f"{b.get('name','')}｜{full_address(b)}｜TEL {b.get('phone','')}"
    block = (
        f"{b.get('name','')}（{b.get('name_kana','')}）\n"
        f"{full_address(b)}\n"
        f"TEL: {b.get('phone','')}\n"
        + (f"WEB: {b.get('website','')}\n" if b.get("website") else "")
    )
    md = [
        "# 統一NAP（全媒体でこの表記に揃える）",
        "",
        "> NAP（名称・住所・電話）は **全ての媒体で1文字も変えず** に使ってください。",
        "> 表記ゆれ（ビル名の有無・ハイフン種別・全角半角など）はMEO評価を下げます。",
        "",
        "## 1行表記",
        "```", one, "```",
        "",
        "## ブロック表記（掲載欄・署名用）",
        "```", block.rstrip(), "```",
        "",
    ]
    return "\n".join(md) + "\n"


# ----------------------------------------------------------- posts
def render_posts(b, month: str | None, count: int | None) -> str:
    cfg = load(TPL / "posts.yaml")
    templates = cfg["templates"]
    d = cfg.get("defaults", {})
    count = count or d.get("per_month", 5)
    cadence = d.get("cadence_days", 7)

    today = datetime.date.today()
    if month:
        y, m = (int(x) for x in month.split("-"))
    else:
        y, m = today.year, today.month
    days_in_month = calendar.monthrange(y, m)[1]

    ctx = context(b)
    kws = keywords_expanded(b)
    services = b.get("services", []) or []

    rnd = random.Random(y * 100 + m)  # 月ごとに安定・月が違えば変化
    order = templates[:]
    rnd.shuffle(order)
    chosen = [order[i % len(order)] for i in range(count)]

    lines = [
        f"# Googleビジネスプロフィール 投稿案 {y}年{m}月",
        "",
        "そのままコピペして投稿できます。写真メモとCTA（ボタン）も参考に。",
        "Googleは週1回以上の投稿を推奨しています。",
        "",
    ]
    ki = si = 0
    for i, t in enumerate(chosen):
        day = 1 + i * cadence
        if day > days_in_month:
            day = days_in_month
        date = datetime.date(y, m, day)
        c = dict(ctx)
        use = t.get("use", "none")
        if use == "keyword" and kws:
            c["keyword"] = kws[ki % len(kws)]
            ki += 1
        if use == "service" and services:
            s = services[si % len(services)]
            si += 1
            c["service"] = s.get("name", "")
            c["service_price"] = price_yen(s.get("price", ""))
            c["service_duration"] = s.get("duration", "")
            c["service_desc"] = s.get("desc", "")
        title = fill(t.get("title", ""), c)
        body = fill(t.get("body", ""), c)
        lines += [
            f"## {i+1}. {date:%Y/%m/%d}（{WD_JA[WD[date.weekday()]]}）｜{t.get('category','')}",
            f"- **CTAボタン**: {t.get('cta','詳細')}　**写真**: {t.get('photo_hint','')}",
            f"- **タイトル**: {title}",
            "",
            "```", body, "```",
            f"（本文 {len(body)} 文字）",
            "",
        ]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------- replies
def render_replies(b, stars: str | None) -> str:
    cfg = load(TPL / "replies.yaml")
    ctx = context(b)
    ctx["customer"] = "○○様"
    lines = ["# 口コミ返信テンプレート", "", cfg.get("guide", "").strip(), ""]
    for t in cfg["templates"]:
        if stars and stars not in str(t.get("stars", "")):
            continue
        lines += [
            f"## {t.get('topic','')}（{t.get('stars','')}）",
            "```", fill(t.get("body", ""), ctx), "```",
            "",
        ]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------- citations
def field_value(b, key, desc_len):
    a = b["address"]
    if key == "name":
        return b.get("name", "")
    if key == "name_kana":
        return b.get("name_kana", "")
    if key == "name_romaji":
        return b.get("name_romaji", "")
    if key == "address":
        return full_address(b)
    if key == "phone":
        return b.get("phone", "")
    if key == "website":
        return b.get("website", "")
    if key == "primary_category":
        return b.get("primary_category", "")
    if key == "additional_categories":
        return "、".join(b.get("additional_categories", []) or [])
    if key == "hours":
        return " / ".join(f"{j} {v}" for j, v in hours_lines(b))
    if key == "description":
        return b.get(f"description_{desc_len}", b.get("description_mid", "")).strip()
    if key == "keywords":
        return "、".join(keywords_expanded(b))
    if key == "photos":
        return "（院内・施術風景・スタッフ・外観など5枚以上を推奨）"
    return ""


def render_citations(b):
    cfg = load(TPL / "citations.yaml")
    portals = sorted(cfg["portals"], key=lambda p: p.get("priority", 9))
    prio = {1: "最優先", 2: "優先", 3: "余力があれば"}

    index = ["# サイテーション掲載用テキスト（媒体別）", "",
             "各媒体の登録フォームに、下記の値をそのままコピペしてください。",
             "**NAPは全媒体で完全一致**させること（meo/out/nap.md 参照）。", ""]
    for p in portals:
        index.append(f"- [{p['name']}]（{prio.get(p.get('priority',9),'')}・{p.get('cost','')}）"
                     f": `meo/out/citations/{p['id']}.md`")
        sec = [
            f"# {p['name']}",
            "",
            f"- 登録URL: {p.get('url','')}",
            f"- 優先度: {prio.get(p.get('priority',9),'')}　費用: {p.get('cost','')}　区分: {p.get('type','')}",
            f"- メモ: {p.get('notes','')}",
            "",
            "## 入力項目（コピペ用）",
            "",
        ]
        for key in p.get("fields", []):
            val = field_value(b, key, p.get("desc_len", "mid"))
            sec += [f"**{key}**", "```", str(val), "```", ""]
        write(OUT / "citations" / f"{p['id']}.md", "\n".join(sec) + "\n")
    write(OUT / "citations_index.md", "\n".join(index) + "\n")


# ----------------------------------------------------------- tracker
CSV_COLS = ["id", "portal", "priority", "cost", "status",
            "listing_url", "nap_match", "last_checked", "notes"]
CSV_PATH = DATA / "citation_status.csv"


def ensure_tracker_csv():
    cfg = load(TPL / "citations.yaml")
    existing = {}
    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["id"]] = row
    rows = []
    for p in sorted(cfg["portals"], key=lambda x: x.get("priority", 9)):
        r = existing.get(p["id"], {})
        rows.append({
            "id": p["id"],
            "portal": p["name"],
            "priority": p.get("priority", 9),
            "cost": p.get("cost", ""),
            "status": r.get("status", "未登録"),
            "listing_url": r.get("listing_url", ""),
            "nap_match": r.get("nap_match", "-"),
            "last_checked": r.get("last_checked", ""),
            "notes": r.get("notes", ""),
        })
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(rows)
    return rows


def render_tracker(b):
    rows = ensure_tracker_csv()
    done = sum(1 for r in rows if str(r["status"]).startswith("登録"))
    total = len(rows)
    pct = int(done / total * 100) if total else 0
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    prio = {1: "最優先", 2: "優先", 3: "余力", 9: "-"}
    lines = [
        "# サイテーション掲載状況トラッカー",
        "",
        f"進捗: {bar} {done}/{total}（{pct}%）",
        "",
        "状況を更新するには `meo/data/citation_status.csv` を編集して再実行してください。",
        "（status: 未登録 / 申請中 / 登録済 ／ nap_match: ○ × -）",
        "",
        "| 媒体 | 優先 | 費用 | 状況 | NAP一致 | 掲載URL | メモ |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['portal']} | {prio.get(int(r['priority']) if str(r['priority']).isdigit() else 9,'-')} "
            f"| {r['cost']} | {r['status']} | {r['nap_match']} | {r['listing_url']} | {r['notes']} |"
        )
    todo = [r for r in rows if not str(r["status"]).startswith("登録")]
    if todo:
        lines += ["", "## 次にやること（未登録の優先度順）", ""]
        for r in todo[:5]:
            lines.append(f"- [ ] {r['portal']} を登録 → `meo/out/citations/{r['id']}.md` の内容で入力")
    write(OUT / "citation_tracker.md", "\n".join(lines) + "\n")


# ----------------------------------------------------------- schema (JSON-LD)
def render_schema(b):
    a = b["address"]
    data = {
        "@context": "https://schema.org",
        "@type": b.get("schema_type", "LocalBusiness"),
        "name": b.get("name", ""),
        "telephone": b.get("phone", ""),
        "address": {
            "@type": "PostalAddress",
            "postalCode": a.get("postal_code", ""),
            "addressRegion": a.get("prefecture", ""),
            "addressLocality": a.get("city", ""),
            "streetAddress": (a.get("street", "") + " " + a.get("building", "")).strip(),
            "addressCountry": "JP",
        },
        "description": b.get("description_mid", ""),
        "priceRange": b.get("price_range", ""),
    }
    if b.get("website"):
        data["url"] = b["website"]
    geo = b.get("geo", {}) or {}
    if geo.get("lat") and geo.get("lng"):
        data["geo"] = {"@type": "GeoCoordinates",
                       "latitude": geo["lat"], "longitude": geo["lng"]}
    spec = []
    for d in WD:
        v = str(b.get("hours", {}).get(d, "") or "")
        if "-" in v and "定休" not in v:
            o, c = v.split("-", 1)
            spec.append({"@type": "OpeningHoursSpecification",
                         "dayOfWeek": f"https://schema.org/{WD_EN[d]}",
                         "opens": o.strip(), "closes": c.strip()})
    if spec:
        data["openingHoursSpecification"] = spec
    same = [u for u in (b.get("social", {}) or {}).values() if u]
    if b.get("booking_url"):
        same.append(b["booking_url"])
    if same:
        data["sameAs"] = same
    if b.get("area_served"):
        data["areaServed"] = b["area_served"]
    offers = []
    for s in b.get("services", []) or []:
        offer = {"@type": "Offer",
                 "itemOffered": {"@type": "Service", "name": s.get("name", "")}}
        if isinstance(s.get("price"), (int, float)):
            offer["price"] = s["price"]
            offer["priceCurrency"] = "JPY"
        offers.append(offer)
    if offers:
        data["makesOffer"] = offers

    j = json.dumps(data, ensure_ascii=False, indent=2)
    write(OUT / "localbusiness.jsonld", j + "\n")
    snippet = ('<!-- 公式サイトの <head> 内に貼り付けてください -->\n'
               '<script type="application/ld+json">\n' + j + "\n</script>\n")
    write(OUT / "localbusiness_snippet.html", snippet)


# ----------------------------------------------------------- check
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[ \t　]", "", s)
    s = re.sub(r"[‐-‑–—―ー−]", "-", s)
    return s


def cmd_check(b, path):
    text = norm(Path(path).read_text(encoding="utf-8"))
    a = b["address"]
    checks = {
        "名称": norm(b.get("name", "")),
        "名称(カナ)": norm(b.get("name_kana", "")),
        "郵便番号": norm(a.get("postal_code", "")),
        "町名番地": norm(a.get("street", "")),
        "電話": re.sub(r"\D", "", b.get("phone", "")),
    }
    print(f"[check] {path} のNAP一致チェック")
    ng = 0
    for label, val in checks.items():
        if not val:
            continue
        hay = re.sub(r"\D", "", text) if label == "電話" else text
        ok = val in hay
        ng += 0 if ok else 1
        print(f"  {'○' if ok else '×'} {label}: {val if ok else val + ' が見つかりません'}")
    print("[ok] 全て一致しています。" if ng == 0 else f"[warn] {ng}件の不一致。表記を統一してください。")


# ----------------------------------------------------------- main
def posts_path(month):
    m = month or datetime.date.today().strftime("%Y-%m")
    return OUT / f"google_posts_{m}.md"


def cmd_all(b, args):
    write(OUT / "nap.md", render_nap(b))
    write(posts_path(args.month), render_posts(b, args.month, args.count))
    write(OUT / "review_replies.md", render_replies(b, None))
    render_citations(b)
    render_tracker(b)
    render_schema(b)
    print("\n[done] meo/out/ に全ての生成物を出力しました。")


def main():
    ap = argparse.ArgumentParser(description="MEO・サイテーション対策ジェネレータ")
    ap.add_argument("cmd", nargs="?", default="all",
                    choices=["all", "nap", "posts", "replies",
                             "citations", "tracker", "schema", "check"])
    ap.add_argument("file", nargs="?", help="check 用の対象ファイル")
    ap.add_argument("--month", help="posts の対象月 例: 2026-06")
    ap.add_argument("--count", type=int, help="posts の生成数")
    ap.add_argument("--stars", help="replies の絞り込み 例: 5")
    args = ap.parse_args()

    b = biz()
    cmd = args.cmd

    if cmd == "all":
        cmd_all(b, args)
    elif cmd == "nap":
        write(OUT / "nap.md", render_nap(b))
    elif cmd == "posts":
        write(posts_path(args.month), render_posts(b, args.month, args.count))
    elif cmd == "replies":
        write(OUT / "review_replies.md", render_replies(b, args.stars))
    elif cmd == "citations":
        render_citations(b)
    elif cmd == "tracker":
        render_tracker(b)
    elif cmd == "schema":
        render_schema(b)
    elif cmd == "check":
        if not args.file:
            sys.exit("使い方: python3 meo/generate.py check <file>")
        cmd_check(b, args.file)


if __name__ == "__main__":
    main()
