#!/usr/bin/env python3
"""GKS Academics — yuzsiz (matnli) Reels videolarini yasaydi.

Foydalanish:
    python3 reels/reel.py reels/batch.json --out OUT_DIR [--only R01,R02] [--sheet] [--sheet-only]

--sheet       har video uchun SANA_ID_sheet.png ham yasaydi (har sahnadan bitta kadr — tekshirish uchun)
--sheet-only  faqat sheet.png yasaydi, video yasamaydi (tez tekshiruv)

Natija (OUT_DIR ichida):
    SANA_ID.mp4        1080x1920, 30 fps, H.264 + jim audio (musiqani Instagram'da qo'shasiz)
    SANA_ID_cover.jpg  muqova (birinchi sahna)
    captions.txt       barcha izohlar (caption) ketma-ket

batch.json:
{
  "reels": [
    {
      "id": "R01", "date": "2026-10-11", "theme": "navy" | "sky" | "paper",
      "watermark": "장학금",                      # ixtiyoriy, fondagi xira koreyscha so'z
      "scenes": [
        {"type": "hook",   "kicker": "GKS-U 2027", "text": "Sarlavha, *urg'u*", "sub": "ixtiyoriy", "dur": 2.4},
        {"type": "number", "kicker": "...", "value": 1200000, "unit": "₩", "label": "...", "note": "...", "dur": 3.2},
        {"type": "list",   "title": "...", "items": ["...", "..."], "dur": 4.5},
        {"type": "text",   "kicker": "...", "title": "...", "body": "...", "big": false, "dur": 2.8},
        {"type": "steps",  "title": "...", "items": [["16-oktabr", "voqea"], ["...", "..."]], "dur": 5},
        {"type": "end",    "title": "Obuna bo'ling", "sub": "...", "button": "Do'stingizga yuboring ↗", "dur": 2.6}
      ],
      "caption": "Instagram izohi"
    }
  ]
}
Matnda *so'z* — urg'u rangi (to'q fonda oltin, och fonda ko'k) va chizilib chiqadigan chiziq.
Talablar: python playwright (chromium), ffmpeg.
"""
import argparse
import base64
import html as htmlmod
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "brand.json").read_text(encoding="utf-8"))
W, H, FPS = 1080, 1920, 30
HANDLE = BRAND.get("instagram", "@gks_academics")


def uz(text):
    """O'zbekcha apostroflar: o‘ g‘ va ’ (render.py dagi qoida bilan bir xil)."""
    if not text:
        return ""
    text = text.replace("\u02bb", "\u2018").replace("\u02bc", "\u2019").replace("`", "\u2018")
    text = re.sub(r"([OoGg])'", "\\1\u2018", text)
    return text.replace("'", "\u2019")


UNDERLINE = ('<svg viewBox="0 0 300 26" preserveAspectRatio="none"><path d="M4 17 C 60 9, 120 8, 170 12 '
             'S 260 19, 296 10"/></svg>')


def md(text):
    """Matn -> HTML: *urg'u* -> <span class=acc>, \\n -> <br>."""
    out = []
    for i, part in enumerate(re.split(r"\*([^*]+)\*", uz(text or ""))):
        esc = htmlmod.escape(part).replace("\n", "<br>")
        out.append(f'<span class="acc">{esc}{UNDERLINE}</span>' if i % 2 else esc)
    return "".join(out)


def logo_uri(mono_rgb=None):
    from PIL import Image
    p = ROOT / "assets" / "logo_dark.b64"
    if not p.exists():
        return None
    im = Image.open(io.BytesIO(base64.b64decode("".join(p.read_text().split())))).convert("RGBA")
    if mono_rgb:
        mono = Image.new("RGBA", im.size, mono_rgb + (0,))
        mono.putalpha(im.getchannel("A"))
        im = mono
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


