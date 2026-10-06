# Claude uchun ish tartibi — GKS Academics Instagram avtopost

Bu faylni rejali vazifa (scheduled task) har ishga tushganda o'qiydi va bajaradi.
Rejali vazifa promptida beriladi: `INSTAGRAM_PAGE_ID` va `GITHUB_REPO` (Zapier qiymati).

Umumiy oqim:
1. Claude `posts/DATE/post.json` ni yozadi va o'zida render qilib tekshiradi.
2. `post.json` ni Zapier (GitHub → create_file) orqali repoga qo'shadi.
3. GitHub Actions (`.github/workflows/render.yml`) rasmlarni yasab repoga qo'shadi.
4. Claude rasmlar paydo bo'lishini kutadi va Zapier (Instagram → publish_media_v2) orqali joylaydi.

Zapier byudjeti: har post = 2 ta chaqiruv = 4 task. Har chaqiruvni **faqat bir marta** qil.

## 0. Tayyorgarlik
```bash
git clone -q https://github.com/Ulugbek-glitch/gks-instagram.git && cd gks-instagram
DATE=$(TZ=Asia/Tashkent date +%F)
```

## 1. Himoya tekshiruvlari (birortasi bajarilsa — TO'XTA, hech narsa yozma va joylama)
- `posts/$DATE/post.json` allaqachon bor → bugungi post qilingan.
- Shu oyda (`posts/YYYY-MM-*`) 15 yoki undan ko'p post papkasi bor.

## 2. Kontekstni o'qi
- `content/plan.md` — auditoriya, ohang, mavzu ustunlari, formatlar.
- `content/facts.md` — postda ishlatish mumkin bo'lgan faktlar.
- Oxirgi 20 ta `posts/*/post.json` dagi `topic` va `pillar` — mavzu takrorlanmasin, ustunlar navbatlashsin.

## 3. Postni yoz → `posts/$DATE/post.json`
```json
{
  "date": "DATE",
  "topic": "bir qatorli mavzu",
  "pillar": "plan.md dagi ustun nomi",
  "slides": [
    {"type": "cover", "kicker": "QISQA YORLIQ", "title": "Sarlavha, *oltin so'z*", "subtitle": "1-2 gap"},
    {"type": "point", "title": "Fikr sarlavhasi", "body": "2-4 gap"},
    {"type": "list",  "title": "Ro'yxat sarlavhasi", "items": ["band", "band", "band"]},
    {"type": "stat",  "value": "3", "label": "nima soni", "note": "izoh"},
    {"type": "cta",   "title": "Yakuniy chaqiriq", "body": "1-2 gap", "button": "Tugma matni"}
  ],
  "caption": "Instagram izohi"
}
```
Qoidalar:
- Til: o'zbek (lotin). `o‘`, `g‘` va `’` belgilaridan foydalan.
- Format: odatda karusel — `cover` + 3–5 ta `point`/`list` + `cta` (jami 5–7 slayd, max 10).
  Ba'zan bitta slaydli post (`stat` yoki `cover`) ham bo'lishi mumkin.
- Slayd matni qisqa: sarlavha ≤ 8 so'z, `body` ≤ 45 so'z, `list` ≤ 6 band.
- `caption` ≤ 2200 belgi; oxirida 5–10 ta heshteg (max 30).
- **Faktlar:** raqam, sana, foiz, kvota, muddat — faqat `content/facts.md` ning "Tasdiqlangan" bo'limidan.
  U yerda yo'q bo'lsa — raqamsiz, umumiy maslahat yoz. "Tasdiqlash kutilmoqda" bo'limidagilarni ISHLATMA.
- Taqiqlar: "100% grant olasiz" kabi kafolatlar; o'ylab topilgan talaba hikoyalari yoki sharhlar;
  boshqa odamlarni ismi bilan tilga olish; boshqa tashkilot nomidan gapirish.

## 4. O'zingda render qilib tekshir (Zapier'ga yuborishdan OLDIN)
```bash
pip install -q pillow 2>/dev/null || true
python3 render.py posts/$DATE/post.json
python3 preview.py posts/$DATE
```
`posts/$DATE/_preview.png` ni Read bilan ko'r. Matn kesilgan, juda mayda yoki chalkash bo'lsa —
`post.json` ni tuzatib qayta render qil. Natija yaxshi bo'lguncha takrorla (bu bepul).

## 5. post.json ni repoga qo'sh (Zapier → GitHub)
1. `inspect_zapier_actions` (selected_api `GitHubCLIAPI`, action `create_file`).
2. `execute_zapier_write_action`:
   - `repo`: promptdagi `GITHUB_REPO`
   - `path`: `posts/DATE/post.json`
   - `message`: `post: DATE`
   - `content`: post.json ning to'liq matni
   - `branch`: `main`

## 6. Rasmlar tayyor bo'lishini kut (ko'pi bilan ~8 daqiqa)
```bash
N=$(python3 -c "import json;print(len(json.load(open('posts/$DATE/post.json'))['slides']))")
for i in $(seq 1 32); do
  git fetch -q origin main
  HAVE=$(git ls-tree --name-only origin/main "posts/$DATE/" | grep -c '/[0-9][0-9]\.jpg$')
  [ "$HAVE" -ge "$N" ] && break
  sleep 15
done
SHA=$(git rev-parse origin/main)
```
Havolalar (SHA bilan — kesh muammosi bo'lmaydi):
`https://raw.githubusercontent.com/Ulugbek-glitch/gks-instagram/$SHA/posts/$DATE/01.jpg` …
Har birini `curl -sfI` bilan tekshir (200). Rasmlar chiqmasa — joylama, hisobotda
"GitHub Actions rasmlarni yasamadi — repo → Actions bo'limini tekshiring" deb yoz.

## 7. Instagram'ga joyla (Zapier → Instagram)
1. `inspect_zapier_actions` (selected_api `InstagramBusinessCLIAPI`, action `publish_media_v2`).
2. `execute_zapier_write_action` — bir marta:
   - `instagramPageId`: promptdagi `INSTAGRAM_PAGE_ID`
   - `media`: yuqoridagi havolalar ro'yxati, slaydlar tartibida (01, 02, …)
   - `caption`: post.json dagi `caption`
3. Xato bo'lsa — qayta urinma.

## 8. Hisobot
Qisqa: sana, mavzu, slaydlar soni, natija (joylandi / xato va sababi).
Instagram ulanishi bilan bog'liq xato bo'lsa: "Zapier'da Instagram ulanishini yangilang" deb yoz.
