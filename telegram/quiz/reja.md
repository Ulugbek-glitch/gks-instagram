# GKS Academics Telegram — kunlik interaktiv postlar rejasi

Kanal: @gks_academic (t.me/gks_academic). Auditoriya: O‘zbekistondagi 16–24 yoshli GKS-U abituriyentlari.
Boshlangan: 2026-11-08. 2026-11-16 dan kanalga har kuni 20:00 (Toshkent) da koreys tili quizi avtomatik yuboriladi.

## 0. Hozirgi tartib — koreys tili quizlari (2026-11-16 dan)
Bu bo‘lim qolgan bo‘limlardan ustun. 15-noyabrgacha bo‘lgan eski reja (jadval, ruknlar, rasm kartochkalari, madaniyat va GKS taqvimi) git tarixida: commit 9b791ad, telegram/quiz/reja.md.
- Format: har kuni bitta Telegram quizi (to‘g‘ri javob va izoh bilan). So‘rovnoma va rasm yo‘q. Mavzu faqat koreys tili: 초급, 중급, 고급 so‘zlar, grammatika va so‘z tuzilishi.
- Vaqt: har kuni 20:00 Toshkent (24:00 Koreya). Yuboruvchi: telegram/quiz/send_quiz.py (telegram/send_post.py chaqiradi; 20:00 Toshkentdan oldin yubormaydi, kuniga bir marta).
- Ishga tushirish: cron-job.org har kuni 20:00 (Asia/Tashkent) da GitHub API orqali telegram.yml ni workflow_dispatch bilan ishga tushiradi (Ulugbek sozlaydi, token cron-job.org da saqlanadi). telegram.yml dagi "37 15 * * *" zaxira cron 4–8 soat kechikib, Toshkentda yarim tundan keyin ishlaydi — u quizni yubormaydi.
- Haftalik navbat: Du — 초급 · So‘z; Se — 초급 · Grammatika; Cho — 중급 · So‘z; Pa — 중급 · Grammatika; Ju — 고급 · Ibora yoki So‘z (관용구, kamroq ishlatiladigan so‘zlar); Sha — 고급 · Grammatika; Ya — So‘z tuzilishi (한자어 ildizlari, old va oxirgi qo‘shimchalar, qo‘shma so‘zlar; daraja navbat bilan 초급 → 중급 → 고급).
- Savol: bitta qator, qator tashlashsiz: «🇰🇷 DARAJA · TUR. Ko‘rsatma: koreyscha misol». Masalan: «🇰🇷 초급 · So‘z. Bo‘sh joyga mos so‘zni tanlang: 저는 지금 버스를 ___.» Ko‘rsatma va izoh o‘zbekcha; misol va variantlar koreyscha (ma’no so‘ralganda variantlar o‘zbekcha). Bo‘sh joy: so‘z yoki kelishik qo‘shimchasi uchun «___», grammatik shakl uchun «( )».
- Variantlar: 4 ta, faqat bittasi to‘g‘ri. Qolganlari o‘sha darajadagi real so‘z yoki shakl, lekin shu gapda grammatik yoki ma’no jihatdan to‘g‘ri kelmaydi. Ikkinchi variant ham to‘g‘ri bo‘lib qolishi mumkin bo‘lsa, vaziyatni savolda aniqlashtiring. To‘g‘ri javob o‘rni kecha bilan bir xil bo‘lmasin.
- Izoh (≤200 belgi): nega to‘g‘ri + 1–2 chalg‘ituvchi variant ma’nosi. Romanizatsiya shart emas (4-bo‘limdagi Hangul + romanizatsiya qoidasi bu quizlarga tegishli emas).
- Takrorlanmasin: quizzes.json va git tarixidagi oldingi so‘z, grammatika va iboralar.
- Tekshirish: har bir til faktini (ma’no, grammatik qoida, 한자 ma’nosi) kamida 2 ta ishonchli manbada (표준국어대사전, 국립국어원, darsliklar, ishonchli o‘quv saytlari) tasdiqlang; ikkilansangiz — boshqa misol oling.
- Bank: telegram/quiz/quizzes.json. Har payshanba 09:33 (Koreya) «GKS Telegram — haftalik quizlar» vazifasi keyingi 7 kunni qo‘shadi. Fayl matnida teskari chiziq (backslash) va qator tashlash bo‘lmasin.
- Jurnal: 2026-11-10 – 11-15 quizlari kanalga chiqmadi — zaxira cron Toshkent vaqti bilan 00:30–05:00 da ishladi va «Hali erta» deb to‘xtadi. 2026-11-15: Ulugbek mavzuni koreys tiliga o‘zgartirdi, 16–29-noyabr quizlari yozildi.

## 1. Nega va qanday
- Holat (8-noyabr): avtomatik kontent — Instagram karusellari (albom, oxiri Instagram havolasi bilan); 19-oktabrdan 3-noyabrgacha avtomatik postlar to‘xtab qolgan (Zapier limiti); bu kontentda quiz va so‘rovnoma yo‘q.
- Usullar: har kuni bitta interaktiv post (quiz yoki so‘rovnoma); doimiy ruknlar va vaqt; javob ertasi kuni (ochiq halqa); kun mavzusiga bog‘lash; natijani keyingi postda aytish; «Do‘stingizga yuboring» chaqirig‘i; izoh va reaksiyalar; oyiga bir jonli efir.

## 4. Umumiy qoidalar
- Telegram limitlari: savol ≤300 belgi, variant ≤100, 2–12 variant, izoh ≤200 belgi va ≤2 qator tashlash; rasm izohi ≤1024 belgi.
- Quiz: 4 ta real, ishonarli variant; to‘g‘ri javob o‘rni kecha bilan bir xil bo‘lmasin. So‘rovnoma: 3–5 variant, ko‘p tanlov faqat «qaysi kontent/mavzu» savollarida.
- Koreyscha: Hangul + qavs ichida Revised Romanization, masalan 수고하세요 (sugohaseyo).
- Til: adabiy o‘zbek tili (lotin), «siz»; o‘ va g‘ uchun ‘ (U+2018), tutuq belgisi ’ (U+2019). Ohang content/plan.md dagi kabi: kafolat, «100%», «eng zo‘r» yo‘q. Captionda ≤3 emoji va bitta chaqiriq.
- Faktlar: madaniyat/til faktlari, sana va raqamlar kamida 2 ta ishonchli manbada tasdiqlanadi, aks holda ishlatilmaydi. GKS raqamlari faqat content/facts.md («Tasdiqlangan») va content/growth.md (3-bo‘lim) dan; facts.md da «yozmang» deyilgan narsa yozilmaydi.
- Savol javobni oshkor qilmaydi.

## 7. Zaxira mavzular (madaniyat va GKS postlari uchun, quiz uchun emas)
- Iboralar: 잠깐만요, 실례합니다, 미안해요 / 죄송합니다, 진짜?, 대박, 아이고, 잘 지냈어요?, 고생했어요.
- Madaniyat: 첫눈 (birinchi qor), 한글 (yaratilishi va e’lon qilinishi), 설날 (2027 sanasini tekshiring), T-money, 기숙사 va 학식, 동아리 va MT.
- GKS savol (faqat tasdiqlangan): Universitet yo‘lida faqat bitta universitet tanlanadi; hujjatlar apostil yoki konsullik tasdig‘idan o‘tgan bo‘lishi kerak.
