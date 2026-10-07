#!/usr/bin/env python3
"""GKS Academics — Instagram karusel rasmlarini yasaydi.

Foydalanish:
    python3 render.py posts/2026-10-09/post.json

post.json ichidagi "slides" ro'yxatidan 1080x1350 JPEG fayllar yasaydi
(01.jpg, 02.jpg, ...) va ularni post.json yonidagi papkaga saqlaydi.

Slayd turlari: cover, point, list, stat, cta  (README.md ga qarang)
Sarlavhalarda *so'z* ko'rinishida yozilgan so'zlar to'q fonda oltin rangda chiqadi
(och fonda rang ishlatilmaydi — minimalist uslub).

Logo: assets/logo.png (yoki logo-512.png, logo.jpg) bo'lsa, bir rangli qilib
yuqori chap burchakka qo'yiladi. Telegram va sayt manzillari brand.json dan olinadi.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BRAND = json.loads((ROOT / "brand.json").read_text(encoding="utf-8"))

W, H = 1080, 1350
M = 96  # chekka bo'shliq
NAVY = BRAND["colors"]["navy"]
PAPER = BRAND["colors"]["paper"]
GOLD = BRAND["colors"]["gold"]
SORA = str(ROOT / "fonts" / "Sora.ttf")
MANROPE = str(ROOT / "fonts" / "Manrope.ttf")


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """a rangdan b rangga t ulushda aralashtirish (faqat brend ranglari ichida tus olish uchun)."""
    a, b = hex2rgb(a), hex2rgb(b)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def uz(text):
    """O'zbekcha apostroflarni shriftda bor belgilarga keltiradi: o‘ g‘ va ’."""
    if not text:
        return ""
    text = text.replace("\u02bb", "\u2018").replace("\u02bc", "\u2019").replace("`", "\u2018")
    text = re.sub(r"([OoGg])'", "\\1\u2018", text)
    return text.replace("'", "\u2019")


def tokens(text):
    """Matnni so'zlarga bo'ladi; *yulduzcha* ichidagilar 'gold' bayrog'ini oladi."""
    out = []
    for para in uz(text).split("\n"):
        line = []
        gold = False
        for word in para.split(" "):
            if not word:
                continue
            start = word.startswith("*")
            w = word.lstrip("*")
            if start:
                gold = True
            end = w.endswith("*") or w.rstrip(".,:;!?").endswith("*")
            w_clean = w.replace("*", "")
            line.append((w_clean, gold))
            if end:
                gold = False
        out.append(line)
    return out


def wrap(paras, f, max_w):
    space = f.getlength(" ")
    lines = []
    for para in paras:
        cur, cur_w = [], 0
        for word, gold in para:
            ww = f.getlength(word)
            add = ww if not cur else cur_w + space + ww
            if cur and add > max_w:
                lines.append(cur)
                cur, cur_w = [(word, gold)], ww
            else:
                cur.append((word, gold))
                cur_w = add
        lines.append(cur)
    return lines


def fit(text, path, weight, max_w, max_h, big, small, lh):
    paras = tokens(text)
    for size in range(big, small - 1, -2):
        f = font(path, size, weight)
        lines = wrap(paras, f, max_w)
        too_wide = any(f.getlength(w) > max_w for line in lines for w, _ in line)
        if len(lines) * size * lh <= max_h and not too_wide:
            return f, lines, size
    f = font(path, small, weight)
    return f, wrap(paras, f, max_w), small


def draw_lines(d, x, y, f, lines, size, lh, color, gold=None):
    gold = gold or color
    space = f.getlength(" ")
    for line in lines:
        cx = x
        for word, is_gold in line:
            d.text((cx, y), word, font=f, fill=gold if is_gold else color)
            cx += f.getlength(word) + space
        y += size * lh
    return y


def text_block(d, text, x, y, max_w, max_h, path, weight, big, small, lh, color, accent=None):
    f, lines, size = fit(text, path, weight, max_w, max_h, big, small, lh)
    end = draw_lines(d, x, y, f, lines, size, lh, color, accent)
    return end


class Block:
    """Avval o'lchab, keyin chizish uchun matn bloki (vertikal markazlash uchun)."""

    def __init__(self, text, path, weight, max_h, big, small, lh, color, gap_before=0, x=M, max_w=W - 2 * M,
                 accent=None):
        self.f, self.lines, self.size = fit(text, path, weight, max_w, max_h, big, small, lh)
        self.lh, self.color, self.gap, self.x, self.accent = lh, color, gap_before, x, accent
        self.h = len(self.lines) * self.size * lh

    def draw(self, d, y):
        return draw_lines(d, self.x, y, self.f, self.lines, self.size, self.lh, self.color, self.accent)


