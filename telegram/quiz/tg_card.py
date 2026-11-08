#!/usr/bin/env python3
"""GKS Academics — Telegram kartochkalari (1080x1350 dizayn, 2x PNG = 2160x2700).

Foydalanish (repo ichida, eng oddiy yo'l):
    python3 telegram/quiz/tg_card.py spec.json OUT_DIR
  Shriftlar (fonts/), logo (assets/logo_dark.b64) va brand.json repodan olinadi; Hangul uchun
  Pretendard birinchi ishga tushishda `npm pack pretendard@1.3.9` bilan ~/.cache/gks-tg ga yuklanadi.
Yoki tayyor papka bilan:
    python3 tg_card.py spec.json OUT_DIR ASSETS_DIR
  ASSETS_DIR ichida: Sora.ttf, Manrope.ttf, logo_dark.b64, brand.json, PretendardVariable.ttf

spec.json:
    {"cards": [{"file": "01_post.png", "theme": "navy" | "paper", "badge": "Quiz · 01",
                "blocks": [{"type": "rule"}, {"type": "kicker", "text": "..."}, ...]}]}

Bloklar (matnda *so'z* — urg'u: to'q fonda oltin, och fonda qalin; matndagi yangi qator saqlanadi):
    rule                            oltin chiziq (64x6)
    kicker   text                   kichik, BOSH HARFLI sarlavha
    lead     text                   o'rta kattalikdagi xira matn
    title    text  [size=112]       katta sarlavha (Sora ExtraBold)
    subtitle text  [size=60]        o'rta sarlavha (Sora ExtraBold)
    hangul   text  [size=140]       katta koreyscha yozuv; "[]" — bo'sh katak (savol uchun)
    roman    text                   transliteratsiya / ma'no (xira)
    text     text  [size=36]        oddiy matn
    rows     items=[[chap, o'ng], ...] [left=290]  ikki ustunli ro'yxat (chapda odatda koreyscha)
    options  items=[...] [correct=i] A/B/C/D variantlar; correct berilsa oltin bilan belgilanadi
    tip      label, text            ramkali blok (masalan "GKS maslahati")
    cta      text                   pastki chaqiriq; strelkani *↓* deb yozing
    space    h                      bo'sh joy (px)
Har blokka "gap" (px) berib, undan oldingi bo'shliqni o'zgartirish mumkin.
Brend: faqat navy #0F1E3A / paper #F2F3EF / gold #C9A34E va ularning aralashmalari.
Sig'may qolsa "OGOHLANTIRISH" chiqadi va kod 2 bilan tugaydi — matnni qisqartiring.
"""
import base64
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

W, H, M = 1080, 1350, 96
NAVY, PAPER, GOLD = "#0F1E3A", "#F2F3EF", "#C9A34E"

GAP = {"rule": 0, "kicker": 40, "lead": 30, "title": 20, "subtitle": 26, "hangul": 24,
       "roman": 10, "text": 26, "rows": 40, "options": 34, "tip": 44, "cta": 48, "space": 0}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def uz(text):
    """O'zbekcha apostroflar: o‘ g‘ (U+2018) va tutuq belgisi ’ (U+2019)."""
    text = (text or "").replace("ʻ", "‘").replace("ʼ", "’").replace("`", "‘")
    text = re.sub("([OoGg])'", lambda m: m.group(1) + "‘", text)
    return text.replace("'", "’")


def rich(text):
    t = html.escape(uz(text), quote=False)
    t = re.sub("[*](.+?)[*]", lambda m: '<span class="acc">' + m.group(1) + "</span>", t)
    return "<br>".join(t.splitlines())


def logo_mask(assets):
    raw = base64.b64decode("".join((assets / "logo_dark.b64").read_text().split()))
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    alpha = im.getchannel("A")
    im = im.crop(alpha.getbbox())
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(im.getchannel("A"))
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode(), im.size


