"""Generador de icono .ico nativo en Python puro (sin dependencias externas).
Crea un icono profesional con sobre azul de correo y tilde verde de verificación.
"""
from pathlib import Path
import struct
import zlib


def create_png_rgba(width: int, height: int, draw_fn) -> bytes:
    """Genera un archivo PNG válido en formato RGBA de 32 bits."""
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)  # Filter type: None
        for x in range(width):
            r, g, b, a = draw_fn(x, y, width, height)
            raw_rows.extend([r, g, b, a])
    
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xffffffff)
        return length + chunk_type + data + crc

    png_header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    idat = chunk(b"IDAT", zlib.compress(bytes(raw_rows), level=9))
    iend = chunk(b"IEND", b"")
    return png_header + ihdr + idat + iend


def draw_mail_badge(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    """Dibuja un icono estilizado: sobre azul elegante con sello verde de verificación."""
    nx = x / w
    ny = y / h
    bg = (0, 0, 0, 0)
    
    em_left, em_right = 0.10, 0.82
    em_top, em_bot = 0.24, 0.78
    
    bcx, bcy, brad = 0.75, 0.72, 0.22
    dist_badge = ((nx - bcx)**2 + (ny - bcy)**2)**0.5

    if dist_badge <= brad:
        if dist_badge > brad - 0.035:
            return (255, 255, 255, 255)
        def dist_to_segment(px, py, x1, y1, x2, y2):
            dx, dy = x2 - x1, y2 - y1
            l2 = dx*dx + dy*dy
            if l2 == 0:
                return ((px - x1)**2 + (py - y1)**2)**0.5
            t = max(0, min(1, ((px - x1)*dx + (py - y1)*dy) / l2))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            return ((px - proj_x)**2 + (py - proj_y)**2)**0.5

        d1 = dist_to_segment(nx, ny, 0.68, 0.72, 0.73, 0.78)
        d2 = dist_to_segment(nx, ny, 0.73, 0.78, 0.82, 0.66)
        if min(d1, d2) <= 0.032:
            return (255, 255, 255, 255)
        return (22, 163, 74, 255)

    if em_left <= nx <= em_right and em_top <= ny <= em_bot:
        flap_mid_x = (em_left + em_right) / 2
        flap_bot_y = 0.52
        border = 0.025
        if (nx - em_left < border or em_right - nx < border or 
            ny - em_top < border or em_bot - ny < border):
            return (30, 58, 138, 255)

        def dist_to_line(px, py, x1, y1, x2, y2):
            dx, dy = x2 - x1, y2 - y1
            t = max(0, min(1, ((px - x1)*dx + (py - y1)*dy) / (dx*dx + dy*dy)))
            return ((px - (x1 + t*dx))**2 + (py - (y1 + t*dy))**2)**0.5

        d_flap1 = dist_to_line(nx, ny, em_left, em_top, flap_mid_x, flap_bot_y)
        d_flap2 = dist_to_line(nx, ny, flap_mid_x, flap_bot_y, em_right, em_top)
        
        if min(d_flap1, d_flap2) <= 0.02:
            return (37, 99, 235, 255)

        slope1 = (flap_bot_y - em_top) / (flap_mid_x - em_left)
        in_flap = (ny < em_top + slope1 * (nx - em_left)) if nx < flap_mid_x else (ny < em_top + slope1 * (em_right - nx))
        
        if in_flap:
            grad = (ny - em_top) / (flap_bot_y - em_top)
            r = int(59 + (37 - 59) * grad)
            g = int(130 + (99 - 130) * grad)
            b = int(246 + (235 - 246) * grad)
            return (r, g, b, 255)
        else:
            return (240, 246, 255, 255)

    return bg


def generate_ico(output_path: Path):
    """Crea un archivo .ico con resoluciones estándar de Windows (256, 64, 48, 32, 16)."""
    sizes = [256, 64, 48, 32, 16]
    png_images = []
    
    for size in sizes:
        png_data = create_png_rgba(size, size, draw_mail_badge)
        png_images.append((size, png_data))
    
    header = struct.pack("<HHH", 0, 1, len(png_images))
    entries = []
    offset = 6 + 16 * len(png_images)
    
    for size, data in png_images:
        w_byte = 0 if size == 256 else size
        h_byte = 0 if size == 256 else size
        entry = struct.pack("<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, len(data), offset)
        entries.append(entry)
        offset += len(data)
    
    ico_bytes = header + b"".join(entries) + b"".join(data for _, data in png_images)
    output_path.write_bytes(ico_bytes)
    print(f"Icono ICO creado en: {output_path} ({len(ico_bytes):,} bytes)")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "mxcorreo.ico"
    generate_ico(out)