def layout(d, parts, top=210, bottom=H - 190, bias=0.42):
    """parts: Block yoki (balandlik, chizish_funksiyasi, oldingi_bo'shliq). Markazlab chizadi."""
    total = sum(p.gap + p.h if isinstance(p, Block) else p[2] + p[0] for p in parts)
    y = top + max(0, (bottom - top - total) * bias)
    for p in parts:
        if isinstance(p, Block):
            y += p.gap
            p.draw(d, y)
            y += p.h
        else:
            h, fn, gap = p
            y += gap
            fn(y)
            y += h
    return y


_LOGO_CACHE = {}


def load_logo_mask():
    """assets/ dagi logodan bir rangli niqob (L rejim) yasaydi. Topilmasa None."""
    if "mask" in _LOGO_CACHE:
        return _LOGO_CACHE["mask"]
    mask = None
    for name in ("logo.png", "logo-512.png", "logo.jpg", "logo.jpeg"):
        p = ROOT / "assets" / name
        if not p.exists():
            continue
        try:
            im = Image.open(p)
            im.load()
        except Exception:
            continue
        im = im.convert("RGBA")
        alpha = im.getchannel("A")
        if alpha.getextrema()[0] < 250:  # shaffof fonli PNG
            mask = alpha
        else:  # oq fonli rasm: to'q joylar = logo
            lum = im.convert("L")
            mask = lum.point(lambda v: 0 if v > 235 else min(255, int((235 - v) * 1.6)))
        box = mask.getbbox()
        if box:
            mask = mask.crop(box)
            break
        mask = None
    _LOGO_CACHE["mask"] = mask
    return mask


def paste_logo(img, x, y, h, color):
    mask = load_logo_mask()
    if mask is None:
        return 0
    w = round(mask.width * h / mask.height)
    m = mask.resize((w, h), Image.LANCZOS)
    img.paste(Image.new("RGB", (w, h), color), (x, y), m)
    return w


def header(d, img, dark, idx, total):
    fg = PAPER if dark else NAVY
    muted = mix(PAPER, NAVY, 0.45) if dark else mix(NAVY, PAPER, 0.45)
    f = font(MANROPE, 24, 800)
    x = M
    lw = paste_logo(img, M, M - 22, 68, hex2rgb(fg) if isinstance(fg, str) else fg)
    if lw:
        x = M + lw + 20
    for ch in BRAND["wordmark"]:
        d.text((x, M), ch, font=f, fill=fg)
        x += f.getlength(ch) + 4
    f = font(MANROPE, 24, 600)
    counter = f"{idx:02d} / {total:02d}"
    d.text((W - M - f.getlength(counter), M), counter, font=f, fill=muted)


def footer(d, dark):
    """Pastki qator: chapda Telegram, o'ngda sayt manzili (brand.json)."""
    strong = mix(PAPER, NAVY, 0.20) if dark else mix(NAVY, PAPER, 0.15)
    line = mix(PAPER, NAVY, 0.78) if dark else mix(NAVY, PAPER, 0.85)
    y = H - M - 14
    d.line([(M, y - 30), (W - M, y - 30)], fill=line, width=2)
    vals = [BRAND.get(k) for k in ("telegram", "website") if BRAND.get(k)] or [BRAND["name"]]
    size = 24
    while size > 16:
        f = font(MANROPE, size, 600)
        if sum(f.getlength(v) for v in vals) + 48 * (len(vals) - 1) <= W - 2 * M:
            break
        size -= 1
    f = font(MANROPE, size, 600)
    d.text((M, y), vals[0], font=f, fill=strong)
    if len(vals) > 1:
        d.text((W - M - f.getlength(vals[1]), y), vals[1], font=f, fill=strong)


def accent_rule(d, x, y, w=64):
    d.rectangle([x, y, x + w, y + 5], fill=GOLD)


def slide_cover(s, idx, total):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    header(d, img, True, idx, total)
    parts = [(5, lambda y: accent_rule(d, M, y), 0)]
    if s.get("kicker"):
        f = font(MANROPE, 30, 700)
        kick = uz(s["kicker"]).upper()
        parts.append((36, lambda y: d.text((M, y), kick, font=f, fill=mix(PAPER, NAVY, 0.35)), 40))
    parts.append(Block(s["title"], SORA, 800, 560, 104, 62, 1.12, PAPER, gap_before=30, accent=GOLD))
    if s.get("subtitle"):
        parts.append(Block(s["subtitle"], MANROPE, 500, 220, 40, 32, 1.42, mix(PAPER, NAVY, 0.30), gap_before=40))
    layout(d, parts, bias=0.5)
    if total > 1:
        f = font(MANROPE, 24, 600)
        hint = uz(BRAND["swipe_hint"])
        d.text((W - M - f.getlength(hint), H - M - 110), hint, font=f, fill=mix(PAPER, NAVY, 0.40))
    footer(d, True)
    return img


def number_part(d, num):
    f = font(SORA, 140, 800)
    return (140, lambda y: d.text((M - 6, y - 26), num, font=f, fill=mix(NAVY, PAPER, 0.84)), 0)