CSS = r"""
@font-face { font-family: Sora; src: url("__FONTS__/Sora.ttf"); font-weight: 100 800; }
@font-face { font-family: Manrope; src: url("__FONTS__/Manrope.ttf"); font-weight: 200 800; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1080px; height: 1920px; overflow: hidden; background: #000; }
body { font-family: Manrope, sans-serif; -webkit-font-smoothing: antialiased; text-rendering: geometricPrecision; }
.navy  { --bg:#0F1E3A; --fg:#F2F3EF; --muted:rgba(242,243,239,.70); --acc:#C9A34E; --line:rgba(242,243,239,.16); --card:rgba(242,243,239,.06); --wm:rgba(242,243,239,.045); }
.sky   { --bg:#E8EEF5; --fg:#0F1E3A; --muted:rgba(15,30,58,.66); --acc:#0869B0; --line:rgba(15,30,58,.14); --card:#FFFFFF; --wm:rgba(8,105,176,.07); }
.paper { --bg:#F2F3EF; --fg:#0F1E3A; --muted:rgba(15,30,58,.64); --acc:#9A7A2E; --line:rgba(15,30,58,.14); --card:#FBFBF8; --wm:rgba(15,30,58,.045); }
#frame { position:relative; width:1080px; height:1920px; background:var(--bg); color:var(--fg); overflow:hidden; }
.grain { position:absolute; left:0; top:0; width:1080px; height:1920px; pointer-events:none; }
.sky .grain, .paper .grain { opacity:.10; mix-blend-mode:multiply; }
.navy .grain { opacity:.05; mix-blend-mode:screen; }
#wm { position:absolute; left:40px; top:1290px; font:900 400px/1 "Noto Sans CJK KR", "Noto Sans CJK JP", sans-serif;
      color:var(--wm); white-space:nowrap; letter-spacing:-.02em; will-change:transform; }
#brand { position:absolute; left:96px; top:186px; display:flex; align-items:center; gap:18px; }
#brand img { height:76px; width:auto; display:block; }
#brand span { font:800 23px/1 Manrope; letter-spacing:.2em; }
#bar { position:absolute; left:96px; right:96px; top:300px; height:5px; background:var(--line); }
#bar i { position:absolute; left:0; top:0; bottom:0; width:0; background:var(--acc); }
#stage { position:absolute; left:96px; width:860px; top:360px; height:1150px; }
.scene { position:absolute; left:0; top:0; width:860px; height:1150px; display:flex; flex-direction:column;
         justify-content:center; visibility:hidden; }
.kicker { font:800 27px/1.2 Manrope; letter-spacing:.16em; text-transform:uppercase; color:var(--acc); }
.rule { width:64px; height:6px; background:var(--acc); }
h1 { font:800 104px/1.08 Sora; letter-spacing:-.03em; }
h2 { font:800 84px/1.1 Sora; letter-spacing:-.025em; }
h1.big { font-size:128px; }
.sub, .body { font:500 48px/1.42 Manrope; color:var(--muted); }
.acc { color:var(--acc); position:relative; }
.acc svg { position:absolute; left:-4px; bottom:-10px; width:calc(100% + 8px); height:24px; overflow:visible; }
.acc svg path { fill:none; stroke:var(--acc); stroke-width:6; stroke-linecap:round; opacity:.55; }
h1 .acc { white-space:nowrap; }
h2 .acc svg, .body .acc svg { display:none; }
.num { font:800 168px/1 Sora; letter-spacing:-.045em; white-space:nowrap; font-variant-numeric:tabular-nums; }
.num .unit { font-family:Manrope; font-weight:700; font-size:.5em; color:var(--acc); margin-left:.07em; letter-spacing:0; }
.label { font:700 46px/1.3 Manrope; }
.note { font:500 36px/1.4 Manrope; color:var(--muted); }
.list { list-style:none; border-top:2px solid var(--line); }
.list li { display:grid; grid-template-columns:88px 1fr; align-items:baseline; padding:28px 0; border-bottom:2px solid var(--line); }
.list .n { font:800 40px/1 Sora; color:var(--acc); letter-spacing:-.02em; }
.list .it { font:650 50px/1.3 Manrope; }
.steps { position:relative; }
.steps li { list-style:none; display:grid; grid-template-columns:52px 1fr; padding:22px 0; position:relative; }
.steps .pt { width:24px; height:24px; margin-top:12px; border:4px solid var(--fg); background:var(--bg); position:relative; z-index:1; }
.steps li.final .pt { background:var(--acc); border-color:var(--acc); }
.steps .dt { font:800 52px/1.15 Sora; letter-spacing:-.015em; }
.steps .ev { font:500 43px/1.35 Manrope; color:var(--muted); margin-top:6px; }
.steps:before { content:""; position:absolute; left:11px; top:40px; bottom:40px; width:3px; background:var(--line); }
.endlogo { height:190px; width:auto; align-self:flex-start; }
.handle { font:800 50px/1 Manrope; letter-spacing:.01em; }
.pill { align-self:flex-start; font:800 40px/1 Manrope; padding:30px 46px; border:3px solid var(--fg); }
.navy .pill { background:var(--acc); color:#0F1E3A; border-color:var(--acc); }
.sky .pill { background:var(--acc); color:#FFFFFF; border-color:var(--acc); }
.m8{margin-top:8px}.m16{margin-top:16px}.m24{margin-top:24px}.m32{margin-top:32px}.m40{margin-top:40px}
.m48{margin-top:48px}.m56{margin-top:56px}.m64{margin-top:64px}
"""

