#!/usr/bin/env python3
"""Post slaydlarini bitta kichik rasmga yig'adi (tekshirish uchun).
Foydalanish: python3 preview.py posts/2026-10-09   ->  posts/2026-10-09/_preview.png (gitga kirmaydi)
"""
import sys
from pathlib import Path
from PIL import Image

folder = Path(sys.argv[1])
files = sorted(folder.glob("[0-9][0-9].jpg"))
w, h, cols = 360, 450, 3
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (w + 10) + 10, rows * (h + 10) + 10), "#888888")
for k, f in enumerate(files):
    sheet.paste(Image.open(f).resize((w, h)), (10 + (k % cols) * (w + 10), 10 + (k // cols) * (h + 10)))
out = folder / "_preview.png"
sheet.save(out)
print(out)
