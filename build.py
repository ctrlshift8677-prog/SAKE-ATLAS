#!/usr/bin/env python3
"""SAKE ATLAS 靜態網站產生器

用法：
    python3 build.py

讀取 data/ 裡的資料，輸出完整網站到 dist/。
把 dist/ 整個資料夾上傳到任何靜態網站主機即可。
不需要 npm、資料庫或 API 金鑰。若電腦有 Pillow（pip install pillow），
會額外產生較小的卡片用照片；沒有也能正常建置。
"""
import html
import json
import math
import re
import random
import shutil
import os
from collections import Counter, defaultdict
from pathlib import Path

# ───────────────────────── 網站設定（部署前可修改） ─────────────────────────
SITE = {
    "name": "SAKE ATLAS",
    "tagline": "清酒產地圖鑑",
    # 正式網址，例如 "https://sake-atlas.tw"。填了才會產生 sitemap.xml 與完整的分享預覽圖網址。
    "url": "",
    # 合作與品飲會聯絡信箱。留空時「關於」頁不顯示聯絡區塊。
    "contact_email": "",
}

# 在 GitHub Actions 上建置時，網址與路徑前綴會自動帶入
import os as _os
if _os.environ.get("SITE_URL"):
    SITE["url"] = _os.environ["SITE_URL"].rstrip("/")


def site_base_path():
    """網站所在的路徑前綴，例如 GitHub Pages 的 /SAKE-ATLAS/。"""
    bp = _os.environ.get("SITE_BASE_PATH")
    if bp is None and SITE["url"]:
        bp = re.sub(r"^https?://[^/]+", "", SITE["url"])
    bp = "/" + (bp or "").strip("/")
    return bp if bp.endswith("/") else bp + "/"


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)

# ───────────────────────── 地理與區域 ─────────────────────────
PREF_ALIAS = {
    "広島": "廣島", "静岡": "靜岡", "徳島": "德島", "沖縄": "沖繩", "鹿児島": "鹿兒島",
    "枥木": "栃木", "栃木縣": "栃木", "琦玉": "埼玉", "埼玉縣": "埼玉", "會津": "福島", "新潟縣": "新潟",
}
DENDO = 4.5  # 殿堂門檻:喜歡程度達此分數,酒卡與酒款頁蓋「殿堂」朱印