def slide_point(s, idx, total):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    header(d, img, False, idx, total)
    parts = []
    if s.get("number"):
        parts.append(number_part(d, s["number"]))
    parts.append((5, lambda y: accent_rule(d, M, y, 48), 36 if parts else 0))
    parts.append(Block(s["title"], SORA, 800, 320, 72, 46, 1.15, NAVY, gap_before=30))
    if s.get("body"):
        parts.append(Block(s["body"], MANROPE, 500, 520, 44, 30, 1.45, mix(NAVY, PAPER, 0.18), gap_before=40))
    layout(d, parts)
    footer(d, False)
    return img


def slide_list(s, idx, total):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    header(d, img, False, idx, total)
    parts = []
    if s.get("number"):
        parts.append(number_part(d, s["number"]))
    parts.append((5, lambda y: accent_rule(d, M, y, 48), 36 if parts else 0))
    parts.append(Block(s["title"], SORA, 800, 260, 68, 44, 1.15, NAVY, gap_before=30))
    items = s.get("items", [])
    budget = 1350 - 210 - 190 - sum(p.gap + p.h if isinstance(p, Block) else p[0] + p[2] for p in parts) - 56
    tw = W - 2 * M - 52
    size = 42
    while size > 26:
        f = font(MANROPE, size, 600)
        hsum = sum(len(wrap(tokens(it), f, tw)) * size * 1.4 + 26 for it in items)
        if hsum <= budget:
            break
        size -= 2
    f = font(MANROPE, size, 600)
    wrapped = [wrap(tokens(it), f, tw) for it in items]
    list_h = sum(len(w_) * size * 1.4 + 26 for w_ in wrapped) - 26

    def draw_items(y):
        for lines in wrapped:
            d.rectangle([M, y + size * 0.62, M + 22, y + size * 0.62 + 3], fill=NAVY)
            y = draw_lines(d, M + 52, y, f, lines, size, 1.4, NAVY) + 26

    parts.append((list_h, draw_items, 56))
    layout(d, parts)
    footer(d, False)
    return img


def slide_stat(s, idx, total):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    header(d, img, True, idx, total)
    y = 330
    f, lines, size = fit(s["value"], SORA, 800, W - 2 * M, 300, 240, 120, 1.0)
    draw_lines(d, M - 8, y, f, lines, size, 1.0, PAPER)
    y += size * len(lines) + 60
    y = text_block(d, s["label"], M, y, W - 2 * M, 260, SORA, 800, 64, 42, 1.15, PAPER)
    if s.get("note"):
        y += 32
        text_block(d, s["note"], M, y, W - 2 * M, H - y - 210, MANROPE, 500, 38, 28, 1.45,
                   mix(PAPER, NAVY, 0.28))
    footer(d, True)
    return img


def slide_cta(s, idx, total):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    header(d, img, True, idx, total)
    parts = []
    if load_logo_mask() is not None:
        parts.append((150, lambda y: paste_logo(img, M, int(y), 150, hex2rgb(PAPER)), 0))
    parts.append((5, lambda y: accent_rule(d, M, y), 48 if parts else 0))
    parts.append(Block(s["title"], SORA, 800, 360, 84, 52, 1.12, PAPER, gap_before=34, accent=GOLD))
    if s.get("body"):
        parts.append(Block(s["body"], MANROPE, 500, 240, 40, 30, 1.42, mix(PAPER, NAVY, 0.30), gap_before=34))
    if s.get("button"):
        f = font(MANROPE, 32, 700)
        label = uz(s["button"])
        bw = f.getlength(label) + 80

        def btn(y):
            d.rectangle([M, y, M + bw, y + 84], outline=PAPER, width=2)
            d.text((M + 40, y + 22), label, font=f, fill=PAPER)
        parts.append((84, btn, 52))
    layout(d, parts, bias=0.5)
    footer(d, True)
    return img


RENDERERS = {
    "cover": slide_cover,
    "point": slide_point,
    "list": slide_list,
    "stat": slide_stat,
    "cta": slide_cta,
}


def render(post_json):
    post_json = Path(post_json)
    spec = json.loads(post_json.read_text(encoding="utf-8"))
    slides = spec["slides"]
    if not 1 <= len(slides) <= 10:
        sys.exit("Slaydlar soni 1 dan 10 gacha bo'lishi kerak (Instagram karusel limiti).")
    n = 0
    for s in slides:  # point/list slaydlarga avtomatik raqam (01, 02, ...)
        if s["type"] in ("point", "list") and s.get("numbered", True):
            n += 1
            s.setdefault("number", f"{n:02d}")
    out = []
    for i, s in enumerate(slides, 1):
        img = RENDERERS[s["type"]](s, i, len(slides))
        path = post_json.parent / f"{i:02d}.jpg"
        img.save(path, "JPEG", quality=92, optimize=True, progressive=False)
        out.append(path)
        print(path)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    render(sys.argv[1])