CSS = """
@font-face{font-family:"Sora";src:url("Sora.ttf");font-weight:100 800}
@font-face{font-family:"Manrope";src:url("Manrope.ttf");font-weight:200 800}
@font-face{font-family:"Pretendard";src:url("PretendardVariable.ttf");font-weight:45 920}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--bg)}
.card{position:relative;width:1080px;height:1350px;background:var(--bg);color:var(--fg);
 font-family:"Manrope","Pretendard",sans-serif;-webkit-font-smoothing:antialiased;
 text-rendering:geometricPrecision;word-break:keep-all;overflow-wrap:normal}
.navy{--bg:%(NAVY)s;--fg:%(PAPER)s;--muted:%(n_muted)s;--muted2:%(n_muted2)s;--body:%(n_body)s;
 --line:%(n_line)s;--foot:%(n_foot)s;--acc:%(GOLD)s;--box:%(n_box)s}
.paper{--bg:%(PAPER)s;--fg:%(NAVY)s;--muted:%(p_muted)s;--muted2:%(p_muted2)s;--body:%(p_body)s;
 --line:%(p_line)s;--foot:%(p_foot)s;--acc:%(NAVY)s;--box:%(NAVY)s}
.header{position:absolute;left:96px;right:96px;top:74px;height:68px;display:flex;align-items:center}
.logo{height:68px;flex:none;background:var(--fg);-webkit-mask:var(--logo) center/contain no-repeat;
 mask:var(--logo) center/contain no-repeat}
.wordmark{margin-left:20px;font:800 24px/1 "Manrope";letter-spacing:4px;color:var(--fg)}
.badge{margin-left:auto;font:600 24px/1 "Manrope","Pretendard";color:var(--muted2)}
.content{position:absolute;left:96px;right:96px;top:210px;bottom:190px;display:flex;flex-direction:column}
.sp1{flex:42 1 0}.sp2{flex:58 1 0}
.stack{flex:none}
.footer{position:absolute;left:96px;right:96px;top:1209px;border-top:2px solid var(--line);padding-top:28px;
 display:flex;justify-content:space-between;font:600 24px/1 "Manrope";color:var(--foot)}
.rule{width:64px;height:6px;background:%(GOLD)s}
.kicker{font:700 30px/1.2 "Manrope","Pretendard";color:var(--muted);text-transform:uppercase;letter-spacing:.01em}
.lead{font:600 38px/1.35 "Manrope","Pretendard";color:var(--muted)}
.title{font:800 112px/1.04 "Sora","Pretendard";letter-spacing:-.01em;color:var(--fg)}
.subtitle{font:800 60px/1.14 "Sora","Pretendard";letter-spacing:-.005em;color:var(--fg)}
.hangul{font:800 140px/1.14 "Pretendard";letter-spacing:-.02em;color:var(--fg);white-space:nowrap}
.hangul .blank{display:inline-block;position:relative;width:.88em;height:.88em;border:.035em solid %(GOLD)s;
 border-radius:.16em;vertical-align:-.1em;margin-right:.07em}
.hangul .blank i{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
 font:800 .4em/1 "Sora";font-style:normal;color:%(GOLD)s}
.roman{font:600 34px/1.35 "Manrope","Pretendard";color:var(--muted)}
.text{font:500 36px/1.5 "Manrope","Pretendard";color:var(--body)}
.rows .row{display:grid;grid-template-columns:var(--left,290px) 1fr;column-gap:32px;align-items:center;
 padding:20px 0;border-top:2px solid var(--line)}
.rows .row:last-child{border-bottom:2px solid var(--line)}
.rows .ko{font:700 38px/1.2 "Pretendard";color:var(--fg);white-space:nowrap}
.rows .uz{font:600 28px/1.42 "Manrope","Pretendard";color:var(--body)}
.options .opt{display:flex;align-items:center;gap:24px;padding:16px 0}
.options .letter{flex:none;width:56px;height:56px;border-radius:50%%;border:2px solid var(--line);display:flex;
 align-items:center;justify-content:center;font:800 26px/1 "Manrope";color:var(--muted)}
.options .otext{font:600 34px/1.3 "Manrope","Pretendard";color:var(--fg)}
.options .ok .letter{background:%(GOLD)s;border-color:%(GOLD)s;color:%(NAVY)s}
.tip{background:var(--box);border-radius:24px;padding:34px 40px}
.tip .label{font:800 22px/1 "Manrope","Pretendard";letter-spacing:3px;text-transform:uppercase;color:%(GOLD)s;margin-bottom:16px}
.tip .ttext{font:600 30px/1.42 "Manrope","Pretendard";color:%(PAPER)s}
.cta{font:700 34px/1.35 "Manrope","Pretendard";color:var(--fg)}
.acc{color:var(--acc)}
.paper .acc{font-weight:800}
.navy .tip .acc,.paper .tip .acc{color:%(GOLD)s}
""" % {
    "NAVY": NAVY, "PAPER": PAPER, "GOLD": GOLD,
    "n_muted": mix(PAPER, NAVY, .35), "n_muted2": mix(PAPER, NAVY, .45), "n_body": mix(PAPER, NAVY, .18),
    "n_line": mix(PAPER, NAVY, .78), "n_foot": mix(PAPER, NAVY, .20), "n_box": mix(NAVY, PAPER, .07),
    "p_muted": mix(NAVY, PAPER, .42), "p_muted2": mix(NAVY, PAPER, .45), "p_body": mix(NAVY, PAPER, .16),
    "p_line": mix(NAVY, PAPER, .85), "p_foot": mix(NAVY, PAPER, .15),
}

