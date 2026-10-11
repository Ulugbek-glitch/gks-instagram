#!/usr/bin/env python3
"""Instagram karusel rasmlarini Telegram kanalga albom qilib yuboradi.

Ishga tushiruvchi: .github/workflows/telegram.yml
  - "Render post images" tugagach (Instagram'ga joylanishini kutib) va kuniga bir marta
    zaxira sifatida: bugungi yoki kechagi, hali yuborilmagan postlar;
  - qo'lda (Actions -> Telegram crosspost -> Run workflow): sana berilsa, o'sha kungi post.

Muhit o'zgaruvchilari:
  TELEGRAM_BOT_TOKEN  @BotFather bergan token (GitHub secret, repoga yozilmaydi)
  TELEGRAM_CHAT_ID    kanal, masalan @gks_academic
  POST_DATE           ixtiyoriy, YYYY-MM-DD

Izoh Instagram caption'idan olinadi: heshteglar va Telegram havolasi olib tashlanadi,
o'rniga Instagram havolasi qo'yiladi. Holat: telegram/sent.json (qayta yuborilmaydi).
Faqat standart kutubxona ishlatiladi.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
STATE = ROOT / "telegram" / "sent.json"
API = os.environ.get("TELEGRAM_API", "https://api.telegram.org")
TZ = dt.timezone(dt.timedelta(hours=5))  # Toshkent (AGENT.md dagi DATE ham shu bo'yicha)
START = "2026-10-11"   # bundan oldingi postlar avtomatik yuborilmaydi (qo'lda yuborish mumkin)
MAX_AGE_DAYS = 1       # avtomatik rejim: bugungi va kechagi postlar
CAPTION_LIMIT = 1024   # Telegram rasm izohi chegarasi; uzunroq bo'lsa matn alohida xabar bo'ladi
ALBUM_MAX = 10


class TelegramError(Exception):
    def __init__(self, code, desc, params=None):
        super().__init__(f"{code}: {desc}")
        self.code, self.desc, self.params = code, desc or "", params or {}


def log(msg):
    print(msg, flush=True)


def summary(msg):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def fail(msg):
    log(f"::error::{msg}")
    summary(f"❌ {msg}")
    return 1


def hint(err):
    d = err.desc.lower()
    if err.code == 401:
        return ("Token noto'g'ri: GitHub -> Settings -> Secrets and variables -> Actions -> "
                "TELEGRAM_BOT_TOKEN ni @BotFather bergan token bilan yangilang.")
    if "chat not found" in d:
        return "Kanal topilmadi: botni kanalga admin qilib qo'shing va TELEGRAM_CHAT_ID ni tekshiring."
    if err.code == 403 or "rights" in d or "not a member" in d:
        return "Botda kanalga yozish huquqi yo'q: kanal -> Administrators -> bot -> 'Post messages' ni yoqing."
    return ""


def utf16_len(s):
    return len(s.encode("utf-16-le")) // 2


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    out = bytearray()
    for name, value in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += str(value).encode() + b"\r\n"
    for name, path in files.items():
        out += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                f'filename="{path.name}"\r\nContent-Type: image/jpeg\r\n\r\n').encode()
        out += path.read_bytes() + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def call(token, method, fields, files=None):
    body, ctype = multipart(fields, files or {})
    for attempt in range(3):
        req = urllib.request.Request(f"{API}/bot{token}/{method}", data=body,
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read().decode() or "{}")
            except ValueError:
                data = {}
            data.setdefault("error_code", e.code)
            data.setdefault("description", str(e.reason))
        if data.get("ok"):
            return data["result"]
        wait = (data.get("parameters") or {}).get("retry_after")
        if data.get("error_code") == 429 and wait and attempt < 2:  # 429 = yuborilmagan, qayta urinish xavfsiz
            time.sleep(min(int(wait), 60) + 1)
            continue
        raise TelegramError(data.get("error_code"), data.get("description"), data.get("parameters"))


def tg_caption(caption, brand):
    """Instagram izohini Telegram uchun moslaydi."""
    tg = brand.get("telegram", "t.me/gks_academic")
    ig_line = "📲 Instagram: instagram.com/" + brand.get("instagram", "@gks_academics").lstrip("@")
    paras, has_ig = [], False
    for para in re.split(r"\n\s*\n", caption.strip()):
        lines = []
        for line in para.splitlines():
            s = line.strip()
            if not s or re.fullmatch(r"(#\S+\s*)+", s):        # heshteg qatori
                continue
            if tg in s:                                         # aloqa blokidagi Telegram -> Instagram
                lines.append(ig_line)
                has_ig = True
                continue
            if "telegram" in s.lower():                         # "Telegram kanalimizga qo'shiling" kabi gaplar
                s = " ".join(x for x in re.split(r"(?<=[.!?])\s+", s) if "telegram" not in x.lower())
                if not s:
                    continue
            lines.append(s)
        if lines:
            paras.append("\n".join(lines))
    if not has_ig:
        paras.append(ig_line)
    return "\n\n".join(paras)


def send_media(token, chat, images, caption):
    """Rasm(lar)ni yuboradi. Qaytaradi: (message_ids, izoh_alohida_yuborilishi_kerakmi)."""
    images = images[:ALBUM_MAX]
    fits = bool(caption) and utf16_len(caption) <= CAPTION_LIMIT
    if len(images) == 1:
        fields = {"chat_id": chat}
        if fits:
            fields["caption"] = caption
        ids = [call(token, "sendPhoto", fields, {"photo": images[0]})["message_id"]]
    else:
        media, files = [], {}
        for i, path in enumerate(images):
            item = {"type": "photo", "media": f"attach://p{i}"}
            if i == 0 and fits:
                item["caption"] = caption
            media.append(item)
            files[f"p{i}"] = path
        result = call(token, "sendMediaGroup",
                      {"chat_id": chat, "media": json.dumps(media, ensure_ascii=False)}, files)
        ids = [m["message_id"] for m in result]
    return ids, bool(caption) and not fits


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")


def candidates(state, forced):
    if forced:
        return [forced]
    today = dt.date.fromisoformat(os.environ.get("TODAY") or dt.datetime.now(TZ).date().isoformat())
    lo = max(START, (today - dt.timedelta(days=MAX_AGE_DAYS)).isoformat())
    hi = today.isoformat()
    return sorted(p.name for p in POSTS.iterdir()
                  if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
                  and lo <= p.name <= hi and p.name not in state)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or "@gks_academic"
    forced = os.environ.get("POST_DATE", "").strip()
    if forced and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", forced):
        return fail(f"Sana noto'g'ri: {forced!r} (YYYY-MM-DD ko'rinishida yozing).")
    if not token:
        log("::warning::TELEGRAM_BOT_TOKEN secret qo'shilmagan — Telegram'ga hech narsa yuborilmadi.")
        summary("⚠️ TELEGRAM_BOT_TOKEN secret qo'shilmagan.")
        return 0

    brand = json.loads((ROOT / "brand.json").read_text(encoding="utf-8"))
    state = load_state()
    todo = candidates(state, forced)
    if not todo:
        log("Yuboriladigan yangi post yo'q.")
    for date in todo:
        if date in state:
            log(f"{date}: allaqachon yuborilgan ({state[date].get('sent_at')}).")
            summary(f"ℹ️ {date}: allaqachon yuborilgan.")
            continue
        folder = POSTS / date
        if not (folder / "post.json").exists():
            if forced:
                return fail(f"{date}: posts/{date}/post.json topilmadi.")
            continue
        post = json.loads((folder / "post.json").read_text(encoding="utf-8"))
        images = sorted(folder.glob("[0-9][0-9].jpg"))
        need = min(len(post.get("slides") or [None]), ALBUM_MAX)
        if len(images) < need:
            msg = f"{date}: rasmlar hali tayyor emas ({len(images)}/{need})."
            if forced:
                return fail(msg)
            log(msg)
            continue

        caption = tg_caption(post.get("caption", ""), brand)
        try:
            ids, text_separately = send_media(token, chat, images, caption)
        except TelegramError as e:
            return fail(f"{date}: Telegram xatosi {e.code} — {e.desc}. {hint(e)}".strip())
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return fail(f"{date}: Telegram'ga ulanib bo'lmadi — {e}.")

        state[date] = {"sent_at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
                       "chat": chat, "photos": len(ids), "message_ids": ids}
        save_state(state)  # albom yuborildi — endi qayta yuborilmaydi
        if text_separately:
            try:
                msg = call(token, "sendMessage", {
                    "chat_id": chat, "text": caption,
                    "link_preview_options": json.dumps({"is_disabled": True})})
            except (TelegramError, urllib.error.URLError, TimeoutError, OSError) as e:
                return fail(f"{date}: rasmlar yuborildi, lekin izoh matni yuborilmadi — {e}.")
            state[date]["message_ids"].append(msg["message_id"])
            save_state(state)
        log(f"{date}: yuborildi — {len(ids)} ta rasm -> {chat}"
            + (" (izoh alohida xabarda)" if text_separately else ""))
        summary(f"✅ {date}: «{post.get('topic', '')}» — {len(ids)} ta rasm {chat} kanaliga yuborildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