JS = r"""
const T = __TOTAL__;
const scenes = [...document.querySelectorAll('.scene')];
const bar = document.querySelector('#bar i');
const wm = document.querySelector('#wm');
function clamp(x){ return Math.min(1, Math.max(0, x)); }
function ease(x){ x = clamp(x); return 1 - Math.pow(1 - x, 3); }
function fmt(n){ return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0'); }
const TEXT = 'h1,h2,.sub,.body,.it,.num,.label,.note,.dt,.ev,.handle,.pill,.kicker';
function overflow(s){
  if (s.scrollHeight > s.clientHeight + 2) return true;
  for (const e of s.querySelectorAll(TEXT)) { if (e.scrollWidth > e.clientWidth + 1) return true; }
  return false;
}
function fitAll(){
  const report = [];
  scenes.forEach((s, si) => {
    s.style.visibility = 'visible';
    s.querySelectorAll('[data-count]').forEach(el => { el.textContent = fmt(+el.dataset.count); });
    let k = 0;
    while (overflow(s) && k < 40) {
      s.querySelectorAll(TEXT).forEach(e => {
        const fs = parseFloat(getComputedStyle(e).fontSize);
        e.style.fontSize = (fs * 0.96) + 'px';
      });
      s.querySelectorAll('.list li, .steps li').forEach(e => {
        const p = parseFloat(getComputedStyle(e).paddingTop);
        e.style.paddingTop = e.style.paddingBottom = (p * 0.94) + 'px';
      });
      k++;
    }
    report.push({scene: si, shrink_steps: k, still_overflow: overflow(s)});
    s.style.visibility = 'hidden';
  });
  return report;
}
function render(t){
  bar.style.width = (clamp(t / T) * 100) + '%';
  if (wm) wm.style.transform = 'translateX(' + (-t * 22) + 'px)';
  scenes.forEach((s, si) => {
    const st = +s.dataset.start, en = +s.dataset.end;
    if (t < st || t >= en) { s.style.visibility = 'hidden'; s.style.display = 'none'; return; }
    s.style.display = 'flex'; s.style.visibility = 'visible';
    const lt = t - st, first = si === 0, last = si === scenes.length - 1;
    const stay = last ? 1 : clamp((en - t) / 0.2);
    const gone = 1 - stay;
    s.querySelectorAll('.a').forEach((el, i) => {
      const p = first ? 1 : ease((lt - i * 0.09) / 0.36);
      el.style.opacity = (p * stay).toFixed(3);
      el.style.transform = 'translateY(' + ((1 - p) * 40 - gone * 22).toFixed(2) + 'px)';
    });
    s.querySelectorAll('[data-count]').forEach(el => {
      const v = +el.dataset.count, p = ease((lt - 0.25) / 1.15);
      const step = v >= 100000 ? 1000 : 1;
      el.textContent = fmt(p >= 1 ? v : Math.round(v * p / step) * step);
    });
    s.querySelectorAll('.acc path').forEach(path => {
      const L = path.getTotalLength();
      path.style.strokeDasharray = L;
      const p = ease((lt - (first ? 0.2 : 0.6)) / 0.5);
      path.style.strokeDashoffset = (L * (1 - p)).toFixed(2);
      path.style.opacity = p > 0.02 ? '' : '0';
    });
  });
}
"""

