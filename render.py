#!/usr/bin/env python3
"""GKS Academics — Instagram karusel rasmlarini yasaydi.

Foydalanish:
    python3 render.py posts/2026-10-09/post.json

post.json ichidagi "slides" ro'yxatidan 1080x1350 JPEG fayllar yasaydi
(01.jpg, 02.jpg, ...) va ularni post.json yonidagi papkaga saqlaydi.

Slayd turlari: cover, point, list, stat, cta  (README.md ga qarang)
Sarlavhalarda *so'z* ko'rinishida yozilgan so'zlar oltin rangda chiqadi.
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


def draw_lines(d, x, y, f, lines, size, lh, color, gold=GOLD):
    space = f.getlength(" ")
    for line in lines:
        cx = x
        for word, is_gold in line:
            d.text((cx, y), word, font=f, fill=gold if is_gold else color)
            cx += f.getlength(word) + space
        y += size * lh
    return y


def text_block(d, text, x, y, max_w, max_h, path, weight, big, small, lh, color):
    f, lines, size = fit(text, path, weight, max_w, max_h, big, small, lh)
    end = draw_lines(d, x, y, f, lines, size, lh, color)
    return end


class Block:
    """Avval o'lchab, keyin chizish uchun matn bloki (vertikal markazlash uchun)."""

    def __init__(self, text, path, weight, max_h, big, small, lh, color, gap_before=0, x=M, max_w=W - 2 * M):
        self.f, self.lines, self.size = fit(text, path, weight, max_w, max_h, big, small, lh)
        self.lh, self.color, self.gap, self.x = lh, color, gap_before, x
        self.h = len(self.lines) * self.size * lh

    def draw(self, d, y):
        return draw_lines(d, self.x, y, self.f, self.lines, self.size, self.lh, self.color)


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


def header(d, img, dark, idx, total):
    fg = GOLD if dark else NAVY
    muted = mix(PAPER, NAVY, 0.45) if dark else mix(NAVY, PAPER, 0.45)
    logo_path = ROOT / "assets" / ("logo_light.png" if dark else "logo_dark.png")
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        h = 56
        logo = logo.resize((round(logo.width * h / logo.height), h), Image.LANCZOS)
        img.paste(logo, (M, M - 8), logo)
    else:
        f = font(MANROPE, 26, 800)
        x = M
        for ch in BRAND["wordmark"]:
            d.text((x, M), ch, font=f, fill=fg)
            x += f.getlength(ch) + 5
    f = font(MANROPE, 26, 600)
    counter = f"{idx:02d} / {total:02d}"
    d.text((W - M - f.getlength(counter), M), counter, font=f, fill=muted)


def footer(d, dark, last):
    muted = mix(PAPER, NAVY, 0.45) if dark else mix(NAVY, PAPER, 0.45)
    line = mix(PAPER, NAVY, 0.75) if dark else mix(NAVY, PAPER, 0.82)
    y = H - M - 10
    d.line([(M, y - 34), (W - M, y - 34)], fill=line, width=2)
    f = font(MANROPE, 26, 600)
    d.text((M, y - 6), uz(BRAND.get("handle") or BRAND["name"]), font=f, fill=muted)
    if not last:
        f2 = font(MANROPE, 26, 700)
        hint = uz(BRAND["swipe_hint"])
        d.text((W - M - f2.getlength(hint), y - 6), hint, font=f2, fill=GOLD if dark else NAVY)


def slide_cover(s, idx, total):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    header(d, img, True, idx, total)
    parts = [(6, lambda y: d.rectangle([M, y, M + 72, y + 6], fill=GOLD), 0)]
    if s.get("kicker"):
        f = font(MANROPE, 34, 700)
        parts.append((40, lambda y: d.text((M, y), uz(s["kicker"]).upper(), font=f, fill=GOLD), 44))
    parts.append(Block(s["title"], SORA, 800, 560, 108, 64, 1.12, PAPER, gap_before=34))
    if s.get("subtitle"):
        parts.append(Block(s["subtitle"], MANROPE, 500, 220, 42, 34, 1.4, mix(PAPER, NAVY, 0.28), gap_before=40))
    layout(d, parts, bias=0.55)
    footer(d, True, idx == total)
    return img


def number_part(d, num):
    f = font(SORA, 150, 800)
    return (150, lambda y: d.text((M - 6, y - 28), num, font=f, fill=GOLD), 0)


def slide_point(s, idx, total):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    header(d, img, False, idx, total)
    parts = []
    if s.get("number"):
        parts.append(number_part(d, s["number"]))
    parts.append(Block(s["title"], SORA, 800, 320, 76, 48, 1.15, NAVY, gap_before=40 if parts else 0))
    if s.get("body"):
        parts.append(Block(s["body"], MANROPE, 500, 520, 44, 30, 1.45, mix(NAVY, PAPER, 0.18), gap_before=40))
    layout(d, parts)
    footer(d, False, idx == total)
    return img


def slide_list(s, idx, total):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    header(d, img, False, idx, total)
    parts = []
    if s.get("number"):
        parts.append(number_part(d, s["number"]))
    parts.append(Block(s["title"], SORA, 800, 260, 72, 46, 1.15, NAVY, gap_before=40 if parts else 0))
    items = s.get("items", [])
    budget = 1350 - 210 - 190 - sum(p.gap + p.h if isinstance(p, Block) else p[0] for p in parts) - 56
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
            d.rectangle([M, y + size * 0.45, M + 18, y + size * 0.45 + 18], fill=GOLD)
            y = draw_lines(d, M + 52, y, f, lines, size, 1.4, NAVY) + 26

    parts.append((list_h, draw_items, 56))
    layout(d, parts)
    footer(d, False, idx == total)
    return img


def slide_stat(s, idx, total):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    header(d, img, True, idx, total)
    y = 330
    f, lines, size = fit(s["value"], SORA, 800, W - 2 * M, 300, 240, 120, 1.0)
    draw_lines(d, M - 8, y, f, lines, size, 1.0, GOLD)
    y += size * len(lines) + 60
    y = text_block(d, s["label"], M, y, W - 2 * M, 260, SORA, 800, 64, 42, 1.15, PAPER)
    if s.get("note"):
        y += 32
        text_block(d, s["note"], M, y, W - 2 * M, H - y - 210, MANROPE, 500, 38, 28, 1.45,
                   mix(PAPER, NAVY, 0.28))
    footer(d, True, idx == total)
    return img


def slide_cta(s, idx, total):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    header(d, img, True, idx, total)
    y = 380
    d.rectangle([M, y, M + 72, y + 6], fill=GOLD)
    y += 50
    y = text_block(d, s["title"], M, y, W - 2 * M, 380, SORA, 800, 88, 54, 1.12, PAPER)
    if s.get("body"):
        y += 36
        y = text_block(d, s["body"], M, y, W - 2 * M, 260, MANROPE, 500, 40, 30, 1.4,
                       mix(PAPER, NAVY, 0.28))
    if s.get("button"):
        y += 56
        f = font(MANROPE, 36, 800)
        label = uz(s["button"])
        bw = f.getlength(label) + 88
        d.rectangle([M, y, M + bw, y + 92], fill=GOLD)
        d.text((M + 44, y + 24), label, font=f, fill=NAVY)
    footer(d, True, True)
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
