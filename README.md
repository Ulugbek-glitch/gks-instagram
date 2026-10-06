# GKS Academics — Instagram avtopost (Claude + Zapier, bepul)

Claude har 2 kunda (oyiga ko'pi bilan 15 ta) GKS Academics uchun post yozadi, rasmini yasaydi
va Zapier orqali Instagram'ga o'zi joylaydi.

## Qanday ishlaydi

```
Claude rejali vazifasi (har toq kuni, Toshkent vaqti ~19:00)
   │  1. post matnini yozadi (posts/SANA/post.json)
   │  2. Zapier → GitHub: post.json ni shu repoga qo'shadi
   ▼
GitHub Actions (.github/workflows/render.yml)
   │  3. render.py bilan karusel rasmlarini yasaydi va repoga qo'shadi
   ▼
Claude
   │  4. Zapier → Instagram: rasmlar havolasi + izoh
   ▼
Instagram profili
```

Nega GitHub? Instagram rasmni fayl sifatida emas, internetdagi **ochiq havola** orqali oladi.
Ochiq repodagi rasmlar `raw.githubusercontent.com` havolasiga ega bo'ladi.

## Narxi — 0 so'm
| Xizmat | Bepul limit | Bizga kerak |
|---|---|---|
| Zapier Free | 100 task / oy | 15 post × 4 task = 60 task |
| GitHub (ochiq repo + Actions) | cheksiz | ~15 MB / oy |
| Claude | mavjud obunangiz | — |

Zapier'dagi boshqa Zap'lar ham shu 100 task limitidan foydalanadi.

## O'rnatish (bir marta)

### 1. Instagram → Business akkaunt
Zapier faqat **Business** akkaunt bilan ishlaydi (Personal ham, Creator ham emas).
Instagram ilovasi → Profil → ☰ → **Account type and tools** → **Switch to professional account** →
kategoriya: *Education* → **Business**. Akkaunt Creator bo'lsa: shu menyuda **Switch to business account**.

### 2. Facebook sahifa yaratish va Instagram'ni ulash
1. facebook.com/pages/create → nomi: *GKS Academics*, kategoriya: *Education* → Create.
2. Instagram → **Edit profile** → *Public business information* → **Page** → sahifani tanlang.
   Siz shu sahifaning admini bo'lishingiz shart.

### 3. Zapier'da Instagram va GitHub'ni ulash
Claude bergan ikkita Zapier havolasini oching:
- **Instagram for Business** — Facebook bilan kiring, sahifa va Instagram'ni belgilang, ruxsat bering.
- **GitHub** — GitHub bilan kiring va Zapier'ga ruxsat bering.

### 4. Fayllarni repoga yuklash (bir marta)
`gks-instagram` papkasini (zip) yuklab oling, oching va Terminal'da:
```bash
cd ~/Downloads/gks-instagram
git push https://Ulugbek-glitch:TOKEN@github.com/Ulugbek-glitch/gks-instagram.git main
```
`TOKEN` — siz yaratgan `github_pat_...`. Push'dan keyin bu token kerak emas:
GitHub → Settings → Developer settings → Fine-grained tokens → **Delete**.

### 5. Claude'ga xabar bering
Claude Instagram akkaunt ID sini topadi, (ruxsatingiz bilan) bitta test post qiladi va rejali vazifani yoqadi.

## Boshqarish
- **To'xtatish:** Claude ilovasi → Scheduled tasks → vazifani o'chiring (yoki Claude'ga ayting).
- **Mavzular, ohang:** `content/plan.md`.
- **Faktlar:** raqam/sanalar faqat `content/facts.md` ning "Tasdiqlangan" bo'limidan olinadi.
- **Logo:** `assets/logo_light.png` (to'q fon uchun) va `assets/logo_dark.png` (och fon uchun) qo'shsangiz,
  yozuv o'rniga logo chiqadi. **Instagram nomi:** `brand.json` → `handle`.
- **Ish tartibi:** `AGENT.md` — Claude har safar shu faylga qarab ishlaydi.

## Muammolar
| Belgi | Sabab / yechim |
|---|---|
| Zapier'da Instagram akkaunt ko'rinmaydi | Akkaunt Business emas yoki Facebook sahifaga ulanmagan (1–2 qadam) |
| "permission" xatosi | Zapier'da Instagram ulanishini qayta ulang, barcha ruxsatlarni bering |
| Rasmlar yasalmadi | Repo → **Actions** bo'limida "Render post images" xatosini ko'ring |
| Post chiqmadi, xato yo'q | Instagram'da paydo bo'lishi bir necha daqiqa olishi mumkin |
| Zapier task tugadi | Oyiga 100 task; boshqa Zap'lar ham shu limitdan foydalanadi |