GRAIN = ('<svg class="grain" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg"><filter id="n">'
         '<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="11" stitchTiles="stitch"/>'
         '<feColorMatrix type="saturate" values="0"/></filter><rect width="1080" height="1920" filter="url(#n)"/></svg>')


def scene_html(sc, logo_big):
    t = sc["type"]
    a = 'class="a'
    if t == "hook":
        h = ""
        if sc.get("kicker"):
            h += f'<div {a} kicker">{md(sc["kicker"])}</div>'
        h += f'<h1 {a}{" m32" if sc.get("kicker") else ""}">{md(sc["text"])}</h1>'
        if sc.get("sub"):
            h += f'<p {a} sub m40">{md(sc["sub"])}</p>'
        return h
    if t == "number":
        h = f'<div {a} rule"></div>'
        if sc.get("kicker"):
            h += f'<div {a} kicker m32">{md(sc["kicker"])}</div>'
        unit = f'<span class="unit">{htmlmod.escape(sc.get("unit", ""))}</span>' if sc.get("unit") else ""
        h += f'<div {a} num m32"><b data-count="{int(sc["value"])}">0</b>{unit}</div>'
        if sc.get("label"):
            h += f'<div {a} label m32">{md(sc["label"])}</div>'
        if sc.get("note"):
            h += f'<div {a} note m24">{md(sc["note"])}</div>'
        return h
    if t == "list":
        h = ""
        if sc.get("kicker"):
            h += f'<div {a} kicker">{md(sc["kicker"])}</div>'
        if sc.get("title"):
            h += f'<h2 {a}{" m24" if sc.get("kicker") else ""}">{md(sc["title"])}</h2>'
        items = "".join(f'<li {a}"><span class="n">{i:02d}</span><span class="it">{md(x)}</span></li>'
                        for i, x in enumerate(sc["items"], 1))
        return h + f'<ul class="list m48">{items}</ul>'
    if t == "steps":
        h = ""
        if sc.get("kicker"):
            h += f'<div {a} kicker">{md(sc["kicker"])}</div>'
        if sc.get("title"):
            h += f'<h2 {a}{" m24" if sc.get("kicker") else ""}">{md(sc["title"])}</h2>'
        n = len(sc["items"])
        items = "".join(
            f'<li {a}{" final" if i == n - 1 else ""}"><span class="pt"></span><div><div class="dt">{md(d)}</div>'
            f'<div class="ev">{md(e)}</div></div></li>' for i, (d, e) in enumerate(sc["items"]))
        return h + f'<ul class="steps m40">{items}</ul>'
    if t == "text":
        h = f'<div {a} rule"></div>'
        if sc.get("kicker"):
            h += f'<div {a} kicker m32">{md(sc["kicker"])}</div>'
        tag = "h1" if sc.get("big") else "h2"
        h += f'<{tag} {a} m32">{md(sc["title"])}</{tag}>'
        if sc.get("body"):
            h += f'<p {a} body m32">{md(sc["body"])}</p>'
        return h
    if t == "end":
        h = f'<img {a} endlogo" src="{logo_big}" alt="">' if logo_big else ""
        h += f'<h1 {a} m48">{md(sc.get("title", "Obuna bo‘ling"))}</h1>'
        h += f'<div {a} handle m32">{htmlmod.escape(HANDLE)}</div>'
        h += f'<p {a} body m24">{md(sc.get("sub", "Har kuni GKS bo‘yicha qisqa video"))}</p>'
        if sc.get("button", "Do‘stingizga yuboring ↗"):
            h += f'<div {a} pill m56">{md(sc.get("button", "Do‘stingizga yuboring ↗"))}</div>'
        return h
    raise ValueError(f"Noma'lum sahna turi: {t}")


