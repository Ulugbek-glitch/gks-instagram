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

Videolar (Reels): telegram/videos/SANA.json — {"video": "reels/fayl.mp4", "text": "...",
"cover_at": 3.0}. Video va matn kanalga sendVideo bilan ketadi (matn o'zgartirilmaydi,
Instagram havolasi qo'shilmaydi). Muqova: ffmpeg bo'lsa, cover_at soniyadagi kadr.
Video fayli hali repoda bo'lmasa, o'tkazib yuboriladi va keyingi ishga tushishda yuboriladi.
Holat kaliti: "video:SANA".
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
STATE = ROOT / "telegram" / "sent.json"
VIDEOS = ROOT / "telegram" / "videos"
CTYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4"}
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
                f'filename="{path.name}"\r\nContent-Type: '
                f'{CTYPES.get(path.suffix.lower(), "application/octet-stream")}\r\n\r\n').encode()
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


def find_video(rel):
    """Video faylini topadi: avval ko'rsatilgan yo'l, bo'lmasa repodagi shu nomli fayl."""
    path = ROOT / rel
    if path.is_file():
        return path
    for cand in sorted(ROOT.rglob(Path(rel).name)):
        if ".git" not in cand.parts and cand.is_file():
            return cand
    return None


def find_ffmpeg():
    """Tizimdagi ffmpeg; bo'lmasa imageio-ffmpeg (pip) ichidagi tayyor ffmpeg; bo'lmasa None."""
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--user", "imageio-ffmpeg"],
                       check=True, timeout=180, capture_output=True)
        out = subprocess.run([sys.executable, "-c", "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())"],
                             check=True, timeout=60, capture_output=True, text=True)
        return out.stdout.strip() or None
    except (subprocess.SubprocessError, OSError) as e:
        log(f"::warning::ffmpeg topilmadi ({e}) — video muqovasiz yuboriladi.")
        return None


def make_covers(video, at, tmp):
    """ffmpeg bo'lsa: to'liq muqova va 320px eskiz. Bo'lmasa — {}."""
    if at is None:
        return {}
    ff = find_ffmpeg()
    if not ff:
        return {}
    out = {}
    for name, vf in (("cover", None), ("thumbnail", "scale=320:-2")):
        dst = Path(tmp) / f"{name}.jpg"
        cmd = [ff, "-v", "error", "-y", "-ss", str(at), "-i", str(video), "-frames:v", "1", "-q:v", "3"]
        if vf:
            cmd += ["-vf", vf]
        try:
            subprocess.run(cmd + [str(dst)], check=True, timeout=60)
        except (subprocess.SubprocessError, OSError) as e:
            log(f"::warning::Muqova kadri olinmadi ({name}): {e}")
            return {}
        if dst.is_file() and dst.stat().st_size > 0:
            out[name] = dst
    if "thumbnail" in out and out["thumbnail"].stat().st_size > 200_000:
        del out["thumbnail"]  # Telegram eskiz chegarasi 200 kB
    return out


def send_video(token, chat, video, text, meta, covers):
    """Videoni yuboradi. Qaytaradi: (message_ids, matn_alohida_yuborilishi_kerakmi)."""
    fits = bool(text) and utf16_len(text) <= CAPTION_LIMIT
    fields = {"chat_id": chat, "supports_streaming": "true"}
    for key in ("width", "height", "duration"):
        if meta.get(key):
            fields[key] = int(meta[key])
    if fits:
        fields["caption"] = text
    files = {"video": video}
    extra = {}
    if "cover" in covers:
        extra["cover"] = "attach://cover"
        files["cover"] = covers["cover"]
    if "thumbnail" in covers:
        extra["thumbnail"] = "attach://thumbnail"
        files["thumbnail"] = covers["thumbnail"]
    try:
        msg = call(token, "sendVideo", {**fields, **extra}, files)
    except TelegramError as e:
        if e.code != 400 or not extra:
            raise
        log(f"::warning::Muqova bilan yuborilmadi ({e.desc}) — muqovasiz qayta urinilmoqda.")
        msg = call(token, "sendVideo", fields, {"video": video})
    return [msg["message_id"]], bool(text) and not fits


def video_candidates(state, forced):
    if not VIDEOS.is_dir():
        return []
    names = sorted(p.stem for p in VIDEOS.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
    if forced:
        return [d for d in names if d == forced]
    today = dt.date.fromisoformat(os.environ.get("TODAY") or dt.datetime.now(TZ).date().isoformat())
    lo = max(START, (today - dt.timedelta(days=MAX_AGE_DAYS)).isoformat())
    return [d for d in names if lo <= d <= today.isoformat() and f"video:{d}" not in state]


def send_videos(token, chat, state, forced):
    for date in video_candidates(state, forced):
        key = f"video:{date}"
        if key in state:
            log(f"{date}: video allaqachon yuborilgan ({state[key].get('sent_at')}).")
            continue
        try:
            meta = json.loads((VIDEOS / f"{date}.json").read_text(encoding="utf-8"))
        except ValueError as e:
            return fail(f"{date}: telegram/videos/{date}.json o'qilmadi — {e}.")
        rel = (meta.get("video") or "").strip()
        video = find_video(rel) if rel else None
        if not video:
            log(f"::warning::{date}: video fayli ({rel or '—'}) hali repoda yo'q — keyingi safar yuboriladi.")
            summary(f"⏳ {date}: video fayli hali repoda yo'q ({rel}).")
            continue
        size = video.stat().st_size
        if size > 50 * 1024 * 1024:
            return fail(f"{date}: video {size // (1024 * 1024)} MB — Telegram bot chegarasi 50 MB.")
        text = (meta.get("text") or "").strip()
        with tempfile.TemporaryDirectory() as tmp:
            covers = make_covers(video, meta.get("cover_at"), tmp)
            try:
                ids, text_separately = send_video(token, chat, video, text, meta, covers)
            except TelegramError as e:
                return fail(f"{date}: video — Telegram xatosi {e.code} — {e.desc}. {hint(e)}".strip())
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                return fail(f"{date}: video — Telegram'ga ulanib bo'lmadi — {e}.")
        state[key] = {"sent_at": dt.datetime.now(TZ).isoformat(timespec="seconds"), "chat": chat,
                      "video": str(video.relative_to(ROOT)), "message_ids": ids}
        save_state(state)
        if text_separately:
            try:
                msg = call(token, "sendMessage", {
                    "chat_id": chat, "text": text,
                    "link_preview_options": json.dumps({"is_disabled": True})})
            except (TelegramError, urllib.error.URLError, TimeoutError, OSError) as e:
                return fail(f"{date}: video yuborildi, lekin matn yuborilmadi — {e}.")
            state[key]["message_ids"].append(msg["message_id"])
            save_state(state)
        log(f"{date}: video yuborildi -> {chat} ({video.name}, {size // 1024} KB)")
        summary(f"✅ {date}: video «{meta.get('topic', video.name)}» {chat} kanaliga yuborildi.")
    return 0


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
            if forced and not (VIDEOS / f"{date}.json").exists():
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
    return send_videos(token, chat, state, forced)


if __name__ == "__main__":
    sys.exit(main())