FIT_JS = """async () => {
  const faces = [['800 20px Sora', 'Aa'], ['600 20px Manrope', 'Aa'], ['800 20px Pretendard', '가']];
  await Promise.all(faces.map(([f, s]) => document.fonts.load(f, s)));
  await document.fonts.ready;
  const res = {warnings: [], fonts: {}};
  for (const [f, s] of faces) res.fonts[f] = document.fonts.check(f, s);
  for (const el of document.querySelectorAll('.fit')) {
    let size = parseFloat(getComputedStyle(el).fontSize);
    const min = size * 0.55;
    while (el.scrollWidth > el.clientWidth + 1 && size > min) { size -= 2; el.style.fontSize = size + 'px'; }
    if (el.scrollWidth > el.clientWidth + 1) res.warnings.push("eniga sig'madi: " + el.textContent.slice(0, 40));
  }
  const box = document.querySelector('.content'), stack = document.querySelector('.stack');
  res.stack = stack.offsetHeight; res.room = box.clientHeight;
  if (stack.offsetHeight > box.clientHeight) res.warnings.push("bo'yiga sig'madi: " + stack.offsetHeight + "px > " + box.clientHeight + "px");
  const right = box.getBoundingClientRect().right + 1;
  for (const el of stack.querySelectorAll('*')) {
    if (el.getBoundingClientRect().right > right) { res.warnings.push("o'ngdan chiqib ketdi: " + (el.textContent || "").slice(0, 40)); break; }
  }
  return res;
}"""


def block_html(b, first):
    t = b["type"]
    gap = b.get("gap", 0 if first else GAP.get(t, 24))
    st = f"margin-top:{gap}px;"
    if "size" in b:
        st += f"font-size:{b['size']}px;"
    if t == "rule":
        return f'<div class="rule" style="{st}"></div>'
    if t == "space":
        return f'<div style="height:{b.get("h", 40)}px"></div>'
    if t in ("kicker", "lead", "roman", "text", "cta"):
        return f'<div class="{t}" style="{st}">{rich(b["text"])}</div>'
    if t in ("title", "subtitle"):
        return f'<div class="{t} fit" style="{st}">{rich(b["text"])}</div>'
    if t == "hangul":
        inner = rich(b["text"]).replace("[]", '<span class="blank"><i>?</i></span>')
        if b.get("gold"):
            st += f"color:{GOLD};"
        return f'<div class="hangul fit" style="{st}">{inner}</div>'
    if t == "rows":
        left = b.get("left", 290)
        rows = "".join(f'<div class="row"><div class="ko fit">{rich(a)}</div><div class="uz">{rich(c)}</div></div>'
                       for a, c in b["items"])
        return f'<div class="rows" style="{st}--left:{left}px">{rows}</div>'
    if t == "options":
        out = []
        for i, o in enumerate(b["items"]):
            ok = " ok" if b.get("correct") == i else ""
            out.append(f'<div class="opt{ok}"><div class="letter">{"ABCDEFGHIJKL"[i]}</div>'
                       f'<div class="otext">{rich(o)}</div></div>')
        return f'<div class="options" style="{st}">{"".join(out)}</div>'
    if t == "tip":
        label = f'<div class="label">{rich(b["label"])}</div>' if b.get("label") else ""
        return f'<div class="tip" style="{st}">{label}<div class="ttext">{rich(b["text"])}</div></div>'
    raise ValueError(f"Noma'lum blok turi: {t}")


