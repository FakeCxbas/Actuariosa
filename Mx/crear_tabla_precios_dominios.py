from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).with_name("actuariosa-precios-dominios.png")
W, H = 1440, 1800
NAVY = "#123B76"
BLUE = "#0D5BAA"
RED = "#E43A3A"
INK = "#18233B"
MUTED = "#61708A"
BG = "#F5F8FC"
WHITE = "#FFFFFF"
PALE = "#EAF3FF"
HIGHLIGHT = "#FFF3E8"
GRID = "#D9E2EF"

font_dir = Path("C:/Windows/Fonts")
bold = str(font_dir / "arialbd.ttf")
regular = str(font_dir / "arial.ttf")
fonts = {
    "title": ImageFont.truetype(bold, 56),
    "subtitle": ImageFont.truetype(regular, 25),
    "header": ImageFont.truetype(bold, 23),
    "cell": ImageFont.truetype(regular, 23),
    "cell_bold": ImageFont.truetype(bold, 23),
    "note": ImageFont.truetype(regular, 21),
    "note_bold": ImageFont.truetype(bold, 21),
}

rows = [
    ("actuariosa.com", "Ya registrado", "USD 0 hasta mar. 2027", "Actual"),
    ("actuariosa.ec", "USD 40,25", "USD 40,25", "NIC.EC"),
    ("actuariosa.com.ec", "USD 40,25", "USD 40,25", "NIC.EC"),
    ("actuariosa.net", "USD 11,86", "USD 11,86", "Cloudflare"),
    ("actuariosa.org", "USD 8,50", "USD 11,20", "Cloudflare"),
    ("actuariosa.pro", "USD 21,20", "USD 21,20", "Cloudflare"),
    ("actuariosa.consulting", "USD 42,20", "USD 42,20", "Cloudflare"),
    ("actuariosa.co", "USD 30,00", "USD 30,00", "Cloudflare"),
    ("actuariosa.app", "USD 14,20", "USD 14,20", "Cloudflare"),
    ("actuariosa.dev", "USD 12,20", "USD 12,20", "Cloudflare"),
    ("actuariosa.services", "USD 30,20", "USD 30,20", "Cloudflare"),
    ("actuariosa.group", "USD 20,20", "USD 20,20", "Cloudflare"),
    ("actuariosa.site", "USD 4,99", "USD 27,70", "Cloudflare"),
    ("actuariosa.online", "USD 4,99", "USD 27,70", "Cloudflare"),
]

image = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(image)

draw.rounded_rectangle((58, 50, W - 58, 225), radius=28, fill=NAVY)
draw.text((100, 82), "Dominios para Actuariosa", font=fonts["title"], fill=WHITE)
draw.text((102, 155), "Precios anuales en USD · revisados el 9 de septiembre de 2026", font=fonts["subtitle"], fill="#D7E6FF")

x0, x1 = 58, W - 58
y = 275
row_h = 76
columns = [x0, 510, 790, 1090, x1]
headers = ["Dominio", "Registro", "Renovación", "Proveedor"]

draw.rounded_rectangle((x0, y, x1, y + row_h), radius=16, fill=BLUE)
for i, label in enumerate(headers):
    draw.text((columns[i] + 24, y + 23), label, font=fonts["header"], fill=WHITE)
y += row_h

for idx, row in enumerate(rows):
    recommended = row[0] in {"actuariosa.ec", "actuariosa.com.ec"}
    fill = HIGHLIGHT if recommended else (WHITE if idx % 2 == 0 else PALE)
    draw.rectangle((x0, y, x1, y + row_h), fill=fill)
    draw.line((x0, y + row_h, x1, y + row_h), fill=GRID, width=2)
    for col in range(1, len(columns) - 1):
        draw.line((columns[col], y, columns[col], y + row_h), fill=GRID, width=1)
    for i, cell in enumerate(row):
        font = fonts["cell_bold"] if i == 0 or recommended else fonts["cell"]
        draw.text((columns[i] + 24, y + 23), cell, font=font, fill=INK)
    y += row_h

box_y = y + 45
draw.rounded_rectangle((x0, box_y, x1, box_y + 205), radius=20, fill=WHITE, outline=GRID, width=2)
draw.text((x0 + 35, box_y + 28), "Recomendación", font=fonts["note_bold"], fill=RED)
draw.text((x0 + 35, box_y + 72), "Mantener actuariosa.com como dominio principal.", font=fonts["note"], fill=INK)
draw.text((x0 + 35, box_y + 108), "Registrar actuariosa.ec y actuariosa.com.ec para proteger la marca en Ecuador.", font=fonts["note"], fill=INK)
draw.text((x0 + 35, box_y + 152), "Costo conjunto de ambas extensiones ecuatorianas: USD 80,50 al año.", font=fonts["note_bold"], fill=NAVY)

draw.text((x0, H - 72), "La disponibilidad y el precio final se confirman antes del pago. Cloudflare cobra tarifas de registro sin margen adicional.", font=fonts["note"], fill=MUTED)
image.save(OUT, optimize=True)
print(OUT)
