#!/usr/bin/env python3
"""GKS Academics — kunlik Telegram quiz.

telegram/quiz/quizzes.json dagi bugungi (Toshkent sanasi) savolni kanalga Telegram'ning o'z
quiz'i sifatida yuboradi: obunachi javobni bosgach, to'g'ri javob va izoh ko'rinadi.

quizzes.json:
    {"2026-11-09": {"question": "...", "options": ["...", "...", "...", "..."], "correct": 1,
                    "explanation": "..."}, ...}
    correct — to'g'ri variantning 0 dan boshlanadigan tartib raqami.
Limitlar: savol 1–300 belgi, 2–10 variant (har biri 1–100 belgi), izoh ≤200 belgi va ≤2 qator tashlash.

Ishga tushiruvchi: .github/workflows/telegram-quiz.yml (har kuni 20:30 Toshkent) yoki qo'lda.
Muhit: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (standart @gks_academic),
       QUIZ_DATE=YYYY-MM-DD — o'sha kungi quizni vaqtdan qat'i nazar yuboradi (ixtiyoriy),
       QUIZ_AFTER=HH:MM — bundan oldin avtomatik yubormaydi (standart 20:00),
       QUIZ_STATE — holat fayli (standart telegram/quiz/sent.json).
Holat kaliti "quiz:SANA" — bir kunda bir marta. Faqat standart kutubxona.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "quizzes.json"
STATE = Path(os.environ.get("QUIZ_STATE") or HERE / "sent.json")
TZ = dt.timezone(dt.timedelta(hours=5))  # Toshkent
NL = chr(10)


def log(msg):
    print(msg, flush=True)


def summary(msg):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + NL)


def u16(s):
    return len(s.encode("utf-16-le")) // 2


def check(q):
    """Telegram limitlarini tekshiradi. Muammo bo'lsa — uning matni, aks holda bo'sh qator."""
    opts = q.get("options") or []
    if not 1 <= u16(q.get("question", "")) <= 300:
        return "savol bo'sh yoki 300 belgidan uzun"
    if not 2 <= len(opts) <= 10:
        return "variantlar soni 2–10 bo'lishi kerak"
    if any(not 1 <= u16(o) <= 100 for o in opts):
        return "variantlardan biri bo'sh yoki 100 belgidan uzun"
    c = q.get("correct")
    if not isinstance(c, int) or isinstance(c, bool) or not 0 <= c < len(opts):
        return "correct (to'g'ri variant tartib raqami, 0 dan) noto'g'ri"
    ex = q.get("explanation", "")
    if u16(ex) > 200 or ex.count(NL) > 2:
        return "izoh 200 belgidan uzun yoki 2 tadan ortiq qator tashlash bor"
    return ""


def api(token, method, fields):
    base = os.environ.get("TELEGRAM_API", "https://api.telegram.org")
    req = urllib.request.Request(f"{base}/bot{token}/{method}", data=urllib.parse.urlencode(fields).encode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode() or "{}")
        except ValueError:
            data = {"description": str(e.reason)}
        data.setdefault("error_code", e.code)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram xatosi {data.get('error_code')}: {data.get('description')}")
    return data["result"]


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or "@gks_academic"
    forced = os.environ.get("QUIZ_DATE", "").strip()
    after = os.environ.get("QUIZ_AFTER", "").strip() or "20:00"
    now = dt.datetime.now(TZ)
    if forced:
        try:
            date = dt.date.fromisoformat(forced).isoformat()
        except ValueError:
            log(f"::error::QUIZ_DATE noto'g'ri: {forced!r} (YYYY-MM-DD ko'rinishida yozing).")
            return 1
    elif now.strftime("%H:%M") < after:
        log(f"Hali erta ({now:%H:%M} Toshkent): quiz {after} dan keyin yuboriladi.")
        return 0
    else:
        date = now.date().isoformat()

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    problems = {d: e for d, e in ((d, check(q)) for d, q in bank.items()) if e}
    for d, e in sorted(problems.items()):
        log(f"::warning::quizzes.json {d}: {e}")
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    key = f"quiz:{date}"
    if key in state:
        log(f"{date}: quiz allaqachon yuborilgan ({state[key].get('sent_at')}).")
        return 0
    q = bank.get(date)
    if not q:
        log(f"::warning::{date}: quizzes.json da bu sana uchun savol yo'q.")
        summary(f"⚠️ {date}: quiz yo'q — telegram/quiz/quizzes.json ni to'ldiring.")
        return 0
    if date in problems:
        summary(f"❌ {date}: {problems[date]} — quiz yuborilmadi.")
        return 1
    if not token:
        log("::warning::TELEGRAM_BOT_TOKEN secret yo'q — quiz yuborilmadi.")
        return 0

    fields = {"chat_id": chat, "question": q["question"], "type": "quiz", "is_anonymous": "true",
              "options": json.dumps([{"text": o} for o in q["options"]], ensure_ascii=False),
              "correct_option_id": q["correct"]}
    if q.get("explanation"):
        fields["explanation"] = q["explanation"]
    try:
        msg = api(token, "sendPoll", fields)
    except (RuntimeError, urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"::error::{date}: quiz yuborilmadi — {e}")
        summary(f"❌ {date}: quiz yuborilmadi — {e}")
        return 1
    state[key] = {"sent_at": now.isoformat(timespec="seconds"), "chat": chat,
                  "message_id": msg.get("message_id")}
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + NL, encoding="utf-8")
    log(f"{date}: quiz yuborildi -> {chat}")
    summary(f"✅ {date}: quiz {chat} kanaliga yuborildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