def card_html(card, logo_b64, logo_w, brand):
    theme = card.get("theme", "navy")
    blocks = "".join(block_html(b, i == 0) for i, b in enumerate(card["blocks"]))
    badge = f'<div class="badge">{rich(card["badge"])}</div>' if card.get("badge") else ""
    vals = [brand.get(k) for k in ("telegram", "website") if brand.get(k)] or ["t.me/gks_academic"]
    foot = "".join(f"<div>{html.escape(v)}</div>" for v in vals)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body class="{theme}"><div class="card {theme}" style="--logo:url(data:image/png;base64,{logo_b64})">
<div class="header"><div class="logo" style="width:{logo_w}px"></div>
<div class="wordmark">{html.escape(brand.get("wordmark", "GKS ACADEMICS"))}</div>{badge}</div>
<div class="content"><div class="sp1"></div><div class="stack">{blocks}</div><div class="sp2"></div></div>
<div class="footer">{foot}</div></div></body></html>"""


def repo_assets():
    """Repo tuzilmasidan (fonts/, assets/, brand.json) va Pretendard keshidan assets papkasini yig'adi."""
    root = Path(__file__).resolve().parents[2]
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "gks-tg"
    cache.mkdir(parents=True, exist_ok=True)
    pret = cache / "PretendardVariable.ttf"
    if not pret.exists():
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["npm", "pack", "pretendard@1.3.9", "--silent"], cwd=td, check=True,
                           capture_output=True)
            tgz = next(Path(td).glob("pretendard-*.tgz"))
            with tarfile.open(tgz) as tf:
                src = tf.extractfile("package/dist/public/variable/PretendardVariable.ttf")
                pret.write_bytes(src.read())
    assets = cache / "assets"
    assets.mkdir(exist_ok=True)
    for src, name in ((root / "fonts" / "Sora.ttf", "Sora.ttf"), (root / "fonts" / "Manrope.ttf", "Manrope.ttf"),
                      (root / "assets" / "logo_dark.b64", "logo_dark.b64"), (root / "brand.json", "brand.json"),
                      (pret, "PretendardVariable.ttf")):
        shutil.copyfile(src, assets / name)
    return assets


def main():
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        return 1
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    assets = Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else repo_assets()
    brand = json.loads((assets / "brand.json").read_text(encoding="utf-8")) if (assets / "brand.json").exists() else {}
    logo_b64, (lw, lh) = logo_mask(assets)
    logo_w = round(68 * lw / lh)
    status = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for card in spec["cards"]:
            tmp = assets / "_card.html"
            tmp.write_text(card_html(card, logo_b64, logo_w, brand), encoding="utf-8")
            page.goto(tmp.as_uri())
            res = page.evaluate(FIT_JS)
            dst = out / card["file"]
            page.screenshot(path=str(dst))
            missing = [f for f, ok in res["fonts"].items() if not ok]
            print(f"{dst.name}: matn bloki {res['stack']}px / {res['room']}px"
                  + (f" | shrift yuklanmadi: {missing}" if missing else ""))
            for w in res["warnings"]:
                print(f"  OGOHLANTIRISH: {w}")
                status = 2
            if missing:
                status = 2
        browser.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