def build_page(reel):
    theme = reel.get("theme", "navy")
    dark = theme == "navy"
    paper_rgb = (242, 243, 239)
    logo_small = logo_uri(paper_rgb if dark else None)
    logo_big = logo_small
    t0 = 0.0
    scenes = []
    for sc in reel["scenes"]:
        dur = float(sc.get("dur", 2.6))
        scenes.append(f'<div class="scene" data-start="{t0:.3f}" data-end="{t0 + dur:.3f}">'
                      f'{scene_html(sc, logo_big)}</div>')
        t0 += dur
    total = t0
    wm = reel.get("watermark", "")
    css = CSS.replace("__FONTS__", (ROOT / "fonts").as_uri())
    brand = (f'<img src="{logo_small}" alt="">' if logo_small else "") + f'<span>{BRAND["wordmark"]}</span>'
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="frame" class="{theme}{'' if dark else ' light'}">
{f'<div id="wm">{htmlmod.escape(wm)}</div>' if wm else ''}{GRAIN}
<div id="brand">{brand}</div><div id="bar"><i></i></div>
<div id="stage">{''.join(scenes)}</div></div>
<script>{JS.replace('__TOTAL__', f'{total:.3f}')}</script></body></html>"""
    return page, total


def render_reel(reel, out_dir, browser, sheet=False, sheet_only=False):
    page_html, total = build_page(reel)
    name = f'{reel.get("date", "")}_{reel["id"]}'.strip("_")
    mp4 = out_dir / f"{name}.mp4"
    cover = out_dir / f"{name}_cover.jpg"
    with tempfile.TemporaryDirectory() as tmp:
        hp = Path(tmp) / "reel.html"
        hp.write_text(page_html, encoding="utf-8")
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(hp.as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.evaluate("Promise.all([document.fonts.load('800 100px Sora'), document.fonts.load('500 44px Manrope'),"
                      "document.fonts.load('900 400px \"Noto Sans CJK KR\"')]).then(() => true)")
        report = page.evaluate("fitAll()")
        bad = [r for r in report if r["still_overflow"]]
        if bad:
            print(f"  ! {reel['id']}: sahnaga sig'madi {bad}", file=sys.stderr)
        if sheet or sheet_only:
            from PIL import Image
            shots, t0 = [], 0.0
            for sc in reel["scenes"]:
                d = float(sc.get("dur", 2.6))
                page.evaluate(f"render({t0 + d * 0.8:.3f})")
                shots.append(Image.open(io.BytesIO(page.screenshot(type="png"))).convert("RGB").resize((360, 640)))
                t0 += d
            canvas = Image.new("RGB", (len(shots) * 368 + 8, 656), "white")
            for i, im in enumerate(shots):
                canvas.paste(im, (8 + i * 368, 8))
            canvas.save(out_dir / f"{name}_sheet.png")
            if sheet_only:
                page.close()
                print(f"  {name}_sheet.png")
                return None, None, total
        frames = int(round(total * FPS))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg",
               "-i", "-", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
               "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
               "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-r", str(FPS),
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(frames):
            page.evaluate(f"render({f / FPS:.4f})")
            proc.stdin.write(page.screenshot(type="jpeg", quality=94))
        proc.stdin.close()
        if proc.wait() != 0:
            sys.exit(f"ffmpeg xatosi: {reel['id']}")
        first_end = float(reel["scenes"][0].get("dur", 2.6))
        page.evaluate(f"render({min(1.0, first_end - 0.3):.3f})")
        cover.write_bytes(page.screenshot(type="jpeg", quality=93))
        page.close()
    print(f"  {mp4.name}  ({total:.1f} s, {frames} kadr)")
    return mp4, cover, total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--sheet-only", action="store_true")
    args = ap.parse_args()
    batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    out_dir = Path(args.out or Path(args.batch).with_suffix(""))
    out_dir.mkdir(parents=True, exist_ok=True)
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    reels = [r for r in batch["reels"] if not only or r["id"] in only]
    from playwright.sync_api import sync_playwright
    caps = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--font-render-hinting=none", "--disable-gpu"])
        for r in reels:
            mp4, cover, total = render_reel(r, out_dir, browser, args.sheet, args.sheet_only)
            if mp4 is None:
                continue
            caps.append(f"=== {r.get('date', '')} · {r['id']} · {mp4.name} ({total:.0f} s) ===\n\n"
                        f"{uz(r.get('caption', ''))}\n")
        browser.close()
    if caps:
        (out_dir / "captions.txt").write_text("\n\n".join(caps), encoding="utf-8")


if __name__ == "__main__":
    main()