AREAS = [
    {"key": "北海道", "color": "#7d97a6", "members": ["北海道"], "label": [387, 142]},
    {"key": "東北", "color": "#b8646b", "members": ["青森", "岩手", "秋田", "宮城", "山形", "福島"], "label": [556, 318]},
    {"key": "關東", "color": "#c68457", "members": ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川"], "label": [548, 480]},
    {"key": "中部", "color": "#7fa38b", "members": ["新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "靜岡", "愛知"], "label": [336, 345]},
    {"key": "近畿", "color": "#9a82b0", "members": ["三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"], "label": [363, 510]},
    {"key": "中國", "color": "#5e8daa", "members": ["鳥取", "島根", "岡山", "廣島", "山口"], "label": [185, 399]},
    {"key": "四國", "color": "#9caa5c", "members": ["德島", "香川", "愛媛", "高知"], "label": [270, 560]},
    {"key": "九州", "color": "#cfa23c", "members": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿兒島", "沖繩"], "label": [108, 548]},
]
AREA_OF = {p: a for a in AREAS for p in a["members"]}

ICONS = {
    "search": '<circle cx="112" cy="112" r="80" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><line x1="168.57" y1="168.57" x2="224" y2="224" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
    "out": '<line x1="64" y1="192" x2="192" y2="64" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><polyline points="88 64 192 64 192 168" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
    "prev": '<polyline points="160 208 80 128 160 48" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
    "next": '<polyline points="96 48 176 128 96 208" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
    "close": '<line x1="200" y1="56" x2="56" y2="200" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><line x1="200" y1="200" x2="56" y2="56" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
    "grid": '<rect x="48" y="48" width="64" height="64" rx="8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><rect x="144" y="48" width="64" height="64" rx="8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><rect x="48" y="144" width="64" height="64" rx="8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><rect x="144" y="144" width="64" height="64" rx="8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
    "list": '<line x1="88" y1="64" x2="216" y2="64" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><line x1="88" y1="128" x2="216" y2="128" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><line x1="88" y1="192" x2="216" y2="192" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><circle cx="44" cy="64" r="12"/><circle cx="44" cy="128" r="12"/><circle cx="44" cy="192" r="12"/>',
    "arrow": '<line x1="40" y1="128" x2="216" y2="128" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><polyline points="144 56 216 128 144 200" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/>',
}


def icon(name, cls="ic"):
    return f'<svg class="{cls}" viewBox="0 0 256 256" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


# ───────────────────────── 文字工具 ─────────────────────────
KANJI_DIGIT = "〇一二三四五六七八九"


def kanji_month(m):
    names = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
    return names[m]


def kanji_date(ym):
    if not ym:
        return ""
    y, m = ym
    return "".join(KANJI_DIGIT[int(c)] for c in str(y)) + "年" + kanji_month(m) + "月"


def parse_date(s):
    """回傳 (年, 月)。接受 2026.07月、2026-07、2026-07-15、2026年7月、Excel 日期。"""
    d = parse_day(s)
    return d[:2] if d else None


def parse_day(s):
    """回傳 (年, 月, 日或 None)，保留原本的日期精度。"""
    if hasattr(s, "year") and hasattr(s, "month"):
        return (s.year, s.month, getattr(s, "day", None))
    m = re.match(r"\s*(\d{4})\s*[./\-年]\s*(\d{1,2})(?:\s*[./\-月]\s*(\d{1,2}))?", str(s or ""))
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    d = int(m.group(3)) if m.group(3) else None
    return (y, mo, d) if 1 <= mo <= 12 else None


def fmt_date(ym):
    return f"{ym[0]} 年 {ym[1]} 月" if ym else ""


def visual_len(s):
    """CJK 字算 1，半形英數算 0.55，用來決定直書字級。"""
    n = 0.0
    for ch in s:
        n += 0.55 if ord(ch) < 0x2E80 else 1.0
    return n


def brand_size(s):
    n = visual_len(s)
    if n <= 2.2:
        return "xl"
    if n <= 3.2:
        return "l"
    if n <= 4.2:
        return "m"
    if n <= 6.2:
        return "s"
    if n <= 8.5:
        return "xs"
    return "xxs"


SEAL_STRIP = re.compile(r"(株式會社|株式会社|合名會社|合名会社|合資會社|合資会社|有限會社|有限会社)")
SEAL_SUFFIX = ["酒造店", "酒造場", "酒造", "釀造", "醸造", "商店", "本家", "酒藏", "本舖", "銘釀", "酒莊", "酒廠"]


def seal_text(brewery, brand):
    s = SEAL_STRIP.sub("", brewery or "")
    s = re.sub(r"[A-Za-z0-9.\s]+", "", s)
    if not s:
        s = re.sub(r"\s+", "", brand or "")[:4] or "酒"
    if len(s) > 6:
        for suf in SEAL_SUFFIX:
            if s.endswith(suf) and len(s) - len(suf) >= 2:
                s = s[: -len(suf)]
                break
    return s[:6]


def seal(text, cls="", tilt=0):
    n = len(text)
    rows = 1 if n <= 1 else 2 if n <= 4 else 3
    cols = math.ceil(n / rows)
    style = f"--rows:{rows};--cols:{cols}"
    if tilt:
        style += f";--tilt:{tilt}deg"
    return f'<span class="seal {cls}" style="{style}" aria-hidden="true"><span>{esc(text)}</span></span>'


def clean_rice(r):
    out = []
    for p in re.split(r"[／/、,，;；]", r or ""):
        p = re.sub(r"[（(].*?[）)]", "", p)                 # 去掉括號註記，例如（麴米）
        p = re.sub(r"\s*\d+(?:\.\d+)?\s*%", "", p)          # 去掉使用比例，例如 100%
        p = re.sub(r"^\S{1,4}[縣县府道都]產\s*", "", p.strip())  # 去掉產地前綴，例如 福井縣產
        p = p.strip()
        if p and p not in out:
            out.append(p)
    return out


def stable_hash(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


# ───────────────────────── 試算表匯入 ─────────────────────────
def _txt(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if hasattr(v, "year") and hasattr(v, "month") and not isinstance(v, (int, float)):
        return f"{v.year}-{v.month:02d}" + (f"-{v.day:02d}" if getattr(v, "day", None) else "")
    return str(v).strip()


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def _tags(v):
    return [x for x in re.split(r"[、,，/／;；\s]+", _txt(v)) if x]


def _urls(v):
    return re.findall(r"https?://[^\s,，、；;]+", _txt(v))


def find_workbook():
    books = sorted((p for p in DATA.glob("*.xlsx") if not p.name.startswith("~$")), key=lambda p: (p.stat().st_mtime, p.name))
    if len(books) > 1:
        print(f"（提醒：data/ 裡有 {len(books)} 份試算表，使用 {books[-1].name}；建議只留一份）")
    return books[-1] if books else None


def load_workbook_rows(path):
    """讀取酒記試算表（酒款主資料、品飲紀錄），轉成網站使用的格式。"""
    from openpyxl import load_workbook as _lw
    wb = _lw(path, data_only=True, read_only=True)

    def sheet(name_hint):
        for ws in wb.worksheets:
            if name_hint in ws.title:
                rows = list(ws.iter_rows(values_only=True))
                head = [_txt(h) for h in rows[0]]
                return [dict(zip(head, r)) for r in rows[1:]]
        raise SystemExit(f"試算表裡找不到「{name_hint}」工作表")

    def col(row, *names):
        """先找完全相同的欄名，再找開頭相同的（例如「喜歡程度（1～5分）」）。"""
        for n in names:
            if n in row:
                return row[n]
        for n in names:
            for k in row:
                if k and k.startswith(n) and k != n + "ID":
                    return row[k]
        return None

    masters = [r for r in sheet("酒款主資料") if _txt(col(r, "酒款ID"))]
    tastes = [r for r in sheet("品飲紀錄") if _txt(col(r, "品飲ID")) and _txt(col(r, "酒款ID"))]
    by_sake = defaultdict(list)
    for r in tastes:
        by_sake[_txt(col(r, "酒款ID"))].append({
            "id": _txt(col(r, "品飲ID")),
            "date": _txt(col(r, "品飲日期")),
            "dateRaw": col(r, "品飲日期"),
            "method": _txt(col(r, "品飲方式")),
            "acquisition": _txt(col(r, "取得方式")),
            "place": _txt(col(r, "品飲地點")),
            "shop": _txt(col(r, "購入店家")),
            "buyDate": _txt(col(r, "購入日期")),
            "notes": _txt(col(r, "品飲紀錄")),
            "like": _num(col(r, "喜歡程度")),
            "again": _num(col(r, "再喝意願")),
            "buyBottle": _txt(col(r, "整瓶購入意願")),
            "cupMl": _txt(col(r, "單杯容量")),
            "bottleMl": _txt(col(r, "瓶裝容量")),
            "price": _num(col(r, "價格")) if _txt(col(r, "價格")) else None,
            "currency": _txt(col(r, "幣別")),
            "priceUnit": _txt(col(r, "計價單位")),
            "priceNote": _txt(col(r, "價格說明")),
            "pricePublic": _txt(col(r, "價格公開")),
            "aromaTags": _tags(col(r, "香氣標籤")),
            "palateTags": _tags(col(r, "口感標籤")),
            "photos": [x for x in re.split(r"[\s,，、；;]+", _txt(col(r, "品飲照片"))) if x],
            "bottleId": _txt(col(r, "同瓶編號")),
            "by": _txt(col(r, "酒造年度")),
            "shipped": _txt(col(r, "出荷年月")),
            "opened": _txt(col(r, "開瓶日期")),
            "afterOpen": _txt(col(r, "開瓶後變化")),
        })

    legacy = {}
    if (DATA / "data.json").exists():
        legacy = {x["id"]: x for x in json.loads((DATA / "data.json").read_text("utf-8"))}
    out = []
    for r in masters:
        sid = _txt(col(r, "酒款ID"))
        old = legacy.get(sid, {})
        pol = col(r, "精米步合")
        out.append({
            "id": sid,
            "brand": _txt(col(r, "銘柄")),
            "name": _txt(col(r, "酒款")),
            "brewery": _txt(col(r, "酒造")),
            "region": _txt(col(r, "地區")),
            "sakeType": _txt(col(r, "酒種")).replace("醸", "釀"),
            "rice": _txt(col(r, "酒米")),
            "polishRaw": pol,
            "by": _txt(col(r, "酒造年度")),
            "made": _txt(col(r, "製造年月")),
            "remark": _txt(col(r, "備註")),
            # 試算表沒有的欄位，沿用上一版資料
            "sources": _urls(col(r, "來源網址", "資料來源", "來源")) or old.get("sources") or [],
            "specNote": old.get("specNote", ""),
            "image": _txt(col(r, "酒款主圖", "主圖")) or old.get("image", ""),
            "imageCaption": old.get("imageCaption", ""),
            "note": old.get("note", ""),
            "tastings": by_sake.get(sid, []),
        })
    return out


def polish_of(r):
    """精米步合：接受 0.35、35、"35%"、"65%以下"、"非公開"。回傳 (數值或 None, 顯示文字)。"""
    v = r.get("polishRaw", r.get("polishRatio"))
    if v is None or _txt(v) == "":
        return None, ""
    if isinstance(v, (int, float)):
        pct = v * 100 if v <= 1 else v
    else:
        t = _txt(v)
        m = re.search(r"(\d+(?:\.\d+)?)\s*%?", t)
        if not m:
            return None, t
        pct = float(m.group(1))
        if pct <= 1 and "%" not in t:
            pct *= 100
        if "以下" in t:
            return pct, f"{pct:g}% 以下"
    if not (0 < pct <= 100):
        return None, _txt(v)
    return pct, f"{pct:g}%"


# ───────────────────────── 資料載入 ─────────────────────────
def load():
    book = find_workbook()
    meta = json.loads((DATA / "catalog-meta.json").read_text("utf-8"))
    if book:
        try:
            rows = load_workbook_rows(book)
        except ImportError:
            raise SystemExit("要讀取 Excel 需要 openpyxl，請先執行：pip install openpyxl")
        import datetime as _dt
        meta["updated"] = os.environ.get("SA_UPDATED") or _dt.date.fromtimestamp(book.stat().st_mtime).strftime("%Y.%m.%d")
        print(f"資料來源：{book.name}（{len(rows)} 款）")
    else:
        rows = json.loads((DATA / "data.json").read_text("utf-8"))
        print(f"資料來源：data.json（{len(rows)} 款）")
    geo = json.loads((DATA / "prefectures.geojson").read_text("utf-8"))

    prefs = {}
    for f in geo["features"]:
        p = f["properties"]
        prefs[p["name"]] = {
            "name": p["name"], "slug": p["english"].lower(), "code": int(p["code"]),
            "area": AREA_OF.get(p["name"], AREAS[-1]), "feature": f, "items": [],
        }

    items = []
    for r in rows:
        pname = PREF_ALIAS.get(r.get("region", ""), r.get("region", ""))
        pref = prefs.get(pname)
        tastings = []
        for t in r.get("tastings") or []:
            t = dict(t)
            day = parse_day(t.get("dateRaw") if t.get("dateRaw") is not None else t.get("date"))
            t["ym"] = day[:2] if day else None
            t["day"] = day[2] if day else None
            if "buyBottle" not in t and t.get("wouldBuyAgain"):
                t["buyBottle"] = t["wouldBuyAgain"]
            tastings.append(t)
        tastings.sort(key=lambda t: (t["ym"] or (0, 0), t["day"] or 0), reverse=True)
        latest = next((t["ym"] for t in tastings if t["ym"]), None)
        notes = [t.get("notes") for t in tastings if t.get("notes")]
        buy = next((t.get("buyBottle") for t in tastings if t.get("buyBottle")), "")
        polish, polish_label = polish_of(r)
        likes = [t["like"] for t in tastings if t.get("like") is not None]
        photo = (r.get("image") or "").replace("./images/", "")
        if not photo:
            for ext in ("webp", "jpg", "jpeg", "png"):
                if (STATIC / "images" / f"{r['id']}.{ext}").exists():
                    photo = f"{r['id']}.{ext}"
                    break
        it = dict(r)
        it.update({
            "pref": pref, "prefName": pname, "tastings": tastings, "latest": latest,
            "notesAll": notes, "buy": buy, "polish": polish, "polishLabel": polish_label,
            "like": max(likes) if likes else None,
            "riceList": clean_rice(r.get("rice")),
            "seal": seal_text(r.get("brewery"), r.get("brand")),
            "photo": photo,
        })
        items.append(it)
        if pref:
            pref["items"].append(it)

    share_set_prices(items)
    for it in items:
        it["aroma"], it["palate"] = flavor_tags(it)
    order = sorted(items, key=lambda i: (i["pref"]["code"] if i["pref"] else 99, i.get("brewery") or "", i["id"]))
    for n, it in enumerate(order):
        it["order"] = n
    return items, order, prefs, meta, geo


def share_set_prices(items):
    """套餐、活動的總價常常只填在其中一筆：同一天、同一個地方、同一種套餐的紀錄共用這個金額。"""
    groups = defaultdict(list)
    for i in items:
        for t in i["tastings"]:
            if "套餐" in (t.get("priceUnit") or "") or "活動" in (t.get("priceNote") or ""):
                key = (t.get("place") or t.get("shop") or "", t.get("ym"), (t.get("priceNote") or "").strip())
                groups[key].append(t)
    for ts in groups.values():
        src = next((t for t in ts if t.get("price") is not None), None)
        if not src:
            continue
        for t in ts:
            if t.get("price") is None:
                t["price"], t["currency"] = src["price"], src.get("currency") or t.get("currency")
                t["priceUnit"] = t.get("priceUnit") or src.get("priceUnit")
                t["priceShared"] = True


# ───────────────────────── 地圖 ─────────────────────────
def project(pt):
    x, y = pt
    return x * 0.48 + 45, y * 0.48 - 18


def geo_path(feature):
    g = feature["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    out = []
    for poly in polys:
        for ring in poly:
            pts = [project(p) for p in ring]
            out.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
    return "".join(out)


def centroid(feature):
    """投影後最大那塊陸地的形心，用來放朱印與標籤。"""
    g = feature["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    best, best_a = None, -1
    for poly in polys:
        pts = [project(p) for p in poly[0]]
        a = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            cr = x0 * y1 - x1 * y0
            a += cr
            cx += (x0 + x1) * cr
            cy += (y0 + y1) * cr
        if abs(a) > best_a and a:
            best_a, best = abs(a), (cx / (3 * a), cy / (3 * a))
    return best or project(polys[0][0][0])


def map_svg(prefs, base, current=None, labels=True, intro=False):
    mx = max(len(p["items"]) for p in prefs.values()) or 1
    ordered = sorted(prefs.values(), key=lambda p: p["code"])
    land = "".join(f'<path d="{geo_path(p["feature"])}"/>' for p in ordered)
    rings = "".join(
        f'<mask id="ring{i}" maskUnits="userSpaceOnUse" x="-200" y="-200" width="1200" height="1200">'
        f'<g fill="none" stroke-linejoin="round"><use href="#land-shape" stroke="#fff" stroke-width="{w}"/>'
        f'<use href="#land-shape" stroke="#000" stroke-width="{w - 2.2}"/></g></mask>'
        for i, w in enumerate((14, 30, 50, 74))
    )
    parts = [
        f'<svg class="atlas-map{" is-intro" if intro else ""}" viewBox="70 18 690 710" role="group" '
        f'aria-label="日本都道府縣地圖。有顏色的縣代表有品飲紀錄，顏色越深代表喝過越多款，可點選查看。">',
        '<defs>',
        f'<g id="land-shape">{land}</g>',
        rings,
        '<filter id="land-fx" x="-5%" y="-5%" width="110%" height="110%">'
        '<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4" result="n"/>'
        '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -.3 .3" result="grain"/>'
        '<feComposite in="grain" in2="SourceGraphic" operator="in" result="g2"/>'
        '<feBlend in="SourceGraphic" in2="g2" mode="multiply" result="tex"/>'
        '<feDropShadow in="tex" dx="0" dy="1.6" stdDeviation="1.4" flood-color="#1f2b28" flood-opacity=".28"/>'
        '</filter>'
        '<filter id="lift-fx" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0" dy="7" stdDeviation="6" flood-color="#1f2b28" flood-opacity=".35"/></filter>'
        # 水墨暈開：墨滴邊緣用雜訊扭成毛邊，再微微化開（縣內）／大片化開（縣外的淡墨）
        '<filter id="map-ink-bleed" x="-40%" y="-40%" width="180%" height="180%">'
        '<feTurbulence type="fractalNoise" baseFrequency=".045" numOctaves="3" seed="7" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="22" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feGaussianBlur in="d" stdDeviation="1.1"/></filter>'
        '<filter id="map-ink-pool" x="-10%" y="-10%" width="120%" height="120%">'
        '<feTurbulence type="fractalNoise" baseFrequency=".08" numOctaves="2" seed="11" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feGaussianBlur in="d" stdDeviation="1.4"/></filter>'
        '<filter id="map-ink-wash" x="-60%" y="-60%" width="220%" height="220%">'
        '<feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="2" seed="3" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="34" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feGaussianBlur in="d" stdDeviation="7"/></filter>'
        '</defs>',
        '<g class="coast" aria-hidden="true">'
        + "".join(f'<rect class="ring r{i}" x="-200" y="-200" width="1200" height="1200" mask="url(#ring{i})"/>' for i in range(4))
        + '</g>',
        '<g class="lands">',
    ]
    dots = []
    for p in ordered:
        d = geo_path(p["feature"])
        n = len(p["items"])
        cx, cy = centroid(p["feature"])
        delay = (p["code"] - 1) * 16
        if n:
            k = math.sqrt(n / mx)
            cls = "pf is-rec" + (" is-current" if current and p["slug"] == current else "")
            if current and p["slug"] != current:
                cls += " is-dim"
            parts.append(
                f'<a class="{cls}" href="{base}pref/{p["slug"]}/" data-pref="{p["slug"]}" data-area="{esc(p["area"]["key"])}" '
                f'data-name="{esc(p["name"])}" data-n="{n}" data-cx="{cx:.1f}" data-cy="{cy:.1f}" '
                f'style="--c:{p["area"]["color"]};--k:{k:.3f};--d:{delay}ms" aria-label="{esc(p["name"])}，{n} 款"><path d="{d}"/></a>'
            )
            dots.append(f'<circle class="pf-dot" data-pref="{p["slug"]}" cx="{cx:.1f}" cy="{cy:.1f}" r="{2.4 + 4.6 * k:.1f}" style="--d:{delay + 380}ms"/>')
        else:
            parts.append(f'<path class="pf is-empty" style="--d:{delay}ms" d="{d}"><title>{esc(p["name"])}，尚無紀錄</title></path>')
    parts.append("</g>")
    parts.append('<g class="ink-trail" aria-hidden="true"></g><g class="lift" aria-hidden="true"></g>')
    if labels:
        for a in AREAS:
            x, y = a["label"]
            parts.append(f'<text class="area-label" x="{x}" y="{y}" aria-hidden="true">{esc(a["key"])}</text>')
        parts.append('<text class="area-label is-small" x="560" y="652" aria-hidden="true">沖繩</text>')
    parts.append("</svg>")
    return "".join(parts)


# ───────────────────────── 元件 ─────────────────────────
PHOTO_DIM = {}


def photo_dim(it):
    """照片實際尺寸（寬, 高）；照片不裁切，封面框跟著照片比例走。"""
    name = it.get("photo")
    if not name:
        return (3, 4)
    if name not in PHOTO_DIM:
        try:
            from PIL import Image
            with Image.open(STATIC / "images" / name) as im:
                PHOTO_DIM[name] = im.size
        except Exception:
            PHOTO_DIM[name] = (1080, 1440)
    return PHOTO_DIM[name]


def ar_style(it):
    w, h = photo_dim(it)
    return f' style="--ar:{w} / {h};--arn:{w / h:.4f}"'


def photo_tag(it, base, cls="", sizes="(max-width: 700px) 50vw, 240px", eager=False):
    if not it["photo"]:
        return ""
    stem = it["photo"].rsplit(".", 1)[0]
    alt = f'{it["brand"]} {it["name"]} 的酒瓶與酒杯'
    src_l = f"{base}assets/images/{it['photo']}"
    src_s = f"{base}assets/images/{stem}-640.webp"
    srcset = f' srcset="{src_s} 640w, {src_l} 1080w" sizes="{sizes}"' if HAS_SMALL.get(stem) else ""
    loading = "eager" if eager else "lazy"
    w, h = photo_dim(it)
    return f'<img class="{cls}" src="{src_l}"{srcset} width="{w}" height="{h}" alt="{esc(alt)}" loading="{loading}" decoding="async">'


def goshuin(it, size="card"):
    """直書的御朱印頁：縣名、大字酒名、日期、酒造朱印。"""
    h = stable_hash(it["id"])
    pos = h % 4
    tilt = ((h >> 3) % 7) - 3
    pref = it["prefName"] or ""
    date = kanji_date(it["latest"])
    name_html = f'<span class="g-name">{esc(it["name"])}</span>' if size == "cover" and it["name"] and it["name"] != it["brand"] else ""
    return (
        f'<span class="g-page g-{size}" style="--area:{it["pref"]["area"]["color"] if it["pref"] else "#999"}">'
        f'<span class="g-ink">'
        f'<span class="g-pref">{esc(pref)}</span>'
        f'<span class="g-brand b-{brand_size(it["brand"])}">{esc(it["brand"])}</span>'
        f'{name_html}'
        f'<span class="g-date">{esc(date)}</span>'
        f'</span>'
        f'{seal(it["seal"], "g-seal p" + str(pos), tilt)}'
        f'</span>'
    )


def card(it, base, extra=""):
    p = it["pref"]
    area = p["area"]["key"] if p else ""
    rice = "|".join(it["riceList"])
    q = " ".join(filter(None, [
        it["brand"], it["name"], it.get("brewery"), it["prefName"], it.get("sakeType"), it.get("rice"),
        it.get("note"), *it["notesAll"], *[t.get("place") or "" for t in it["tastings"]],
        *[t.get("shop") or "" for t in it["tastings"]],
    ])).lower()
    latest = f'{it["latest"][0]}{it["latest"][1]:02d}' if it["latest"] else "0"
    fl = (it["aroma"] + it["palate"])[:4]
    if fl:
        peek1 = "・".join(fl)
    else:
        peek1 = "・".join(x for x in [it.get("sakeType"), (f'精米 {it["polishLabel"]}' if it.get("polishLabel") else "")] if x) \
            or (f'{it["latest"][0]} 年 {it["latest"][1]} 月品飲' if it["latest"] else "")
    peek2 = "　".join(x for x in [it["prefName"], (it["riceList"][0] if it["riceList"] else "")] if x)
    strip = ""
    if it["aroma"]:
        segs = "".join(f'<i style="--c:{AROMA_COLOR.get(FL_INFO.get(w, {}).get("fam"), AROMA_COLOR["其他"])}"></i>' for w in it["aroma"][:6])
        strip = f'<span class="c-aroma" aria-hidden="true">{segs}</span>'
    fx = (f'{strip}'
          f'<span class="c-peek" aria-hidden="true"><b>{esc(peek1)}</b><small>{esc(peek2)}</small></span>')
    cover = (
        f'<span class="c-cover is-photo{" is-fit" if abs(photo_dim(it)[0] / photo_dim(it)[1] - 9 / 16) > 0.02 else ""}">{photo_tag(it, base)}{fx}</span>' if it["photo"]
        else f'<span class="c-cover">{goshuin(it)}{fx}</span>'
    )
    meta_bits = [b for b in [it.get("sakeType"), " / ".join(it["riceList"][:2])] if b]
    meta = "，".join(meta_bits) if meta_bits else "酒種與酒米未記錄"
    title = it["name"] if it["name"] and it["name"] != it["brand"] else it["brand"]
    return (
        f'<a class="card{extra}" href="{base}sake/{it["id"]}/" '
        f'data-area="{esc(area)}" data-pref="{esc(p["slug"] if p else "")}" data-type="{esc(it.get("sakeType") or "")}" '
        f'data-rice="{esc(rice)}" data-photo="{1 if it["photo"] else 0}" data-note="{1 if (it.get("note") or it["notesAll"]) else 0}" '
        f'data-latest="{latest}" data-order="{it["order"]}" data-pol="{it["polish"] or ""}" data-like="{it["like"] if it["like"] is not None else ""}" data-fl="{esc("|".join(it["aroma"] + it["palate"]))}" data-q="{esc(q)}">'
        f'{cover}'
        f'<span class="c-cap">'
        f'{dendo_of(it)}<span class="c-title"><span class="c-brand">{esc(it["brand"])}</span>'
        f'{"<span class=c-name>" + esc(title) + "</span>" if title != it["brand"] else ""}</span>'
        f'<span class="c-meta">{esc(meta)}</span>'
        f'{("<span class=c-fl>" + "　".join(esc(t) for t in (it["aroma"] + it["palate"])[:4]) + "</span>") if (it["aroma"] or it["palate"]) else ""}'
        f'<span class="c-row" aria-hidden="true">'
        f'<span>{esc(it.get("brewery") or "")}</span><span>{esc(it["prefName"])}</span>'
        f'<span>{esc(it.get("sakeType") or "")}</span><span>{esc(" / ".join(it["riceList"]))}</span>'
        f'<span>{esc(fmt_date(it["latest"]))}</span></span>'
        f'</span></a>'
    )


# ───────────────────────── 風味 ─────────────────────────
# 香氣：(家族, [(標籤, [比對用詞], 說明)])
AROMA = [
    ("果香", [
        ("蘋果", ["紅蘋果", "青蘋果", "蘋果"], "清甜的蘋果香。吟釀酒的果香多來自酵母產生的己酸乙酯，蘋果是其中最典型的一種。"),
        ("水梨", ["水梨", "洋梨", "梨"], "清脆多汁的梨子香，和蘋果香同屬吟釀香一系，給人清爽的印象。"),
        ("白桃", ["白桃", "水蜜桃", "桃子"], "柔和甜美的桃子香，常出現在香氣華麗的吟釀酒裡。"),
        ("哈密瓜", ["哈密瓜", "蜜瓜", "香瓜"], "飽滿的瓜類甜香，和香蕉香一樣多來自乙酸異戊酯。"),
        ("香蕉", ["香蕉"], "熟香蕉般的甜香，主要來自乙酸異戊酯，是另一種常見的吟釀香。"),
        ("柑橘", ["葡萄柚", "柑橘", "柚子", "檸檬"], "明亮的柑橘調，讓整體感覺更清新、帶酸。"),
        ("葡萄", ["麝香葡萄", "白葡萄", "葡萄"], "像麝香葡萄般甜美多汁的香氣，常出現在香氣華麗的酒裡。"),
    ]),
    ("花香", [("白花", ["花香", "白花"], "淡雅的白花香，常和果香一起出現在香氣華麗的酒裡。")]),
    ("米與麴", [
        ("米香", ["米香", "米味", "蒸米", "米飯", "穀物"], "像剛蒸好的米飯，是米與麴原本的香氣。純米酒、溫熱來喝時特別明顯。"),
        ("栗子", ["栗子", "麴香"], "類似蒸栗子的香氣，多半來自米麴。"),
    ]),
    ("發酵", [
        ("優格", ["優酪乳", "優格", "乳酸香", "乳酸"], "聞起來像優格、優酪乳那樣帶發酵感的酸香。生酛、山廢這類靠乳酸菌的酒母，或剛榨好的生酒常見。"),
        ("乳香", ["奶油", "乳香", "牛奶"], "像奶油或牛奶般柔和、圓潤的乳香。"),
    ]),
    ("熟成", [
        ("醬香", ["醬香", "醬油", "味噌"], "近似醬油、味噌的深沉鮮香，常見於熟成時間較長的酒。"),
        ("焦糖", ["焦糖", "蜂蜜", "堅果", "古酒", "熟成香"], "堅果、焦糖或蜂蜜般的香氣，來自較長時間的熟成。"),
    ]),
    ("清涼", [
        ("杉木", ["杉木", "木桶", "木香", "木質"], "杉木、木質的香氣，常見於用木桶釀造或貯藏的酒。"),
        ("青草", ["青草", "草本", "薄荷"], "清涼的青草、草本氣息。"),
    ]),
]
# 口感：(標籤, [比對用詞], 說明, 墨形參數)
PALATE = [
    ("圓潤", ["圓潤", "溫潤", "口感柔和", "入口柔和"], "入口柔和，沒有尖銳的稜角。", "round"),
    ("滑順", ["滑順", "綿密", "絲滑", "細膩", "細緻", "順滑"], "口感細緻，像絲綢一樣滑過。", "smooth"),
    ("鮮活", ["鮮活", "新鮮感"], "入口新鮮、有生命力，常見於剛榨好的生酒。", "acid"),
    ("礦物感", ["礦物"], "像清水流過石頭般的礦物感，讓整體更清爽。", "sharp"),
    ("多汁", ["果汁感", "多汁"], "像咬下水果一樣多汁的口感。", "full"),
    ("輕盈", ["輕盈", "清爽", "輕快", "淡麗"], "酒體輕，喝起來不沉重。", "light"),
    ("飽滿", ["飽滿", "厚實", "濃郁", "醇厚", "濃醇", "厚重", "稍厚"], "酒體厚，味道在口中有份量。", "full"),
    ("俐落", ["俐落", "乾淨", "爽快", "辛口"], "收尾乾淨，味道很快收住。", "sharp"),
    ("酸度", ["果酸", "酸度", "酸味", "酸"], "明亮的酸，讓味道更有精神。", "acid"),
    ("甘口", ["甘口", "甜感", "甜味", "甘甜", "甜潤"], "能感覺到明顯的甜味。", "sweet"),
    ("氣泡感", ["微氣泡", "微發泡", "氣泡", "發泡"], "舌尖有細小的氣泡刺激，常見於生酒或活性酒。", "fizz"),
    ("尾韻微苦", ["苦味", "微苦", "苦"], "收尾帶一點苦，讓味道更立體。", "bitter"),
    ("鮮味", ["旨味", "鮮味", "うま味"], "米帶來的鮮美滋味，越喝越有味道。", "umami"),
]
AROMA_COLOR = {"果香": "#e9a76b", "花香": "#e3a0b4", "米與麴": "#d8c48e", "發酵": "#aebfcf",
               "熟成": "#bf8a4f", "清涼": "#94bf9f", "其他": "#c4b39b"}
FL_INFO = {}
for fam, tags in AROMA:
    for tag, pats, desc in tags:
        FL_INFO[tag] = {"kind": "aroma", "fam": fam, "desc": desc, "pats": pats}
for tag, pats, desc, shape in PALATE:
    FL_INFO[tag] = {"kind": "palate", "desc": desc, "pats": pats, "shape": shape}
_PAT2TAG = sorted(((pt, tag) for tag, v in FL_INFO.items() for pt in v["pats"]), key=lambda x: -len(x[0]))
_PAT_RE = re.compile("|".join(re.escape(pt) for pt, _ in _PAT2TAG))
_PAT_MAP = dict(_PAT2TAG)
_NEG = "不無沒未"


def flavor_scan(text):
    """從心得文字找出風味詞。回傳 [(start, end, tag)]，略過前面有「不、無、沒」的詞。"""
    out = []
    for m in _PAT_RE.finditer(text or ""):
        if m.start() > 0 and text[m.start() - 1] in _NEG:
            continue
        out.append((m.start(), m.end(), _PAT_MAP[m.group(0)]))
    return out


def flavor_mark(text):
    """把心得裡的風味詞包成可互動的標記（輸入為未跳脫文字，輸出為安全 HTML）。"""
    parts, last = [], 0
    for a, b, tag in flavor_scan(text):
        parts.append(esc(text[last:a]))
        parts.append(f'<mark class="fw" data-fl="{esc(tag)}" tabindex="0">{esc(text[a:b])}</mark>')
        last = b
    parts.append(esc(text[last:]))
    return "".join(parts)


def flavor_tags(it):
    texts = [it.get("note") or ""] + it["notesAll"]
    found = []
    for t in texts:
        found += [tag for _, _, tag in flavor_scan(t)]
    explicit, custom_aroma = [], []
    for src in [it] + it["tastings"]:
        for k in ("aromaTags", "palateTags"):
            v = src.get(k)
            if isinstance(v, str):
                v = [x for x in re.split(r"[、,，/／\s]+", v) if x]
            for word in v or []:
                hit = flavor_scan(word)            # 「紅蘋果」→ 蘋果、「微氣泡」→ 氣泡感
                if hit:
                    explicit += [h[2] for h in hit]
                else:
                    explicit.append(word)
                    if k == "aromaTags":
                        custom_aroma.append(word)
    tags = list(dict.fromkeys(explicit + found))
    aroma = [t for t in tags if FL_INFO.get(t, {}).get("kind") == "aroma" or t in custom_aroma]
    palate = [t for t in tags if t not in aroma]
    return aroma, palate


def wheel_svg(active):
    """香氣輪：家族在內圈，標籤在外圈；這支酒有的香氣以朱色標出。"""
    total = sum(len(t) for _, t in AROMA)
    step = 360 / total
    parts = ['<svg class="wheel-svg" viewBox="-170 -170 340 340" aria-hidden="true">',
             '<circle class="wh-ring" r="60"/><circle class="wh-ring is-faint" r="100"/>']
    i = 0
    for fam, tags in AROMA:
        a0 = i * step - 90
        a1 = (i + len(tags)) * step - 90
        has = any(t[0] in active for t in tags)
        large = 1 if (a1 - a0) > 180 else 0
        def pt(r, a):
            return f"{r * math.cos(math.radians(a)):.1f} {r * math.sin(math.radians(a)):.1f}"
        parts.append(
            f'<path class="wh-fam{" is-on" if has else ""}" data-fam="{esc(fam)}" style="--c:{AROMA_COLOR.get(fam, "#c4b39b")}" '
            f'd="M{pt(62, a0 + 1)} A62 62 0 {large} 1 {pt(62, a1 - 1)} L{pt(98, a1 - 1)} A98 98 0 {large} 0 {pt(98, a0 + 1)} Z"/>')
        mid = (a0 + a1) / 2
        parts.append(f'<text class="wh-famlabel" x="{80 * math.cos(math.radians(mid)):.1f}" y="{80 * math.sin(math.radians(mid)):.1f}">{esc(fam)}</text>')
        parts.append(f'<line class="wh-sep" x1="{60 * math.cos(math.radians(a0)):.1f}" y1="{60 * math.sin(math.radians(a0)):.1f}" '
                     f'x2="{150 * math.cos(math.radians(a0)):.1f}" y2="{150 * math.sin(math.radians(a0)):.1f}"/>')
        for j, (tag, _, _) in enumerate(tags):
            a = (i + j + .5) * step - 90
            on = tag in active
            x, y = 112 * math.cos(math.radians(a)), 112 * math.sin(math.radians(a))
            lx, ly = 138 * math.cos(math.radians(a)), 138 * math.sin(math.radians(a))
            col = AROMA_COLOR.get(fam, "#c4b39b")
            if on:
                parts.append(f'<g class="wh-tag is-on" data-fl="{esc(tag)}" style="--c:{col}">'
                             f'<circle class="wh-halo" cx="{x:.1f}" cy="{y:.1f}" r="13"/>'
                             f'<circle class="wh-dot" cx="{x:.1f}" cy="{y:.1f}" r="6.5"/>'
                             f'<text class="wh-label" x="{lx:.1f}" y="{ly:.1f}">{esc(tag)}</text></g>')
            else:
                parts.append(f'<circle class="wh-off" cx="{x:.1f}" cy="{y:.1f}" r="2.2"><title>{esc(tag)}</title></circle>')
        i += len(tags)
    parts.append("</svg>")
    return "".join(parts)


def flavor_section(it, items, base):
    aroma, palate = it["aroma"], it["palate"]
    if not (aroma or palate):
        return ""
    same = {}
    for t in aroma + palate:
        same[t] = [{"id": x["id"], "t": x["brand"] + ("　" + x["name"] if x["name"] != x["brand"] else "")}
                   for x in items if x["id"] != it["id"] and t in (x["aroma"] + x["palate"])][:6]
    data = {
        "aroma": aroma, "palate": palate,
        "info": {**{k: {kk: vv for kk, vv in v.items() if kk != "pats"} for k, v in FL_INFO.items()},
                 **{t: {"kind": "aroma" if t in aroma else "palate", "fam": "其他", "desc": "這支酒紀錄裡的描述。"}
                    for t in aroma + palate if t not in FL_INFO}},
        "same": same, "base": base,
    }
    chip = lambda t: f'<button type="button" class="fl-chip" data-fl="{esc(t)}">{esc(t)}</button>'
    aroma_html = ""
    if aroma:
        aroma_html = f'''<div class="fl-aroma">
        <h3>香氣</h3>
        <div class="wheel">{wheel_svg(set(aroma))}
          <div class="wheel-core"><b data-core-word>{esc(aroma[0])}</b><span data-core-fam>{esc(FL_INFO.get(aroma[0], {}).get("fam", ""))}</span></div>
        </div>
        <p class="fl-chips">{"".join(chip(t) for t in aroma)}</p>
      </div>'''
    palate_html = ""
    if palate:
        palate_html = f'''<div class="fl-palate">
        <h3>口感</h3>
        <div class="ink" data-ink>
          <svg viewBox="-130 -130 260 260" aria-hidden="true">
            <defs>
              <filter id="ink-edge" x="-30%" y="-30%" width="160%" height="160%">
                <feTurbulence type="fractalNoise" baseFrequency=".035 .05" numOctaves="3" seed="7" result="n"/>
                <feDisplacementMap in="SourceGraphic" in2="n" scale="9" xChannelSelector="R" yChannelSelector="G" result="d"/>
                <feGaussianBlur in="d" stdDeviation=".7"/>
              </filter>
              <filter id="map-ink-bleed" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="9"/></filter>
              <radialGradient id="ink-fill" cx="46%" cy="44%" r="62%">
                <stop offset="0" class="ink-s0"/><stop offset=".7" class="ink-s1"/><stop offset="1" class="ink-s2"/>
              </radialGradient>
            </defs>
            <path class="ink-bleed" d=""/>
            <path class="ink-body" d=""/>
            <circle class="ink-core" r="0"/>
            <g class="ink-bubbles"></g>
          </svg>
        </div>
        <p class="fl-chips">{"".join(chip(t) for t in palate)}</p>
      </div>'''
    return f'''<section class="sk-sec flavor" aria-labelledby="fl-h" data-flavor>
      <h2 id="fl-h">風味</h2>
      <div class="fl-grid{" is-one" if not (aroma and palate) else ""}">{aroma_html}{palate_html}</div>
      <div class="fl-say" aria-live="polite"><p class="fl-say-t" data-say-t></p><p class="fl-say-d" data-say-d></p><p class="fl-say-more" data-say-more></p></div>
      <script type="application/json" class="fl-data">{json.dumps(data, ensure_ascii=False)}</script>
    </section>'''


HAS_SMALL = {}


def grain_geom(p, rx0=44.0, ry0=62.0):
    """精米步合是重量比例：米粒的直徑約與重量的立方根成正比；磨得越多，米粒越接近圓形。"""
    p = max(0.001, min(1.0, p))
    s = p ** (1 / 3)
    asp0 = ry0 / rx0
    asp = 1 + (asp0 - 1) * p ** 0.6
    return rx0 * s * (asp0 / asp) ** 0.5, ry0 * s * (asp / asp0) ** 0.5
GRAIN_DEFS = ('<defs><radialGradient id="rg" cx="50%" cy="48%" r="55%">'
              '<stop offset="0" style="stop-color:var(--rice-core)"/><stop offset=".38" style="stop-color:var(--rice-core)"/>'
              '<stop offset=".62" style="stop-color:var(--rice)"/><stop offset="1" style="stop-color:var(--rice)"/></radialGradient></defs>')

# ───────────────────────── 頁面外框 ─────────────────────────
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=LXGW+WenKai+TC:wght@400;700&family=Noto+Sans+TC:wght@400;500;700&display=swap">')


def abs_url(path):
    return SITE["url"].rstrip("/") + "/" + path.lstrip("/") if SITE["url"] else ""


NAVS = [("sake/", "酒款", "sake"), ("guide/", "入門", "guide"), ("about/", "關於", "about")]
PAGES = {}  # 供單檔預覽版使用：路徑 -> 頁面內容


def header_html(base, nav):
    nav_html = "".join(
        f'<a href="{base}{href}" data-nav="{key}"{" aria-current=page" if key == nav else ""}>{label}</a>' for href, label, key in NAVS
    )
    return f'''<a class="skip" href="#main">跳到主要內容</a>
<header class="top">
  <a class="mark" href="{base}"><span class="mark-en">SAKE ATLAS</span><span class="mark-zh">清酒產地圖鑑</span></a>
  <nav class="top-nav" aria-label="主選單">{nav_html}</nav>
  <form class="top-search" action="{base}sake/" role="search">
    <label class="sr" for="q-top">搜尋酒款</label>
    {icon("search")}
    <input id="q-top" name="q" type="search" placeholder="酒名、酒造、酒米" autocomplete="off" enterkeyhint="search">
  </form>
  <a class="top-search-btn" href="{base}sake/?focus=1" aria-label="搜尋酒款">{icon("search")}</a>
</header>'''


def footer_html(base):
    return f'''<footer class="foot">
  <p class="warn"><strong>禁止酒駕</strong><strong>飲酒過量，有害健康</strong><span>未滿十八歲請勿飲酒</span></p>
  <div class="foot-row">
    <p>每一款都是實際喝過後記下。酒款規格以對應批次的酒標為準。本站不販售任何酒類。</p>
    <p class="foot-links"><a href="{base}sake/">全部酒款</a><a href="{base}guide/">清酒入門</a><a href="{base}about/">關於這本圖鑑</a></p>
  </div>
</footer>'''


def page(*, title, desc, depth, body, path, nav="", og_image="", body_class="", base=None):
    base = base or ("../" * depth if depth else "./")
    full_title = f"{title}｜{SITE['name']}" if title else f"{SITE['name']}｜{SITE['tagline']}"
    if path != "404.html":
        PAGES["/" + path] = {"t": full_title, "c": body_class, "n": nav, "b": body}
    og_img = abs_url(og_image) if og_image else abs_url("assets/og.jpg")
    canonical = abs_url(path)
    head_extra = ""
    if canonical:
        head_extra += f'<link rel="canonical" href="{esc(canonical)}"><meta property="og:url" content="{esc(canonical)}">'
    if og_img:
        head_extra += f'<meta property="og:image" content="{esc(og_img)}"><meta name="twitter:card" content="summary_large_image">'
    return f'''<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE['name']}">
<meta property="og:title" content="{esc(full_title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:locale" content="zh_TW">{head_extra}
<meta name="color-scheme" content="light only">
<meta name="theme-color" content="#f2f1eb">
<link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml">
{FONTS}
<link rel="stylesheet" href="{base}assets/site.css">
<script>addEventListener("pagereveal",function(e){{if(!e.viewTransition||!window.navigation||!navigation.activation||!navigation.activation.from)return;var m=(navigation.activation.from.url||"").match(/\\/sake\\/(S\\d{{4}})\\//);if(!m||/\\/sake\\/S\\d{{4}}\\//.test(location.pathname))return;var go=function(){{var c=document.querySelector('a.card[href*="'+m[1]+'/"] .c-cover');if(c){{c.style.viewTransitionName="bottle";e.viewTransition.finished.finally(function(){{c.style.viewTransitionName=""}})}}}};if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",go,{{once:true}});else go()}});</script>
<script src="{base}assets/site.js" defer></script>
</head>
<body class="{body_class}">
{header_html(base, nav)}
<main id="main">
{body}
</main>
{footer_html(base)}
</body>
</html>
'''


# ───────────────────────── 關於我（data/about.md） ─────────────────────────
def load_about():
    """讀取 data/about.md：以「## 標題」分段，回傳 {標題: 內文}。"""
    f = DATA / "about.md"
    if not f.exists():
        return {}
    text = re.sub(r"<!--.*?-->", "", f.read_text("utf-8"), flags=re.S)
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def _inline(t):
    t = esc(t)
    t = re.sub(r"([\w.+-]+@[\w-]+\.[\w.-]+)", r'<a href="mailto:\1">\1</a>', t)
    t = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" rel="noopener">\1</a>', t)
    return t


def md_html(text):
    """極簡的段落與條列轉換。"""
    blocks, para, items = [], [], []
    def flush():
        if para:
            blocks.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()
        if items:
            blocks.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            flush()
        elif line.startswith("- "):
            if para:
                blocks.append(f"<p>{_inline(' '.join(para))}</p>")
                para.clear()
            items.append(line[2:])
        else:
            if items:
                blocks.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
                items.clear()
            para.append(line)
    flush()
    return "".join(blocks)


def certs_html(about):
    certs = [l[2:].strip() for l in about.get("證照", "").splitlines() if l.strip().startswith("- ")]
    return "".join(f'<span class="cert">{esc(c)}</span>' for c in certs)


def me_section(about, base):
    intro = about.get("首頁簡介", "")
    if not intro:
        return ""
    return f'''<section class="me" aria-labelledby="me-h">
  <div class="me-inner">
    <h2 id="me-h">記錄這本圖鑑的人</h2>
    <div class="me-body">{md_html(intro)}
      {f'<p class="me-certs">{certs_html(about)}</p>' if certs_html(about) else ""}
      <a class="me-link" href="{base}about/">關於我與評分標準{icon("arrow")}</a>
    </div>
  </div>
</section>'''


# ───────────────────────── 首頁 ─────────────────────────
def leaf_data(prefs, items):
    out = {}
    total_brew = Counter(i.get("brewery") for i in items if i.get("brewery"))
    latest = max((i["latest"] for i in items if i["latest"]), default=None)

    def summary(its):
        brews = Counter(i.get("brewery") for i in its if i.get("brewery"))
        seal_of = {}
        for i in its:
            if i.get("brewery"):
                seal_of.setdefault(i["brewery"], i["seal"])
        lt = max((i["latest"] for i in its if i["latest"]), default=None)
        picks = sorted(its, key=lambda i: (bool(i["photo"]), bool(i.get("note") or i["notesAll"]), i["latest"] or (0, 0)), reverse=True)[:3]
        return {
            "n": len(its), "b": len(brews),
            "seals": [seal_of[b] for b, _ in brews.most_common(6)],
            "date": kanji_date(lt),
            "picks": [{"id": i["id"], "t": i["brand"] + ("　" + i["name"] if i["name"] and i["name"] != i["brand"] else "")} for i in picks],
        }

    for p in prefs.values():
        if p["items"]:
            s = summary(p["items"])
            s.update({"name": p["name"], "area": p["area"]["key"], "slug": p["slug"], "sc": p["slug"], "cap": SCENE_CAPTION.get(p["slug"], "")})
            out[p["slug"]] = s
    allsum = summary(items)
    allsum.update({"name": "全日本", "area": "日本", "slug": "", "sc": "japan", "cap": SCENE_CAPTION["japan"]})
    out["_all"] = allsum
    return out, len(total_brew), latest


def leaf_html(s, base, is_all=True):
    seals = "".join(seal(t, f"leaf-seal s{n}", ((n * 37) % 9) - 4) for n, t in enumerate(s["seals"]))
    picks = "".join(f'<li><a href="{base}sake/{p["id"]}/">{esc(p["t"])}</a></li>' for p in s["picks"])
    cta_href = f"{base}sake/" if is_all else f'{base}pref/{s["slug"]}/'
    cta = f'瀏覽全部 {s["n"]} 款' if is_all else f'看{s["name"]}的 {s["n"]} 款'
    hint = '<p class="leaf-hint" data-hint>把滑鼠移到地圖上的縣，這一頁會換成那裡的紀錄。</p>' if is_all else ""
    date = ("最近一次　" + esc(s["date"])) if s["date"] else ""
    return f'''<div class="leaf-top">
      {scene_html(s["sc"], base)}
      <div class="leaf-ink">
        <p class="leaf-area">{esc(s["area"])}</p>
        <h2 class="leaf-title">{esc(s["name"])}</h2>
        <p class="leaf-count"><span class="tcy">{s["n"]}</span>款<span class="gap"></span><span class="tcy">{s["b"]}</span>間酒造</p>
      </div>
      <div class="leaf-seals">{seals}</div>
      {side_html(s["sc"], date)}
    </div>
    <div class="leaf-foot">
      <ul class="leaf-picks" aria-label="{esc(s["name"])}的酒款">{picks}</ul>
      <a class="btn" href="{cta_href}">{esc(cta)}{icon("arrow")}</a>
      {hint}
    </div>'''


# 各縣水墨風景的畫題（圖檔在 static/scenes/，由 tools/paint_scenes.py 產生）
SCENE_CAPTION = {
    "japan": "富士與海", "hokkaido": "大雪山", "aomori": "岩木山與弘前城", "iwate": "岩手山", "miyagi": "松島",
    "akita": "鳥海山與秋田杉", "yamagata": "月山與最上川", "fukushima": "磐梯山與豬苗代湖", "ibaraki": "筑波山",
    "tochigi": "男體山與中禪寺湖", "gunma": "赤城山", "saitama": "秩父連山", "chiba": "犬吠埼", "tokyo": "東京灣",
    "kanagawa": "箱根與相模灣", "niigata": "越後山脈", "toyama": "立山連峰與富山灣", "ishikawa": "白山與能登",
    "fukui": "越前海岸", "yamanashi": "富士與忠靈塔", "nagano": "北阿爾卑斯", "gifu": "白川鄉合掌造",
    "shizuoka": "富士與三保松原", "aichi": "名古屋城", "mie": "夫婦岩", "shiga": "琵琶湖", "kyoto": "北山杉",
    "osaka": "大阪灣", "hyogo": "姬路城", "nara": "吉野山櫻", "wakayama": "那智瀑布", "tottori": "大山與鳥取砂丘",
    "shimane": "宍道湖", "okayama": "烏城", "hiroshima": "嚴島大鳥居", "yamaguchi": "錦帶橋", "tokushima": "鳴門渦潮",
    "kagawa": "瀨戶內之島", "ehime": "石鎚山", "kochi": "四萬十川", "fukuoka": "太宰府之梅", "saga": "有明海海苔棚",
    "nagasaki": "九十九島", "kumamoto": "阿蘇", "oita": "由布岳與金鱗湖", "miyazaki": "高千穗峽", "kagoshima": "櫻島",
    "okinawa": "珊瑚之海",
}


def scene_html(slug, base):
    if not (STATIC / "scenes" / f"{slug}.webp").exists():
        return ""
    return f'<img class="leaf-scene" src="{base}assets/scenes/{slug}.webp" alt="" aria-hidden="true" decoding="async">'


def side_html(slug, date_txt):
    cap = SCENE_CAPTION.get(slug, "")
    cap_html = f'<p class="leaf-scene-cap">{esc(cap)}</p>' if cap else ""
    return f'<div class="leaf-side">{cap_html}<p class="leaf-date">{date_txt}</p></div>'


TYPE_MATRIX = [
    # (精米步合列, 純米, 加釀造酒精)
    ("50% 以下", "純米大吟釀", "大吟釀"),
    ("60% 以下", "純米吟釀", "吟釀"),
    ("60% 以下或特別製法", "特別純米酒", "特別本釀造"),
    ("不限｜70% 以下", "純米酒", "本釀造"),
]


def build_home(items, order, prefs, meta):
    base = "./"
    data, nbrew, latest = leaf_data(prefs, items)
    recent = sorted([i for i in items if i["latest"]], key=lambda i: (i["latest"], i["id"]), reverse=True)[:14]
    with_photo = sorted([i for i in items if i["photo"]], key=lambda i: (i["latest"] or (0, 0), i["id"]), reverse=True)
    photos = with_photo[:9]
    rec_prefs = sum(1 for p in prefs.values() if p["items"])

    fold = "".join(f'<li style="--i:{n}">{card(i, base)}</li>' for n, i in enumerate(recent))
    flavored = [i for i in order if i["aroma"]]
    scent_html = ""
    if len(flavored) >= 10:
        ac = Counter(a for i in flavored for a in i["aroma"]).most_common(8)
        first = ac[0][0]
        chips = "".join(
            f'<button type="button" class="fl-chip" data-scent="{esc(a)}" aria-pressed="{"true" if a == first else "false"}">{esc(a)}<b>{n}</b></button>'
            for a, n in ac)
        def row(i):
            dots = "".join(f'<i style="--c:{AROMA_COLOR.get(FL_INFO.get(a, {}).get("fam"), "#c9b8a0")}"></i>' for a in i["aroma"])
            nm = i["name"] if i["name"] != i["brand"] else ""
            return (f'<li data-aroma="{esc("|".join(i["aroma"]))}"{"" if first in i["aroma"] else " hidden"}>'
                    f'<a class="sc-row" href="{base}sake/{i["id"]}/"><span class="sc-dots">{dots}</span>'
                    f'<span class="sc-name"><b>{esc(i["brand"])}</b>{esc(nm)}</span>'
                    f'<span class="sc-aroma">{esc("・".join(i["aroma"]))}</span></a></li>')
        lis = "".join(row(i) for i in flavored)
        scent_html = f'''<section class="scent" aria-labelledby="sc-h">
  <div class="sec-head"><h2 id="sc-h">依香氣找</h2><p>想喝什麼味道？選一種香氣，看看有記錄到這種香氣的酒。</p></div>
  <div class="scent-chips" role="group" aria-label="香氣">{chips}</div>
  <ol class="scent-list" aria-live="polite">{lis}</ol>
</section>'''

    ph = []
    for n, i in enumerate(photos):
        cls = "ph is-lead" if n == 0 else "ph"
        sizes = "(max-width: 700px) 100vw, 50vw" if n == 0 else "(max-width: 700px) 50vw, 25vw"
        ph.append(
            f'<a class="{cls}" href="{base}sake/{i["id"]}/"><span class="ph-img">{photo_tag(i, base, sizes=sizes)}</span>'
            f'<span class="ph-cap"><b>{esc(i["brand"])}</b>{esc(i["name"] if i["name"] != i["brand"] else "")}</span></a>'
        )

    rice = Counter(r for i in items for r in i["riceList"])
    types = Counter(i.get("sakeType") for i in items if i.get("sakeType"))
    brews = Counter(i.get("brewery") for i in items if i.get("brewery"))

    def idx(counter, key, limit):
        rows = "".join(
            f'<li><a href="{base}sake/?{key}={esc(k)}"><span>{esc(k)}</span><i></i><b>{v}</b></a></li>'
            for k, v in counter.most_common(limit)
        )
        return rows

    tcount = Counter(i.get("sakeType") for i in items)
    mrows = []
    for label, a, b in TYPE_MATRIX:
        def cell(t):
            if not t:
                return '<td class="is-na"></td>'
            return f'<td><a href="{base}guide/#{esc(t)}"><span>{esc(t)}</span><b>{tcount.get(t, 0)}</b></a></td>'
        mrows.append(f'<tr><th scope="row">{esc(label)}</th>{cell(a)}{cell(b)}</tr>')

    body = f'''
<section class="spread" aria-labelledby="leaf-title-all">
  <div class="spread-map" data-atlas>
    {map_svg(prefs, base, intro=True)}
    <div class="map-tip" aria-hidden="true"><b></b><span></span></div>
    <ul class="areas" aria-label="依區域瀏覽">
      {"".join(f'<li><a href="{base}sake/?area={esc(a["key"])}" data-area="{esc(a["key"])}" style="--c:{a["color"]}"><span>{esc(a["key"])}</span><b>{sum(len(prefs[m]["items"]) for m in a["members"] if m in prefs)}</b></a></li>' for a in AREAS)}
    </ul>
  </div>
  <div class="spread-gutter" aria-hidden="true"></div>
  <article class="leaf" id="leaf">
    <div class="leaf-bg" aria-hidden="true"><i></i></div>
    <div class="leaf-body">{leaf_html(data["_all"], base, True).replace('class="leaf-title"', 'class="leaf-title" id="leaf-title-all"', 1)}</div>
  </article>
  <script type="application/json" id="atlas-data">{json.dumps(data, ensure_ascii=False)}</script>
</section>

{me_section(load_about(), base)}

<section class="fold" aria-labelledby="fold-h">
  <div class="sec-head">
    <h2 id="fold-h">最近喝過的</h2>
    <p>依品飲日期排列，從最新的一頁開始翻。</p>
  </div>
  <ol class="fold-track" tabindex="0" aria-label="最近的品飲紀錄，可左右捲動">{fold}</ol>
</section>

{scent_html}
<section class="index" aria-labelledby="idx-h">
  <div class="sec-head">
    <h2 id="idx-h">換個方式找</h2>
    <p>已經知道自己喜歡哪種米、哪個酒造，可以從這裡直接翻到。</p>
  </div>
  <div class="idx-cols">
    <div><h3>酒米</h3><ul class="idx">{idx(rice, "rice", 14)}</ul></div>
    <div><h3>酒種</h3><ul class="idx">{idx(types, "type", 14)}</ul></div>
    <div><h3>酒造</h3><ul class="idx">{idx(brews, "q", 14)}</ul></div>
  </div>
</section>

<section class="primer" aria-labelledby="pr-h">
  <div class="primer-copy">
    <h2 id="pr-h"><span class="nw">純米大吟釀和本釀造，</span><span class="nw">差在哪裡？</span></h2>
    <p>酒標上的名字，其實只回答兩件事：米磨掉多少，以及有沒有加釀造酒精。看懂這張表，點酒時就不用猜。</p>
    <a class="btn" href="{base}guide/">打開入門頁{icon("arrow")}</a>
  </div>
  <div class="primer-table">
    <table class="matrix">
      <caption class="sr">特定名稱酒的分類，以及這本圖鑑裡各有幾款</caption>
      <thead><tr><th scope="col">精米步合</th><th scope="col">只用米、米麴、水</th><th scope="col">另加釀造酒精</th></tr></thead>
      <tbody>{"".join(mrows)}</tbody>
    </table>
  </div>
</section>
'''
    desc = f"在日本地圖上翻閱 {len(items)} 款實際喝過的清酒：{rec_prefs} 個縣、{nbrew} 間酒造，附品飲紀錄、酒米與酒種。"
    return page(title="", desc=desc, depth=0, body=body, path="", body_class="is-home")


# ───────────────────────── 全部酒款 ─────────────────────────
def build_explore(items, order, prefs):
    base = "../"
    areas_opt = "".join(f'<option value="{esc(a["key"])}">{esc(a["key"])}</option>' for a in AREAS)
    pref_opt = "".join(
        f'<option value="{p["slug"]}" data-area="{esc(p["area"]["key"])}">{esc(p["name"])}（{len(p["items"])}）</option>'
        for p in sorted(prefs.values(), key=lambda p: p["code"]) if p["items"]
    )
    types = Counter(i.get("sakeType") for i in items if i.get("sakeType"))
    type_opt = "".join(f'<option value="{esc(t)}">{esc(t)}（{n}）</option>' for t, n in types.most_common())
    rice = Counter(r for i in items for r in i["riceList"])
    rice_opt = "".join(f'<option value="{esc(r)}">{esc(r)}（{n}）</option>' for r, n in rice.most_common())
    flc = Counter(t for i in items for t in i["aroma"] + i["palate"])
    fl_sel = ""
    if flc:
        fl_opt = "".join(f'<option value="{esc(t)}">{esc(t)}（{n}）</option>' for t, n in flc.most_common())
        fl_sel = f'<label class="f-sel"><span>風味</span><select name="fl"><option value="">全部</option>{fl_opt}</select></label>'
    cards = "".join(card(i, base) for i in order)
    body = f'''
<div class="ex">
  <div class="ex-head">
    <h1>全部酒款</h1>
    <p class="ex-count" id="ex-count" role="status" aria-live="polite">{len(items)} 款</p>
  </div>
  <form class="filters" id="filters" role="search" aria-label="篩選酒款">
    <div class="f-search">{icon("search")}<label class="sr" for="f-q">搜尋</label>
      <input id="f-q" name="q" type="search" placeholder="酒名、酒造、酒米、喝的地方" autocomplete="off" enterkeyhint="search"></div>
    <label class="f-sel"><span>區域</span><select name="area"><option value="">全部</option>{areas_opt}</select></label>
    <label class="f-sel"><span>縣</span><select name="pref"><option value="">全部</option>{pref_opt}</select></label>
    <label class="f-sel"><span>酒種</span><select name="type"><option value="">全部</option>{type_opt}</select></label>
    <label class="f-sel"><span>酒米</span><select name="rice"><option value="">全部</option>{rice_opt}</select></label>
    {fl_sel}
    <label class="f-chk"><input type="checkbox" name="photo" value="1"><span>有照片</span></label>
    <label class="f-chk"><input type="checkbox" name="note" value="1"><span>有心得</span></label>
    <label class="f-sel"><span>精米</span><select name="pol"><option value="">全部</option>{"".join(f'<option value="{v}">{v}% 以下</option>' for v in (70, 60, 50, 40, 35, 30, 20, 10))}</select></label>
    <label class="f-sel f-sort"><span>排序</span><select name="sort">
      <option value="">依產地</option><option value="latest">最近喝的在前</option><option value="like">喜歡程度高的在前</option><option value="name">依酒名</option></select></label>
    <div class="f-view" role="group" aria-label="顯示方式">
      <button type="button" data-view="grid" aria-pressed="true">{icon("grid")}<span>酒帖</span></button>
      <button type="button" data-view="list" aria-pressed="false">{icon("list")}<span>清單</span></button>
    </div>
    <button type="reset" class="f-reset" hidden>清除條件</button>
  </form>
  <div class="ex-list-head" aria-hidden="true"><span>酒款</span><span>酒造</span><span>縣</span><span>酒種</span><span>酒米</span><span>最近一次</span></div>
  <div class="cards" id="cards" data-view="grid">{cards}</div>
  <div class="empty" id="empty" hidden>
    <p>沒有符合這些條件的酒款。</p>
    <p>拿掉一個條件再試試，或<button type="button" class="linkish" data-clear>清除全部條件</button>。</p>
  </div>
</div>
'''
    return page(title="全部酒款", desc=f"{len(items)} 款實際喝過的清酒，可依區域、縣、酒種、酒米與品飲時間篩選。",
                depth=1, body=body, path="sake/", nav="sake", body_class="is-explore")


# ───────────────────────── 單一酒款 ─────────────────────────
SOURCE_LABEL = re.compile(r"^(?:https?://)?(?:www\.)?([^/]+)")


def related(it, items):
    seen = {it["id"]}
    groups = []

    def take(label, pool, limit):
        picked = []
        for x in pool:
            if x["id"] not in seen:
                picked.append(x)
                seen.add(x["id"])
            if len(picked) >= limit:
                break
        if picked:
            groups.append((label, picked))

    mine = set(it["aroma"] + it["palate"])
    if mine:
        scored = sorted(((len(mine & set(x["aroma"] + x["palate"])), x) for x in items if x["id"] != it["id"]), key=lambda p: -p[0])
        take("風味相近的酒", [x for n, x in scored if n >= 1], 6)
    take(f'同一間酒造：{it.get("brewery")}', [x for x in items if it.get("brewery") and x.get("brewery") == it.get("brewery")], 8)
    for r in it["riceList"][:1]:
        take(f"一樣用{r}", [x for x in items if r in x["riceList"]], 6)
    if it["pref"]:
        take(f'同樣來自{it["prefName"]}', [x for x in it["pref"]["items"]], 6)
    return groups


def backbar(href, label):
    return (f'<div class="backbar"><a class="back" href="{href}" data-back>{icon("prev")}'
            f'<span>返回<b data-back-label>{esc(label)}</b></span></a></div>')


CURRENCY = {"TWD": "NT$", "JPY": "¥", "USD": "US$", "HKD": "HK$", "EUR": "€"}


def fmt_day(t):
    if not t.get("ym"):
        return ""
    y, m = t["ym"]
    return f"{y} 年 {m} 月" + (f" {t['day']} 日" if t.get("day") else "")


def fmt_ml(v):
    v = _txt(v)
    if not v:
        return ""
    v = re.sub(r"\s*ml\s*$", "", v, flags=re.I).replace("-", "–")
    return f"{v} ml"


def price_html(t):
    """有金額就顯示；「價格公開」填「不公開」時隱藏。"""
    if t.get("pricePublic") in ("不公開", "否") or t.get("price") is None:
        return ""
    sym = CURRENCY.get(t.get("currency"), (t.get("currency") or "") + " ")
    amount = f"{sym}{t['price']:,.0f}"
    unit = t.get("priceUnit") or ""
    note = t.get("priceNote") or ""
    m = re.match(r"^\s*NT\.?\s*[\d,]+\s*(?:[（(](.+?)[)）])?\s*$", note)
    if m:
        note = m.group(1) or ""
    label = "套餐總價" if "套餐" in unit else "價格"
    unit_txt = "" if "套餐" in unit else (f"／{unit.replace('每', '')}" if unit else "")
    extra = f'<span class="t-price-note">{esc(note)}</span>' if note else ""
    mcups = re.search(r"(\d+)\s*杯", t.get("priceNote") or "")
    if "套餐" in unit and mcups and int(mcups.group(1)) > 1:
        extra += f'<span class="t-price-note">約每杯 {sym}{t["price"] / int(mcups.group(1)):,.0f}</span>'
    return f'<p class="t-price"><span>{label}</span><b>{amount}</b>{esc(unit_txt)}{extra}</p>'


def score_html(label, v):
    if v is None:
        return ""
    return (f'<div class="score"><span>{label}</span><i style="--v:{max(0, min(5, v)) / 5:.3f}" aria-hidden="true"></i>'
            f'<b>{v:g}</b><small>/ 5</small></div>')


def tasting_html(t, base):
    shown = any(t.get(k) for k in ("ym", "place", "method", "notes", "shop")) or t.get("like") is not None
    if not shown:
        return ""
    bits = []
    if t.get("method"):
        bits.append(f'<span class="tag">{esc(t["method"])}</span>')
    if t.get("acquisition"):
        bits.append(f'<span class="tag is-soft">{esc(t["acquisition"])}</span>')
    where = t.get("place") or t.get("shop") or ""
    vol = fmt_ml(t.get("cupMl"))
    vol = f"單杯 {vol}" if vol else (f"瓶裝 {fmt_ml(t.get('bottleMl'))}" if t.get("bottleMl") else "")
    lines = []
    if where:
        lines.append(f'<p class="t-where">{esc(where)}</p>')
    if t.get("shop") and t.get("shop") != where:
        lines.append(f'<p class="t-sub">購入：{esc(t["shop"])}</p>')
    sub = [x for x in [vol,
                       f"酒造年度 {esc(t['by'])}" if t.get("by") else "",
                       f"出荷 {esc(t['shipped'])}" if t.get("shipped") else "",
                       f"開瓶 {esc(t['opened'])}" if t.get("opened") else ""] if x]
    if sub:
        lines.append(f'<p class="t-sub">{"　".join(sub)}</p>')
    lines.append(price_html(t))
    if t.get("notes"):
        lines.append(f'<p class="t-note">{flavor_mark(t["notes"])}</p>')
    if t.get("afterOpen"):
        lines.append(f'<p class="t-after"><span>開瓶後</span>{flavor_mark(t["afterOpen"])}</p>')
    scores = score_html("喜歡程度", t.get("like")) + score_html("再喝意願", t.get("again"))
    if scores:
        lines.append(f'<div class="scores">{scores}<a class="score-help" href="{base}about/#score">評分標準</a></div>')
    ph = []
    for f in t.get("photos") or []:
        src = f if re.match(r"^https?://", f) else f"{base}assets/images/{f}"
        ph.append(f'<img src="{esc(src)}" alt="這次品飲的照片" loading="lazy" decoding="async">')
    if ph:
        lines.append(f'<div class="t-photos">{"".join(ph)}</div>')
    date = fmt_day(t) or "日期未記錄"
    return f'<li class="t"><p class="t-date">{esc(date)}</p><div class="t-body"><p class="t-tags">{"".join(bits)}</p>{"".join(lines)}</div></li>'


# ───────────────────────── 斟一杯 ─────────────────────────
_CLOUDY = re.compile(r"にごり|濁|霞|かすみ|うすにごり|活性|澱")
_AMBER = re.compile(r"熟成|古酒|秘藏|秘蔵|長期|琥珀|貴釀|貴醸")
_PINK = re.compile(r"Pink|pink|ピンク|粉紅|桃色|ロゼ|[Rr]os[eé]")
_FIZZ = re.compile(r"スパークリング|[Ss]parkling|發泡|発泡|活性|ガス")


def spec_html(it, base):
    cells = []
    if it.get("sakeType"):
        cells.append(f'<div><dt>酒種</dt><dd><a href="{base}sake/?type={esc(it["sakeType"])}">{esc(it["sakeType"])}</a></dd></div>')
    if it["riceList"]:
        rice = "、".join(f'<a href="{base}sake/?rice={esc(r)}">{esc(r)}</a>' for r in it["riceList"])
        cells.append(f"<div><dt>酒米</dt><dd>{rice}</dd></div>")
    if it["polish"]:
        frac = it["polish"] / 100
        rx, ry = grain_geom(frac)
        at_most = "以下" in it["polishLabel"]
        cells.append(
            f'<div class="spec-pol" data-grain data-p="{frac:.4f}"><dt>精米步合</dt><dd>'
            f'<svg class="spec-grain" viewBox="0 0 120 150" aria-hidden="true">{GRAIN_DEFS}'
            f'<ellipse class="grain-whole" cx="60" cy="75" rx="44" ry="62"/>'
            f'<ellipse class="grain-left" cx="60" cy="75" rx="{rx:.2f}" ry="{ry:.2f}" fill="url(#rg)"/></svg>'
            f'<span><b data-grain-num>{it["polish"]:g}</b>%{" 以下" if at_most else ""}'
            f'<small>磨掉{"至少 " if at_most else " "}{100 - it["polish"]:g}%</small></span></dd></div>')
    elif it.get("polishLabel"):
        cells.append(f'<div><dt>精米步合</dt><dd>{esc(it["polishLabel"])}</dd></div>')
    made = re.sub(r"\s*月\s*$", "", it.get("made") or "")
    if it.get("by"):
        cells.append(f'<div><dt>酒造年度</dt><dd>{esc(it["by"])}</dd></div>')
    if made:
        cells.append(f'<div><dt>製造年月</dt><dd>{esc(made)}</dd></div>')
    out = f'<dl class="spec">{"".join(cells)}</dl>' if cells else ""
    if it.get("remark"):
        out += f'<p class="t-sub spec-remark">{esc(it["remark"])}</p>'
    return out



def dendo_of(it):
    """殿堂印:喜歡程度 >= DENDO 才蓋的朱印。"""
    lk = it.get("like")
    if lk is None or float(lk) < DENDO:
        return ""
    return (f'<span class="c-dendo" role="img" aria-label="殿堂・喜歡程度 {float(lk):g}" title="殿堂・喜歡程度 {float(lk):g} / 5">'
            f'{seal("殿堂", tilt=-5)}</span>')


def taste_section(it, items, base):
    """「這一杯」：倒酒動畫、香氣與口感詞、香氣輪、口感墨形。"""
    aroma, palate = it["aroma"], it["palate"]
    ts = [t for t in it["tastings"] if t.get("cupMl") or t.get("bottleMl") or t.get("method")]
    if not ts and not (aroma or palate):
        return ""
    t = ts[0] if ts else {}
    text = " ".join([it["brand"], it["name"], it.get("note") or ""] + it["notesAll"] + aroma + palate)
    bowl_bottom, rim = 119.0, 14.0
    y_full = rim - 2

    def fill_of(tt):
        """依喜歡程度決定倒多滿：4.8 以上滿到溢出，4.2–4.7 八分滿，3.8–4.1 六分滿，3.0–3.7 四分滿，3 以下兩分滿。"""
        lk = like_of(tt)
        if lk is None:
            return 0.5, "還沒評分，先倒半杯"
        lk = float(lk)
        for lo, f, word in ((4.8, 1.0, "滿到溢出來"), (4.2, 0.8, "倒到八分滿"), (3.8, 0.6, "倒到六分滿"), (3.0, 0.4, "倒到四分滿")):
            if lk >= lo - 1e-9:
                return f, word
        return 0.2, "倒到兩分滿"

    def like_of(tt):
        return tt.get("like") if tt.get("like") is not None else it.get("like")

    def level_of(tt):
        f, _ = fill_of(tt)
        return (bowl_bottom - f * (bowl_bottom - rim)) - y_full

    def like_txt(tt):
        lk = like_of(tt)
        return "還沒評分" if lk is None else f"喜歡程度 {lk:g} / 5"

    def over_of(tt):
        return fill_of(tt)[0] >= 1.0

    # 倒酒一律由片口（katakuchi）斟出：單杯是店家倒的那一杯，整瓶也先分到片口再斟，
    # 迴避「酒瓶和杯子比例」的問題；容量資訊仍寫在文字裡。

    def vol_of(tt):
        cup, btl = fmt_ml(tt.get("cupMl")), fmt_ml(tt.get("bottleMl"))
        if tt.get("method") == "單杯" or (cup and tt.get("method") != "整瓶"):
            return f"單杯 {cup}" if cup else "單杯"
        if tt.get("method") == "整瓶" or btl:
            return f"整瓶 {btl}" if btl else "整瓶"
        return tt.get("method") or ""

    def where_of(tt):
        w = re.sub(r"\s*[（(].*?[)）]\s*", "", tt.get("place") or tt.get("shop") or "")
        return "・".join(x for x in [fmt_day(tt), w] if x)
    tone = "is-cloudy" if _CLOUDY.search(text) else "is-pink" if _PINK.search(text) else "is-amber" if _AMBER.search(text) else ""
    fizz = "氣泡感" in palate or bool(_FIZZ.search(it["name"]))
    off0 = level_of(t) if t else (bowl_bottom - 0.5 * (bowl_bottom - rim)) - y_full
    y_t = y_full + off0
    drop = bowl_bottom - y_full + 6
    vol = vol_of(t) if t else ""
    bubbles = "".join(
        f'<circle cx="{62 + (k * 7) % 16}" cy="{bowl_bottom - 5}" r="{1.1 + (k % 3) * 0.5:.1f}" style="--d:{k * 0.37:.2f}s;--h:{-(bowl_bottom - y_t - 6):.0f}px"/>'
        for k in range(9)) if fizz else ""
    # 香氣＝「香の粒」：杯口上方緩緩升起的發光微粒（顏色依香氣家族），
    # 取代舊的波浪蒸氣線（看起來像臭味/熱氣）。
    _mx = (106, 136, 96, 146, 120)
    motes = "".join(
        f'<g class="pour-mote" data-fl="{esc(w)}" style="--c:{AROMA_COLOR.get(FL_INFO.get(w, {}).get("fam"), "#d9b36b")};--i:{k};--sx:{(k % 3 - 1) * 11 or 7}px" '
        f'transform="translate({_mx[k]},72)"><circle class="pm-halo" r="5.4"/><circle class="pm-core" r="2.1"/></g>'
        for k, w in enumerate(aroma[:5]))
    extras = [("有氣泡" if fizz else ""), ("白濁" if tone == "is-cloudy" else "")]
    meta = "　".join(x for x in [vol] + extras if x)
    tabs = ""
    if len(ts) > 1:
        bts = []
        for k, tt in enumerate(ts[:4]):
            m2 = "　".join(x for x in [vol_of(tt)] + extras if x)
            short = re.sub(r"\s*[（(].*?[)）]\s*", "", tt.get("place") or tt.get("shop") or "")
            ym = f'{tt["ym"][0]}.{tt["ym"][1]:02d}' if tt.get("ym") else ""
            lab = "　".join(x for x in [ym, short] if x) + (f"・{tt.get('method')}" if tt.get("method") else "")
            bts.append(f'<button type="button" role="tab" aria-selected="{"true" if k == 0 else "false"}" data-tid="{esc(tt.get("id") or "")}" data-off="{level_of(tt):.1f}" '
                       f'data-meta="{esc(m2)}" data-where="{esc(where_of(tt))}" data-like="{esc(like_txt(tt))}" data-over="{1 if over_of(tt) else 0}">{esc(lab)}</button>')
        tabs = f'<div class="pour-tabs" role="tablist" aria-label="喝過 {len(ts)} 次，選一次看">{"".join(bts)}</div>'
    where = where_of(t) if t else ""
    # 德利（とっくり）：從右上傾入斟酒，斟完退場。線描畫法與杯子同一枝筆；
    # 旋轉軸就是壺口，酒柱永遠從口沿落下。
    kata = '''<g class="pour-tok" aria-hidden="true">
            <path class="pt-fill" d="M-9 0 C-10 4 -6 7 -5.5 11 C-5 15 -17 20 -17 34 C-17 46 -11 52 0 52 C11 52 17 46 17 34 C17 20 5 15 5.5 11 C6 7 10 4 9 0 Z"/>
            <path class="pt-line" d="M-9 0 C-10 4 -6 7 -5.5 11 C-5 15 -17 20 -17 34 C-17 46 -11 52 0 52 C11 52 17 46 17 34 C17 20 5 15 5.5 11 C6 7 10 4 9 0"/>
            <ellipse class="pt-mouth" cx="0" cy="0" rx="9" ry="2.6"/>
            <path class="pt-ring" d="M-16.6 30 C-8 33 8 33 16.6 30"/>
          </g>'''
    vbox = "50 0 145 284"
    chip = lambda w: f'<button type="button" class="fl-chip" data-fl="{esc(w)}">{esc(w)}</button>'
    rows = ""
    if aroma:
        rows += f'<div><dt>香氣</dt><dd>{"".join(chip(w) for w in aroma)}</dd></div>'
    if palate:
        rows += f'<div><dt>口感</dt><dd>{"".join(chip(w) for w in palate)}</dd></div>'
    hint = "點一下杯子再倒一杯" + ("；滑過香氣或口感的詞，看每一種的說明。" if rows else "。")
    glass = f'''<button type="button" class="pour-glass" aria-label="再倒一杯">
        <svg viewBox="{vbox}" aria-hidden="true">
          <defs>
            <filter id="aroma-soft" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="4"/></filter>
            <clipPath id="bowl"><path d="M43 14 C40 40 33 58 34 76 C35 100 52 116 70 120 C88 116 105 100 106 76 C107 58 100 40 97 14 Z"/></clipPath>
            <linearGradient id="sake-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="lq0"/><stop offset="1" class="lq1"/></linearGradient>
          </defs>
          {kata}
          <rect class="pour-stream" x="119.7" y="45" width="2.7" height="{y_t + 19:.0f}" rx="1.3"/>
          <g transform="translate(50,64)">
            <g clip-path="url(#bowl)"><g class="pour-liquid">
              <rect x="20" y="{y_full:.1f}" width="100" height="{bowl_bottom - y_full + 8:.1f}" fill="url(#sake-fill)"/>
              <path class="pour-wave" d="M-40 {y_full:.1f} q 10 -3 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 v 6 h -200 z"/>
              <g class="pour-bubbles">{bubbles}</g></g></g>
            <ellipse class="pour-dome" cx="70" cy="14" rx="27.5" ry="3.4"/>
            <path class="pour-drip" pathLength="1" d="M44 14 C40 40 32.6 58 33.4 76 C34.6 100 51 116.5 69 121 L69 193"/>
            <path class="pour-drip is-r" pathLength="1" d="M96.6 14 C100.4 40 107.2 58 106.4 78 C105.6 98 98 108 92 113"/>
            <ellipse class="pour-puddle" cx="70" cy="198.5" rx="31" ry="3.6"/>
            <path class="pour-glassline" d="M43 14 C40 40 33 58 34 76 C35 100 52 116 70 120 C88 116 105 100 106 76 C107 58 100 40 97 14"/>
            <path class="pour-shine" d="M44 30 C39 50 39 74 49 96"/>
            <path class="pour-stem" d="M68.6 119 C69.4 140 69.4 176 68 193 L72 193 C70.6 176 70.6 140 71.4 119 Z"/>
            <path class="pour-glassline" d="M43 197 C52 192 62 192.6 70 192.6 C78 192.6 88 192 97 197"/>
            <ellipse class="pour-glassline" cx="70" cy="197.4" rx="27" ry="3.2"/>
          </g>
          <g class="pour-motes">{motes}</g>
        </svg>
      </button>'''
    viz, data_json, say = "", "", ""
    if aroma or palate:
        figs = []
        if aroma:
            figs.append(f'''<figure class="viz">
          <div class="wheel">{wheel_svg(set(aroma))}
            <div class="wheel-core"><b data-core-word>{esc(aroma[0])}</b><span data-core-fam>{esc(FL_INFO.get(aroma[0], {}).get("fam", ""))}</span></div></div>
          <figcaption>香氣輪：亮起的是這支酒的香氣</figcaption></figure>''')
        if palate:
            shapes = {FL_INFO.get(w, {}).get("shape") for w in palate}
            cls = " ".join(c for c, keys in (("has-acid", {"acid"}), ("has-fizz", {"fizz"}), ("is-full", {"full"}), ("is-light", {"light"}),
                                             ("is-sweet", {"sweet"}), ("is-bitter", {"bitter"}), ("is-smooth", {"round", "smooth"}),
                                             ("is-crisp", {"sharp"}), ("is-umami", {"umami"})) if shapes & keys)
            rnd = random.Random(it["id"])
            bub = "".join(
                f'<circle cx="{rnd.uniform(-78, 78):.1f}" cy="{rnd.uniform(-78, 78):.1f}" r="{rnd.uniform(1.6, 3.6):.1f}" style="--d:{rnd.uniform(0, 3):.2f}s"/>'
                for _ in range(16))
            figs.append(f'''<figure class="viz">
          <div class="cup {cls}" data-cup><svg viewBox="-130 -130 260 260" aria-hidden="true">
            <defs>
              <radialGradient id="cup-porc" cx="50%" cy="44%" r="58%"><stop offset="0" stop-color="#ffffff"/><stop offset=".8" stop-color="#f3f1ea"/><stop offset="1" stop-color="#d9d4c8"/></radialGradient>
              <radialGradient id="cup-sake" cx="44%" cy="40%" r="66%"><stop offset="0" class="ck0"/><stop offset="1" class="ck1"/></radialGradient>
              <radialGradient id="cup-glow" cx="36%" cy="30%" r="42%"><stop offset="0" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
              <clipPath id="cup-liquid"><circle r="103"/></clipPath>
            </defs>
            <circle r="121" fill="url(#cup-porc)"/>
            <circle r="108" class="cup-wall"/>
            <g clip-path="url(#cup-liquid)">
              <circle r="104" fill="#fdfdfb"/>
              <circle r="104" class="sake-pool" fill="url(#cup-sake)"/>
              <circle r="47" class="janome"/>
              <g class="cup-ripples"><circle r="100"/><circle r="100"/><circle r="100"/></g>
              <circle r="100" class="cup-burst"/>
              <g class="cup-bubbles">{bub}</g>
              <ellipse class="cup-shine" cx="-30" cy="-40" rx="62" ry="32" fill="url(#cup-glow)"/>
            </g>
            <circle r="103.5" class="cup-meniscus"/>
          </svg></div>
          <figcaption>品酒杯：顏色、漣漪與氣泡依口感</figcaption></figure>''')
        viz = f'<div class="taste-viz{" is-one" if len(figs) == 1 else ""}">{"".join(figs)}</div>'
        same = {w: [{"id": x["id"], "t": x["brand"] + ("　" + x["name"] if x["name"] != x["brand"] else "")}
                    for x in items if x["id"] != it["id"] and w in (x["aroma"] + x["palate"])][:6] for w in aroma + palate}
        info = {**{k: {kk: vv for kk, vv in v.items() if kk != "pats"} for k, v in FL_INFO.items()},
                **{w: {"kind": "aroma" if w in aroma else "palate", "fam": "其他", "desc": "這支酒紀錄裡的描述。"}
                   for w in aroma + palate if w not in FL_INFO}}
        data_json = f'<script type="application/json" class="fl-data">{json.dumps({"aroma": aroma, "palate": palate, "info": info, "same": same, "base": base}, ensure_ascii=False)}</script>'
        say = '<div class="fl-say" aria-live="polite"><p class="fl-say-t" data-say-t></p><p class="fl-say-d" data-say-d></p><p class="fl-say-more" data-say-more></p></div>'
    over0 = over_of(t) if t else False
    attrs = (f'class="taste pour {tone}{" has-fizz" if fizz else ""}{" is-overflow" if over0 else ""}" data-pour '
             f'style="--drop:{drop:.0f}px;--off:{off0:.1f}px"') + (" data-flavor" if aroma or palate else "")
    return f'''<section {attrs} aria-labelledby="ta-h">
      <h2 id="ta-h">這一杯{f'<small>喝過 {len(ts)} 次</small>' if len(ts) > 1 else ""}</h2>
      {tabs}
      <div class="taste-top">{glass}
        <div class="taste-sum">{f'<p class="pour-vol">{esc(meta)}</p>' if meta else ""}
          {f'<p class="pour-where">{esc(where)}</p>' if where else ""}
          {f'<p class="pour-like{" is-none" if like_of(t) is None else ""}">{esc(like_txt(t))}</p>' if t else ""}
          {f'<dl class="taste-rows">{rows}</dl>' if rows else ""}
          <p class="pour-hint">{hint}</p></div>
      </div>
      {viz}{say}{data_json}
    </section>'''


def flavor_html(it):
    """選填欄位：sweetness（1-5）、body（1-5）、servingTemps、pairing。"""
    sweet, body = it.get("sweetness"), it.get("body")
    temps, pairing = it.get("servingTemps"), it.get("pairing")
    if not (sweet or body or temps or pairing):
        return ""
    out = ['<section class="sk-sec" aria-labelledby="fx-h"><h2 id="fx-h">飲用建議</h2>']
    if sweet and body:
        x = (float(sweet) - 1) / 4 * 100
        y = 100 - (float(body) - 1) / 4 * 100
        out.append(f'''<div class="flav" role="img" aria-label="甜度 {esc(sweet)} / 5，酒體 {esc(body)} / 5">
          <span class="flav-x">辛口</span><span class="flav-x is-r">甘口</span>
          <span class="flav-y">濃郁</span><span class="flav-y is-b">輕盈</span>
          <i style="left:{x:.0f}%;top:{y:.0f}%"></i></div>''')
    if temps:
        out.append(f'<p class="t-sub">建議溫度：{esc("、".join(temps) if isinstance(temps, list) else temps)}</p>')
    if pairing:
        out.append(f'<p class="t-sub">搭配：{esc("、".join(pairing) if isinstance(pairing, list) else pairing)}</p>')
    out.append("</section>")
    return "".join(out)


def build_sake(it, items, order):
    base = "../../"
    p = it["pref"]
    idx = it["order"]
    prev_it = order[idx - 1] if idx > 0 else None
    next_it = order[idx + 1] if idx + 1 < len(order) else None
    slides = it.get("slides") or []
    if it["photo"] and len(slides) > 1:
        # 好幾張照片：大圖本身左右滑動；滑到哪張，品飲紀錄與「這一杯」就切到那一次
        sl = []
        for k, (tid, f) in enumerate(slides):
            one = dict(it, photo=f)
            w, h = photo_dim(one)
            fit = " is-fit" if abs(w / h - photo_dim(it)[0] / photo_dim(it)[1]) > 0.02 else ""
            sl.append(f'<div class="sk-slide{fit}{" is-on" if k == 0 else ""}" data-tid="{esc(tid)}" role="group" aria-roledescription="照片" aria-label="第 {k + 1} 張，共 {len(slides)} 張">'
                      f'{photo_tag(one, base, sizes="(max-width: 860px) 100vw, 42vw", eager=k == 0)}</div>')
        dots = "".join(f'<i{" class=\"is-on\"" if k == 0 else ""}></i>' for k in range(len(slides)))
        cover = (f'<figure class="sk-cover is-photo has-slides"{ar_style(it)} data-lightbox data-slides tabindex="0" role="button" aria-label="放大照片，可左右滑動看其他照片">'
                 f'<div class="sk-slides">{"".join(sl)}</div>'
                 f'<span class="sk-count" aria-hidden="true"><b>1</b> / {len(slides)}</span>'
                 f'<span class="sk-dots" aria-hidden="true">{dots}</span>'
                 f'<button type="button" class="sk-nav is-prev" aria-label="上一張" tabindex="-1"></button>'
                 f'<button type="button" class="sk-nav is-next" aria-label="下一張" tabindex="-1"></button>'
                 f'</figure>')
    elif it["photo"]:
        cover = (f'<figure class="sk-cover is-photo"{ar_style(it)} data-lightbox tabindex="0" role="button" aria-label="放大照片">'
                 f'{photo_tag(it, base, sizes="(max-width: 860px) 100vw, 42vw", eager=True)}</figure>')
    else:
        cover = f'<figure class="sk-cover is-washi">{goshuin(it, "cover")}</figure>'
    note = it.get("note") or ""
    note_html = f'<blockquote class="sk-note"><p>{flavor_mark(note)}</p></blockquote>' if note else ""
    if it.get("imageCaption"):
        note_html += f'<p class="t-sub">照片註記：{esc(it["imageCaption"])}</p>'

    def fact(label, val, href=None, empty="未記錄"):
        if not val:
            return f'<div><dt>{label}</dt><dd class="is-empty">{empty}</dd></div>'
        v = f'<a href="{href}">{esc(val)}</a>' if href else esc(val)
        return f"<div><dt>{label}</dt><dd>{v}</dd></div>"

    batch = [x for x in [it.get("by"), (f'{it["made"]} 製造' if it.get("made") else "")] if x]
    batch_fact = f'<div><dt>批次</dt><dd>{esc("，".join(batch))}</dd></div>' if batch else ""
    rice_html = "、".join(f'<a href="{base}sake/?rice={esc(r)}">{esc(r)}</a>' for r in it["riceList"])
    polish = it["polish"]
    grain = ""
    if polish:
        frac = polish / 100
        rx, ry = grain_geom(frac)
        dia = round(frac ** (1 / 3) * 100)
        num = f"{polish:g}"
        at_most = "以下" in it["polishLabel"]
        lead = (f"這支酒的米至少磨掉了 {100 - polish:g}%。" if at_most
                else f"這支酒的米磨掉了 {100 - polish:g}%，只留下中心的 {num}%。")
        grain = f'''<div class="grain" data-grain data-p="{frac:.4f}">
          <svg viewBox="0 0 120 150" aria-hidden="true">{GRAIN_DEFS}<ellipse class="grain-whole" cx="60" cy="75" rx="44" ry="62"/>
          <ellipse class="grain-left" cx="60" cy="75" rx="{rx:.2f}" ry="{ry:.2f}" fill="url(#rg)"/></svg>
          <div class="grain-text"><p class="grain-num"><b data-grain-num>{num}</b>%{" 以下" if at_most else ""}</p>
          <p>{lead}</p><p class="t-sub">重量剩 {num}%，米粒的直徑大約是原本的 {dia}%。</p></div></div>'''

    facts = f'''<dl class="facts">
      {fact("酒種", it.get("sakeType"), f'{base}sake/?type={esc(it.get("sakeType"))}' if it.get("sakeType") else None)}
      <div><dt>酒米</dt><dd{' class="is-empty"' if not rice_html else ""}>{rice_html or "未記錄"}</dd></div>
      {fact("精米步合", it["polishLabel"])}
      {fact("酒造", it.get("brewery"), f'{base}pref/{p["slug"]}/#b-{stable_hash(it.get("brewery") or "")}' if p and it.get("brewery") else None)}
      {fact("產地", (it["prefName"] + "縣" if it["prefName"] not in ("北海道", "東京", "京都", "大阪") else it["prefName"]) if it["prefName"] else "", f'{base}pref/{p["slug"]}/' if p else None)}
      {batch_fact}
    </dl>
    {f'<p class="t-sub">{esc(it["remark"])}</p>' if it.get("remark") else ""}'''

    tastings = it["tastings"]
    rec = [(t, tasting_html(t, base)) for t in tastings]
    rec = [(t, h) for t, h in rec if h]
    t_sec = ""
    if len(rec) == 1:
        t_sec = f'''<section class="sk-sec" aria-labelledby="t-h"><h2 id="t-h">品飲紀錄</h2><ol class="ts">{rec[0][1]}</ol></section>'''
    elif rec:
        # 喝過好幾次：同一頁切換，一次只看一筆（沒有 JavaScript 時全部列出）
        btns, panes = [], []
        for k, (t, h) in enumerate(rec):
            tid = esc(t.get("id") or f"t{k}")
            ym = f'{t["ym"][0]}.{t["ym"][1]:02d}' if t.get("ym") else "日期未記錄"
            short = re.sub(r"\s*[（(].*?[)）]\s*", "", t.get("place") or t.get("shop") or "")
            lab = f'<b>{esc(ym)}</b>' + (f'<span>{esc(short)}</span>' if short else "")
            on = k == 0
            btns.append(f'<button type="button" role="tab" id="tt-{tid}" aria-controls="tp-{tid}" aria-selected="{"true" if on else "false"}" '
                        f'tabindex="{0 if on else -1}" data-tid="{tid}">{lab}</button>')
            panes.append(h.replace('<li class="t">', f'<li class="t{" is-on" if on else ""}" role="tabpanel" id="tp-{tid}" aria-labelledby="tt-{tid}" data-tid="{tid}">', 1))
        t_sec = (f'<section class="sk-sec" aria-labelledby="t-h" data-records><h2 id="t-h">品飲紀錄<small>喝過 {len(rec)} 次</small></h2>'
                 f'<div class="ts-tabs" role="tablist" aria-label="選一次品飲">{"".join(btns)}</div>'
                 f'<ol class="ts is-tabbed" tabindex="-1">{"".join(panes)}</ol>'
                 f'<div class="ts-dots" aria-hidden="true">{"".join(f"<i{chr(32)}class=\"is-on\"></i>" if k == 0 else "<i></i>" for k in range(len(rec)))}</div></section>')

    srcs = it.get("sources") or []
    src_html = ""
    if srcs:
        lis = "".join(
            f'<li><a href="{esc(u)}" rel="noopener nofollow" target="_blank">{esc(SOURCE_LABEL.match(u).group(1) if SOURCE_LABEL.match(u) else u)}{icon("out")}</a></li>'
            for u in srcs if re.match(r"^https?://", u)
        )
        src_html = f'<section class="sk-sec is-quiet" aria-labelledby="s-h"><h2 id="s-h">規格參考來源</h2><ul class="srcs">{lis}</ul>' + \
                   (f'<p class="t-sub">{esc(it.get("specNote"))}</p>' if it.get("specNote") else "") + "</section>"

    rel_html = "".join(
        f'<section class="rel" aria-label="{esc(label)}"><h2>{esc(label)}</h2><ol class="fold-track is-small">'
        + "".join(f"<li>{card(x, base)}</li>" for x in xs) + "</ol></section>"
        for label, xs in related(it, items)
    )

    def pn(x, cls, label):
        if not x:
            return "<span></span>"
        ic = icon("prev") if cls == "is-prev" else ""
        ic2 = icon("next") if cls == "is-next" else ""
        return f'<a class="pn {cls}" href="{base}sake/{x["id"]}/">{ic}<span><small>{label}</small>{esc(x["brand"])}　{esc(x["name"] if x["name"] != x["brand"] else "")}</span>{ic2}</a>'

    crumbs = f'<nav class="crumbs" aria-label="位置"><a href="{base}sake/">全部酒款</a>{icon("next")}' + \
             (f'<a href="{base}pref/{p["slug"]}/">{esc(p["name"])}</a>{icon("next")}' if p else "") + \
             f'<span aria-current="page">{esc(it["brand"])}</span></nav>'

    title_name = it["name"] if it["name"] and it["name"] != it["brand"] else ""
    body = f'''
{backbar(f"{base}sake/", "全部酒款")}
<article class="sk">
  <div class="sk-left">{cover}</div>
  <div class="sk-right">
    {crumbs}
    <header class="sk-head">
      <h1><span class="sk-brand">{esc(it["brand"])}{dendo_of(it)}</span>{f'<span class="sk-name">{esc(title_name)}</span>' if title_name else ""}</h1>
      <p class="sk-by">{esc(it.get("brewery") or "")}{"，" if it.get("brewery") and it["prefName"] else ""}{esc(it["prefName"])}</p>
    </header>
    {note_html}
    {spec_html(it, base)}
    {taste_section(it, items, base)}
    {t_sec}
    {flavor_html(it)}
  </div>
</article>
<div class="rels">{rel_html}</div>
<nav class="pns" aria-label="上一款與下一款">{pn(prev_it, "is-prev", "上一款")}{pn(next_it, "is-next", "下一款")}</nav>
'''
    desc_bits = [it["brand"], title_name, it.get("brewery"), it["prefName"], it.get("sakeType"), " / ".join(it["riceList"])]
    desc = "，".join(b for b in desc_bits if b)
    if note:
        desc += "。" + note[:60]
    elif it["notesAll"]:
        desc += "。" + it["notesAll"][0][:60]
    else:
        desc += "。實際品飲紀錄與酒款規格。"
    og = f'assets/images/{it["photo"]}' if it["photo"] else ""
    return page(title=f'{it["brand"]} {title_name}'.strip(), desc=desc, depth=2, body=body,
                path=f'sake/{it["id"]}/', nav="sake", og_image=og, body_class="is-sake")


# ───────────────────────── 縣別頁 ─────────────────────────
UNKNOWN_BREW = "酒造未記錄"
def build_pref(p, prefs, items):
    base = "../../"
    rec = [x for x in sorted(prefs.values(), key=lambda x: x["code"]) if x["items"]]
    i = rec.index(p)
    prev_p, next_p = (rec[i - 1] if i > 0 else None), (rec[i + 1] if i + 1 < len(rec) else None)
    by_brew = defaultdict(list)
    for it in p["items"]:
        by_brew[it.get("brewery") or UNKNOWN_BREW].append(it)
    brews = sorted(by_brew.items(), key=lambda kv: (kv[0] == UNKNOWN_BREW, -len(kv[1]), kv[0]))
    seal_for = lambda b, its: "未詳" if b == UNKNOWN_BREW else its[0]["seal"]
    n_known = sum(1 for b, _ in brews if b != UNKNOWN_BREW)
    lt = max((x["latest"] for x in p["items"] if x["latest"]), default=None)

    seal_list = "".join(
        f'<li><a href="#b-{stable_hash(b)}">{seal(seal_for(b, its), "is-list")}<span>{esc(b)}</span><b>{len(its)}</b></a></li>'
        for b, its in brews
    )
    groups = "".join(
        f'''<section class="brew" id="b-{stable_hash(b)}" aria-labelledby="bh-{stable_hash(b)}">
          <header class="brew-head">{seal(seal_for(b, its), "is-head")}<h2 id="bh-{stable_hash(b)}">{esc(b)}</h2><p>{len(its)} 款</p></header>
          <div class="cards" data-view="grid">{"".join(card(x, base) for x in sorted(its, key=lambda x: x["latest"] or (0, 0), reverse=True))}</div>
        </section>'''
        for b, its in brews
    )

    def pn(x, cls, label):
        if not x:
            return "<span></span>"
        return f'<a class="pn {cls}" href="{base}pref/{x["slug"]}/">{icon("prev") if cls == "is-prev" else ""}<span><small>{label}</small>{esc(x["name"])}（{len(x["items"])} 款）</span>{icon("next") if cls == "is-next" else ""}</a>'

    body = f'''
{backbar(base, "日本地圖")}
<section class="spread is-pref" aria-labelledby="pref-h">
  <div class="spread-map" data-atlas-lite>{map_svg(prefs, base, current=p["slug"], labels=False)}<div class="map-tip" aria-hidden="true"><b></b><span></span></div></div>
  <div class="spread-gutter" aria-hidden="true"></div>
  <article class="leaf is-static">
    <div class="leaf-bg" aria-hidden="true"><i></i></div>
    <div class="leaf-body">
    <div class="leaf-top">
      {scene_html(p["slug"], base)}
      <div class="leaf-ink">
        <p class="leaf-area">{esc(p["area"]["key"])}</p>
        <h1 class="leaf-title" id="pref-h">{esc(p["name"])}</h1>
        <p class="leaf-count"><span class="tcy">{len(p["items"])}</span>款<span class="gap"></span><span class="tcy">{n_known}</span>間酒造</p>
      </div>
      <div class="leaf-seals">{"".join(seal(seal_for(b, its), f"leaf-seal s{n}", ((n * 37) % 9) - 4) for n, (b, its) in enumerate([x for x in brews if x[0] != UNKNOWN_BREW][:6]))}</div>
      {side_html(p["slug"], ("最近一次　" + esc(kanji_date(lt))) if lt else "")}
    </div>
    <ul class="seal-list" aria-label="{esc(p["name"])}的酒造">{seal_list}</ul>
    </div>
  </article>
</section>
<div class="brews">{groups}</div>
<nav class="pns" aria-label="上一個縣與下一個縣">{pn(prev_p, "is-prev", "上一個縣")}{pn(next_p, "is-next", "下一個縣")}</nav>
'''
    names = "、".join(b for b, _ in brews[:5] if b != UNKNOWN_BREW)
    desc = f'{p["name"]}的 {len(p["items"])} 款清酒品飲紀錄，來自 {n_known} 間酒造：{names}。'
    return page(title=f'{p["name"]}的清酒', desc=desc, depth=2, body=body, path=f'pref/{p["slug"]}/', body_class="is-pref")


# ───────────────────────── 入門 ─────────────────────────
GLOSSARY = [
    ("生酒", ["生酒", "生原酒", "本生", "釀生酒"], "完全沒有經過加熱殺菌（火入れ）的酒。香氣鮮活，常帶一點微氣泡感，需要冷藏保存。"),
    ("火入", ["火入"], "加熱殺菌。一般清酒在貯藏前與出貨前各做一次，讓風味穩定、可常溫保存。酒標特別寫出來，多半是為了和同款的生酒做區分。"),
    ("原酒", ["原酒"], "釀好後沒有加水調整度數的酒。酒精度通常較高，味道比較飽滿直接。"),
    ("無濾過", ["無濾過", "無過濾", "無ろ過"], "沒有用活性碳過濾。保留較多的米香與色澤，風味比較厚。"),
    ("生酛", ["生酛", "きもと"], "傳統的酒母做法，利用自然的乳酸菌慢慢培養。風味通常更有層次，酸度也比較明顯。"),
    ("山廢", ["山廢", "山廃"], "生酛的簡化版本，省略了把米磨碎的「山卸」步驟，一樣靠自然乳酸菌，常見較濃的酸與旨味。"),
    ("雄町、山田錦這些名字", [], "是酒造好適米的品種。同一間酒造用不同的米，喝起來會很不一樣，這本圖鑑裡記錄最多的是山田錦。"),
]


def contour_labels():
    """70%、50%、20% 的標籤分散在米粒的左上、右側、下方，避免重疊。"""
    out = []
    for v, ang, anchor, dx, dy in ((70, -38, "end", -4, -2), (50, 62, "start", 5, 3), (20, 180, "middle", 0, 12)):
        rx, ry = grain_geom(v / 100, 58, 82)
        x = 96 + rx * math.sin(math.radians(ang)) + dx
        y = 110 - ry * math.cos(math.radians(ang)) + dy
        out.append(f'<text class="grain-tick" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">{v}%</text>')
    return "".join(out)


def build_guide(items, order):
    base = "../"
    tcount = Counter(i.get("sakeType") for i in items)
    by_type = defaultdict(list)
    for i in order:
        by_type[i.get("sakeType") or ""].append({"id": i["id"], "t": i["brand"] + ("　" + i["name"] if i["name"] != i["brand"] else "")})
    DEFS = {
        "純米大吟釀": "米磨到剩 50% 以下，只用米、米麴和水，以低溫慢慢發酵的吟釀製法釀成。香氣通常最華麗。",
        "大吟釀": "米磨到剩 50% 以下，用吟釀製法，另外添加少量釀造酒精，讓香氣更容易釋放、口感更輕快。",
        "純米吟釀": "米磨到剩 60% 以下，只用米、米麴和水的吟釀酒。果香與米味之間的平衡，是最常見的入門選擇。",
        "吟釀": "米磨到剩 60% 以下，用吟釀製法並添加少量釀造酒精。",
        "特別純米酒": "只用米、米麴和水，米磨到 60% 以下，或用了酒造另外說明的特別製法。",
        "特別本釀造": "添加少量釀造酒精，米磨到 60% 以下，或用了酒造另外說明的特別製法。",
        "純米酒": "只用米、米麴和水，沒有精米步合的門檻。米的味道最直接，溫熱來喝也常常很好。",
        "本釀造": "米磨到剩 70% 以下，添加少量釀造酒精。口感俐落，多半價格親切。",
    }
    cells = []
    for label, a, b in TYPE_MATRIX:
        def cell(t):
            if not t:
                return '<td class="is-na"></td>'
            return f'<td><button type="button" data-type="{esc(t)}" id="{esc(t)}" aria-controls="mx-panel"><span>{esc(t)}</span><b>{tcount.get(t, 0)} 款</b></button></td>'
        cells.append(f'<tr><th scope="row">{esc(label)}</th>{cell(a)}{cell(b)}</tr>')
    others = [t for t in tcount if t and t not in DEFS]
    other_note = "、".join(f"{t}（{tcount[t]}）" for t in others)
    gloss = []
    for term, keys, text in GLOSSARY:
        n = sum(1 for i in items if any(k in (i["name"] or "") + (i.get("brand") or "") for k in keys)) if keys else 0
        link = f'<a href="{base}sake/?q={esc(keys[0])}">圖鑑裡有 {n} 款{icon("arrow")}</a>' if keys and n else ""
        gloss.append(f"<div><dt>{esc(term)}</dt><dd><p>{esc(text)}</p>{link}</dd></div>")

    mx_data = {"defs": DEFS, "items": {k: v for k, v in by_type.items() if k in DEFS}}
    body = f'''
<article class="guide">
  <header class="guide-head">
    <h1>看懂酒標上的字</h1>
    <p>點酒或買酒時，酒標上最大的那幾個字，大多在回答兩件事：米磨掉了多少，以及有沒有另外加釀造酒精。下面用這本圖鑑實際記錄過的酒來對照。</p>
  </header>

  <section class="g-sec" aria-labelledby="mx-h">
    <h2 id="mx-h">八種特定名稱酒</h2>
    <p class="g-lead">表格裡的數字是這本圖鑑記錄過的款數。點一格，看看它的定義和喝過哪些。</p>
    <div class="mx">
      <table class="matrix is-big">
        <caption class="sr">特定名稱酒依精米步合與是否添加釀造酒精分類</caption>
        <thead><tr><th scope="col">精米步合</th><th scope="col">只用米、米麴、水</th><th scope="col">另加釀造酒精</th></tr></thead>
        <tbody>{"".join(cells)}</tbody>
      </table>
      <div class="mx-panel" id="mx-panel" aria-live="polite">
        <h3>從表格選一格</h3>
        <p>每一格會列出定義，以及圖鑑裡對應的酒款。</p>
      </div>
    </div>
    <p class="t-sub">不在表格裡的：{esc(other_note) if other_note else "無"}。另有 {tcount.get("", 0)} 款的酒種尚未記錄。</p>
    <script type="application/json" id="mx-data">{json.dumps(mx_data, ensure_ascii=False)}</script>
  </section>

  <section class="g-sec" aria-labelledby="gr-h">
    <h2 id="gr-h">精米步合：一粒米磨掉多少</h2>
    <p class="g-lead">米粒外層的蛋白質和脂肪會帶來雜味，磨得越多，留下的越接近中心的澱粉（心白）。精米步合 35%，代表磨掉了 65%。拖動看看。</p>
    <div class="polisher" data-polisher>
      <svg viewBox="0 0 220 220" aria-hidden="true">
        {GRAIN_DEFS}
        <ellipse class="grain-whole" cx="96" cy="110" rx="58" ry="82"/>
        {"".join(f'<ellipse class="grain-line" cx="96" cy="110" rx="{grain_geom(v / 100, 58, 82)[0]:.1f}" ry="{grain_geom(v / 100, 58, 82)[1]:.1f}"/>' for v in (70, 50, 20))}
        <ellipse class="grain-left" cx="96" cy="110" rx="58" ry="82" fill="url(#rg)"/>
        {contour_labels()}
      </svg>
      <div class="polisher-ui">
        <label for="pol">留下 <output id="pol-out">60</output>%</label>
        <input id="pol" type="range" min="1" max="100" step="1" value="60" aria-describedby="pol-say">
        <div class="pol-ticks" aria-hidden="true">{"".join(f'<span style="--x:{(v - 1) / 99:.4f}">{lab}<b>{v}</b></span>' for v, lab in ((70, "本釀造"), (60, "吟釀"), (50, "大吟釀"), (20, "")))}</div>
        <p class="polisher-say" id="pol-say">磨掉了 40%。60% 以下，可以標示為吟釀或純米吟釀。</p>
        <p class="polisher-dia" id="pol-dia"></p>
        <p class="polisher-col" id="pol-col"></p>
      </div>
      <script type="application/json" id="pol-data">{json.dumps(sorted([[i["polish"], i["id"], i["brand"] + ("　" + i["name"] if i["name"] != i["brand"] else "")] for i in items if i["polish"]]), ensure_ascii=False)}</script>
    </div>
  </section>

  <section class="g-sec" aria-labelledby="gl-h">
    <h2 id="gl-h">酒名裡常見的其他字</h2>
    <dl class="gloss">{"".join(gloss)}</dl>
  </section>
</article>
'''
    return page(title="看懂酒標上的字", desc="純米大吟釀、吟釀、本釀造差在哪裡？用實際喝過的酒款，對照特定名稱酒、精米步合與生酒、原酒、無濾過等用語。",
                depth=1, body=body, path="guide/", nav="guide", body_class="is-guide")


def build_about(items, prefs, meta):
    base = "../"
    about = load_about()
    nbrew = len({i.get("brewery") for i in items if i.get("brewery")})
    places = Counter(re.sub(r"\s*[（(].*?[)）]\s*", "", t.get("shop") or t.get("place") or "")
                     for i in items for t in i["tastings"] if (t.get("shop") or t.get("place")))
    top = "、".join(k for k, _ in places.most_common(3) if k)
    me = about.get("關於我", "")
    certs = certs_html(about)
    score = about.get("評分標準", "")
    contact = about.get("聯絡", "")
    if not contact and SITE["contact_email"]:
        contact = f"合作與品飲會洽詢：{SITE['contact_email']}"
    body = f'''
<article class="guide about">
  <header class="guide-head">
    <h1>關於這本圖鑑</h1>
    <p>SAKE ATLAS 是一本私人的清酒品飲帖。每一頁都是真的喝過的一款酒，依它來自日本的哪個縣整理在地圖上。</p>
  </header>
  {f'<section class="g-sec" id="me"><h2>關於我</h2>{md_html(me)}{f"<p class=me-certs>{certs}</p>" if certs else ""}</section>' if me else ""}
  {f'<section class="g-sec" id="score"><h2>評分標準</h2>{md_html(score)}</section>' if score else ""}
  <section class="g-sec">
    <h2>怎麼記錄</h2>
    <p>目前收錄 {len(items)} 款、{nbrew} 間酒造，橫跨 {sum(1 for p in prefs.values() if p["items"])} 個都道府縣，多數是在{esc(top)}等地喝到的。每一筆會記下品飲日期、是單杯還是整瓶、在哪裡喝，以及當下的心得與分數；規格則盡量對照酒造或進口商公開的資料。</p>
  </section>
  <section class="g-sec">
    <h2>不會在這裡出現的</h2>
    <p>這裡不賣酒，也不接受為了刊登而付費的推薦。評分不高的酒，一樣會留在圖鑑裡。</p>
  </section>
  {f'<section class="g-sec" id="contact"><h2>聯絡</h2>{md_html(contact)}</section>' if contact else ""}
  <p class="t-sub">資料更新：{esc(meta.get("updated", ""))}</p>
</article>
'''
    return page(title="關於這本圖鑑", desc="記錄者的介紹、評分標準，以及 SAKE ATLAS 如何記錄每一款清酒。", depth=1, body=body,
                path="about/", nav="about", body_class="is-about")


def build_404():
    b = site_base_path()
    body = f'''<article class="guide"><header class="guide-head"><h1>這一頁不在圖鑑裡</h1>
    <p>網址可能打錯了，或這款酒的頁面已經移動。可以回到<a href="{b}">首頁的地圖</a>，或從<a href="{b}sake/">全部酒款</a>重新找。</p></header></article>'''
    return page(title="找不到頁面", desc="找不到這一頁。", depth=0, body=body, path="404.html", base=b)


# ───────────────────────── 單檔預覽版 ─────────────────────────
ROUTER_JS = r"""
(() => {
  const P = JSON.parse(document.getElementById("sa-pages").textContent);
  const IMG = JSON.parse(document.getElementById("sa-img").textContent);
  window.SA_ASSET = (p) => {
    const m = String(p).match(/assets\/(images|scenes)\/([\w-]+?)(?:-640)?\.webp$/);
    return (m && IMG[m[1] + "/" + m[2]]) || p;
  };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const main = document.getElementById("main");
  const ORIGIN = "https://preview.local";
  let first = true;
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";

  const parse = () => {
    const raw = location.hash.slice(1) || "/";
    const i = raw.indexOf("?");
    return i < 0 ? [raw, ""] : [raw.slice(0, i), raw.slice(i)];
  };
  const norm = (p) => (p.endsWith("/") ? p : p + "/");
  const short = (t) => (t.startsWith("SAKE ATLAS") ? "首頁" : t.replace(/｜SAKE ATLAS.*$/, ""));
  const st = () => history.state || { i: 0, y: 0, from: "" };

  const render = (path, search, frag, mode, y) => {
    path = norm(path);
    if (!P[path]) { path = "/"; search = ""; }
    const pg = P[path];
    if (mode === "push") {
      history.replaceState({ ...st(), y: scrollY }, "");
      history.pushState({ i: st().i + 1, y: 0, from: short(document.title) }, "", "#" + path + search);
    }
    const swap = () => {
      SA.path = path; SA.q = search; SA.frag = frag || "";
      main.innerHTML = pg.b;
      document.title = pg.t;
      document.body.className = pg.c;
      document.querySelectorAll(".top-nav a").forEach((a) =>
        a.dataset.nav === pg.n ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
      main.querySelectorAll("img[data-k]").forEach((img) => { img.src = IMG[img.dataset.k] || ""; });
      window.SA_INIT && window.SA_INIT();
      const el = SA.frag && document.getElementById(SA.frag);
      if (el) el.scrollIntoView();
      else if (mode === "pop") window.scrollTo(0, y || 0);
      else if (!first) window.scrollTo(0, 0);
      first = false;
    };
    if (!first && document.startViewTransition && !reduce.matches) document.startViewTransition(swap);
    else swap();
  };

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
    const href = a.getAttribute("href");
    if (/^(https?:|mailto:|tel:)/.test(href)) return;
    e.preventDefault();
    const u = new URL(href, ORIGIN + SA.path);
    const frag = decodeURIComponent(u.hash.slice(1));
    if (norm(u.pathname) === SA.path && !u.search && frag) {
      document.getElementById(frag)?.scrollIntoView({ behavior: reduce.matches ? "auto" : "smooth" });
      return;
    }
    render(u.pathname, u.search, frag, "push");
  });
  document.addEventListener("submit", (e) => {
    const f = e.target;
    if (f.id === "filters") return;
    e.preventDefault();
    const u = new URL(f.getAttribute("action") || "./", ORIGIN + SA.path);
    const qs = new URLSearchParams(new FormData(f)).toString();
    render(u.pathname, qs ? "?" + qs : "", "", "push");
  });
  addEventListener("popstate", (e) => {
    const [p, q] = parse();
    render(p, q, "", "pop", (e.state && e.state.y) || 0);
  });
  if (!history.state) history.replaceState({ i: 0, y: 0, from: "" }, "");
  const [p, q] = parse();
  render(p, q, "", "init");
})();
"""


def data_uri(path, mime):
    import base64
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def build_preview(out_path):
    css = (STATIC / "site.css").read_text("utf-8")
    css = css.replace('url("map-backdrop.webp")', f'url("{data_uri(STATIC / "map-backdrop.webp", "image/webp")}")')
    css = css.replace('url("seal-grain.png")', f'url("{data_uri(STATIC / "seal-grain.png", "image/png")}")')
    for name, mime in (("hosho-light.webp", "image/webp"), ("hosho-dark.webp", "image/webp"), ("kinpaku.webp", "image/webp"), ("label-edge.png", "image/png")):
        css = css.replace(f'url("{name}")', f'url("{data_uri(STATIC / name, mime)}")')
    js = (STATIC / "site.js").read_text("utf-8")
    imgs = {}
    try:
        from PIL import Image as _Im
        import base64 as _b64, io as _io
    except ImportError:
        _Im = None
    for src in (STATIC / "images").glob("*.webp"):
        if _Im:   # 預覽版用較小的照片，讓單一檔案維持在可分享的大小
            im = _Im.open(src).convert("RGB")
            im.thumbnail((420, 560))
            buf = _io.BytesIO()
            im.save(buf, "WEBP", quality=66, method=6)
            imgs["images/" + src.stem] = "data:image/webp;base64," + _b64.b64encode(buf.getvalue()).decode()
        else:
            small = DIST / "assets" / "images" / f"{src.stem}-640.webp"
            imgs["images/" + src.stem] = data_uri(small if small.exists() else src, "image/webp")
    for src in (STATIC / "scenes").glob("*.webp"):
        imgs["scenes/" + src.stem] = data_uri(src, "image/webp")

    def strip_imgs(h):
        h = re.sub(r'src="[^"]*assets/(images|scenes)/([\w-]+?)(?:-640)?\.webp"', r'data-k="\1/\2"', h)
        h = re.sub(r' srcset="[^"]*"', "", h)
        return re.sub(r' sizes="[^"]*"', "", h)

    pages = {k: dict(v, b=strip_imgs(v["b"])) for k, v in PAGES.items()}
    pages_json = json.dumps(pages, ensure_ascii=False).replace("</", "<\\/")
    img_json = json.dumps(imgs)
    favicon = "data:image/svg+xml," + (STATIC / "favicon.svg").read_text("utf-8").replace("#", "%23").replace("\n", "")
    html_out = f'''<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{SITE["name"]}｜{SITE["tagline"]}（預覽）</title>
<meta name="color-scheme" content="light only">
<link rel="icon" href="{esc(favicon)}">
{FONTS}
<style>{css}</style>
</head>
<body>
{header_html("/", "")}
<main id="main"></main>
{footer_html("/")}
<script type="application/json" id="sa-pages">{pages_json}</script>
<script type="application/json" id="sa-img">{img_json}</script>
<script>
window.SA = {{ path: "/", q: "", frag: "" }};
window.SA_NAV = {{
  search: () => SA.q,
  fragment: () => SA.frag,
  replace: (qs) => {{ SA.q = qs ? "?" + qs : ""; history.replaceState(history.state, "", "#" + SA.path + SA.q); }},
  canBack: () => !!(history.state && history.state.i > 0),
  prevLabel: () => (history.state && history.state.i > 0 && history.state.from) || "",
}};
</script>
<script>{js}</script>
<script>{ROUTER_JS}</script>
</body>
</html>
'''
    out_path.write_text(html_out, "utf-8")
    return out_path.stat().st_size


# ───────────────────────── 照片收件匣 ─────────────────────────
# 把照片丟進 photos/，檔名用酒款 ID（S0031.jpg）或酒名（產土-神宴一農.jpg）都可以。
# 建置時會自動對應、保留原始比例縮小（不裁切）、轉成網頁格式，存到 static/images/。對不上的會列在 photo-report.txt。
PHOTO_IN = ROOT / "photos"
FORCE_PHOTOS = bool(os.environ.get("GITHUB_ACTIONS"))   # GitHub 上檔案時間都一樣，收件匣裡的照片一律重做
CONSUMED = []
_VARIANT = str.maketrans({"歳": "歲", "亀": "龜", "黒": "黑", "醸": "釀", "桜": "櫻", "沢": "澤", "万": "萬", "鶴": "鶴",
                          "国": "國", "広": "廣", "徳": "德", "静": "靜", "辺": "邊", "竜": "龍"})


def _norm(t):
    t = re.sub(r"\.(jpe?g|png|webp|heic)$", "", t, flags=re.I).translate(_VARIANT)
    return re.sub(r"[\s\-_「」『』・,，.。()（）]", "", t).lower()


def _jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(1, len(a | b))


def match_photo(stem, items):
    """回傳 (酒款 ID 或 None, 說明)。"""
    if re.fullmatch(r"[Ss]\d{4}", stem):
        sid = stem.upper()
        return (sid, "ID") if any(i["id"] == sid for i in items) else (None, "找不到這個 ID")
    f = _norm(stem)
    scored = []
    for i in items:
        b, n = _norm(i["brand"]), _norm(i["name"])
        if b and b in f:
            rest = f.replace(b, "", 1)
            score = 1 + (_jac(rest, n) if rest else 0.5)
            ok = (not rest) or _jac(rest, n) >= 0.3 or rest in n
        else:
            score = _jac(f, b + n)
            ok = score >= 0.4
        scored.append((score, ok, i["id"]))
    scored.sort(reverse=True)
    best, second = scored[0], (scored[1] if len(scored) > 1 else (0, False, ""))
    if not best[1]:
        return None, "對不上任何酒款"
    if best[0] - second[0] < 0.08:
        return None, f"不確定是 {best[2]} 還是 {second[2]}"
    return best[2], "依酒名"


def process_photos(items):
    if not PHOTO_IN.exists():
        return
    files = [p for p in sorted(PHOTO_IN.iterdir()) if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".heic")]
    if not files:
        return
    try:
        from PIL import Image
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
    except ImportError:
        print("（未安裝 Pillow，photos/ 裡的照片沒有處理：pip install pillow）")
        return
    by_id = {i["id"]: i for i in items}
    out_dir = STATIC / "images"
    wanted = {}
    for i in items:
        for t in i["tastings"]:
            for k, f in enumerate(t.get("photos") or []):
                wanted[f.lower()] = (t, k)
    tasting_files = [p for p in files if p.name.lower() in wanted]
    files = [p for p in files if p.name.lower() not in wanted]

    # 以品飲編號命名的照片（T00025.jpg）：存成 static/images/t-T00025.webp。
    # 哪一張當封面在建置時決定（attach_tasting_photos），所以之後補照片不會蓋掉舊的。
    # 同一次品飲有多張：T00051.jpg、T00051-2.jpg（或 T00051_2、T00051 (2)）
    by_tid = {t["id"]: (i, t) for i in items for t in i["tastings"] if t.get("id")}
    TID_RE = re.compile(r"^(T\d{5})(?:\s*[-_ ]\s*\(?(\d{1,2})\)?|\s*\((\d{1,2})\))?$", re.I)

    def _tid(p):
        m = TID_RE.match(p.stem.strip())
        if m and m.group(1).upper() in by_tid:
            return m.group(1).upper(), int(m.group(2) or m.group(3) or 1)
        return None

    tid_files = [p for p in files if _tid(p)]
    files = [p for p in files if not _tid(p)]
    out_dir.mkdir(parents=True, exist_ok=True)

    def _save(src, out):
        if FORCE_PHOTOS or not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            im = Image.open(src).convert("RGB")
            im.thumbnail((1080, 1920), Image.LANCZOS)   # 只縮小、不裁切，保留原始構圖
            im.save(out, "WEBP", quality=80, method=6)

    tid_report, taken = [], set()
    for src in sorted(tid_files, key=lambda p: (_tid(p), p.suffix.lower() != ".jpg", p.name)):
        tid, n = _tid(src)
        while (tid, n) in taken:          # 同名不同副檔名（T00051.jpg 與 T00051.png）就往後排
            n += 1
        taken.add((tid, n))
        it, t = by_tid[tid]
        name = f"t-{tid}.webp" if n == 1 else f"t-{tid}-{n}.webp"
        _save(src, out_dir / name)
        CONSUMED.append(src)
        tid_report.append(f"✓ {src.name} → {it['id']} {it['brand']} {it['name']}（品飲 {tid}" + ("" if n == 1 else f" 第 {n} 張") + "）")

    # 試算表「品飲照片」欄指定的檔名
    for src in tasting_files:
        t, k = wanted[src.name.lower()]
        name = f"t-{t['id']}-{k + 1}.webp"
        _save(src, out_dir / name)
        CONSUMED.append(src)
        t["photos"][k] = name
        tid_report.append(f"✓ {src.name} → 品飲紀錄 {t['id']}")
    report, used = tid_report, {}
    for src in files:
        stem = re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), src.stem)   # zip 轉碼的中文檔名
        sid, why = match_photo(stem, items)
        if not sid:
            report.append(f"✗ {src.name}：{why}")
            continue
        if sid in used:
            report.append(f"✗ {src.name}：和 {used[sid]} 都對到 {sid}，請改檔名")
            continue
        used[sid] = src.name
        out = out_dir / f"{sid}.webp"
        stale = FORCE_PHOTOS or not out.exists() or out.stat().st_mtime < src.stat().st_mtime
        if not stale:   # 以前裁成 3:4 的版本：比例和原圖不同就重做
            try:
                with Image.open(src) as a, Image.open(out) as b:
                    stale = abs(a.size[0] / a.size[1] - b.size[0] / b.size[1]) > 0.01
            except Exception:
                pass
        if stale:
            try:
                im = Image.open(src).convert("RGB")
            except Exception as e:
                report.append(f"✗ {src.name}：無法讀取（{e.__class__.__name__}）")
                continue
            im.thumbnail((1080, 1920), Image.LANCZOS)   # 只縮小、不裁切，保留原始構圖
            im.save(out, "WEBP", quality=80, method=6)
        by_id[sid]["photo"] = out.name
        CONSUMED.append(src)
        it = by_id[sid]
        report.append(f"✓ {src.name} → {sid} {it['brand']} {it['name']}")
    (ROOT / "photo-report.txt").write_text("\n".join(report) + "\n", "utf-8")
    ok = sum(1 for r in report if r.startswith("✓"))
    total = len(files) + len(tid_files)
    print(f"照片：photos/ 裡 {total} 張，對上 {ok} 張" + (f"，{total - ok} 張沒對上（見 photo-report.txt）" if ok < total else ""))


def attach_tasting_photos(items):
    """static/images/t-T00025.webp → 那次品飲所屬的酒。最近一次有照片的品飲當封面，其他次放進該次品飲紀錄。"""
    img = STATIC / "images"

    def _date_key(t):
        nums = [int(x) for x in re.findall(r"\d+", _txt(t.get("date")))]
        return tuple(nums + [0, 0, 0])[:3]

    def _shots(tid):
        first = [f"t-{tid}.webp"] if (img / f"t-{tid}.webp").exists() else []
        more = sorted((p.name for p in img.glob(f"t-{tid}-*.webp") if re.fullmatch(rf"t-{tid}-\d+\.webp", p.name)),
                      key=lambda n: int(re.search(r"-(\d+)\.webp$", n).group(1)))
        return first + more

    for it in items:
        have = [(t, _shots(t["id"])) for t in it["tastings"] if t.get("id")]
        have = [(t, sh) for t, sh in have if sh]
        if not have:
            continue
        have.sort(key=lambda x: (_date_key(x[0]), x[0]["id"]), reverse=True)
        cover_t, cover_sh = have[0]
        it["photo"] = cover_sh[0]
        # 酒款頁大圖可以左右滑：每一次品飲的照片各一張（最近一次在最前面）
        it["slides"] = [(t["id"], f) for t, sh in have for f in sh]
        for t, sh in have:
            rest = sh[1:] if t is cover_t else sh       # 封面那張不在品飲紀錄裡重複
            if rest:
                t["photos"] = rest + [f for f in (t.get("photos") or []) if f not in rest]


def consume_photos():
    """GitHub 上建置時：處理好的原始照片從 photos/ 移除（已轉成網頁版存在 static/images/）。"""
    for src in CONSUMED:
        try:
            src.unlink()
        except FileNotFoundError:
            pass
    if CONSUMED:
        print(f"photos/：{len(CONSUMED)} 張已處理，原檔移除")


# ───────────────────────── 主程式 ─────────────────────────
def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


def make_images(dist_img):
    try:
        from PIL import Image
    except ImportError:
        print("（未安裝 Pillow，略過縮圖，網站仍可正常使用）")
        return
    for src in (STATIC / "images").glob("*.*"):
        if src.suffix.lower() not in (".webp", ".jpg", ".jpeg", ".png") or src.stem.endswith("-640"):
            continue
        out = dist_img / f"{src.stem}-640.webp"
        if not out.exists():
            im = Image.open(src).convert("RGB")
            w, h = im.size
            im.resize((640, round(h * 640 / w)), Image.LANCZOS).save(out, "WEBP", quality=78, method=6)
        HAS_SMALL[src.stem] = True


def main():
    items, order, prefs, meta, geo = load()
    process_photos(items)
    attach_tasting_photos(items)
    if os.environ.get("SA_CONSUME_PHOTOS"):
        consume_photos()
    if DIST.exists():
        shutil.rmtree(DIST)
    assets = DIST / "assets"
    (assets / "images").mkdir(parents=True)
    for f in STATIC.glob("*"):
        if f.is_file():
            shutil.copy2(f, assets / f.name)
    for f in (STATIC / "images").glob("*"):
        shutil.copy2(f, assets / "images" / f.name)
    if (STATIC / "scenes").exists():
        shutil.copytree(STATIC / "scenes", assets / "scenes")
    make_images(assets / "images")

    write(DIST / "index.html", build_home(items, order, prefs, meta))
    write(DIST / "sake" / "index.html", build_explore(items, order, prefs))
    for it in items:
        write(DIST / "sake" / it["id"] / "index.html", build_sake(it, items, order))
    for p in prefs.values():
        if p["items"]:
            write(DIST / "pref" / p["slug"] / "index.html", build_pref(p, prefs, items))
    write(DIST / "guide" / "index.html", build_guide(items, order))
    write(DIST / "about" / "index.html", build_about(items, prefs, meta))
    write(DIST / "404.html", build_404())

    urls = ["", "sake/", "guide/", "about/"] + [f"sake/{i['id']}/" for i in items] + [f"pref/{p['slug']}/" for p in prefs.values() if p["items"]]
    if SITE["url"]:
        sm = "".join(f"<url><loc>{esc(abs_url(u))}</loc></url>" for u in urls)
        write(DIST / "sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
        write(DIST / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {abs_url('sitemap.xml')}\n")
    else:
        write(DIST / "robots.txt", "User-agent: *\nAllow: /\n")
    size = build_preview(ROOT / "preview.html")
    print(f"單檔預覽：preview.html（{size / 1e6:.1f} MB，可直接用瀏覽器開啟）")
    n_pages = len(list(DIST.rglob("*.html")))
    print(f"完成：{len(items)} 款酒、{sum(1 for p in prefs.values() if p['items'])} 個縣，共 {n_pages} 個頁面，輸出到 {DIST}")


if __name__ == "__main__":
    main()
