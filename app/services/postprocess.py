"""图像后处理:Pillow 缩放、白底合成、九宫格拼接"""
from io import BytesIO

from PIL import Image


def _load(b: bytes) -> Image.Image:
    return Image.open(BytesIO(b)).convert("RGB")


def to_square_800(b: bytes, bg: str = "white") -> bytes:
    """等比缩放+居中到 800×800,白底(默认)。bg 可传 'white' 或 (r,g,b)"""
    img = _load(b)
    img.thumbnail((760, 760), Image.LANCZOS)  # 主体占 95%,留白边
    canvas = Image.new("RGB", (800, 800), bg)
    x = (800 - img.width) // 2
    y = (800 - img.height) // 2
    canvas.paste(img, (x, y))
    buf = BytesIO()
    canvas.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def make_grid(cells: list[bytes], cols: int = 3, gap: int = 10,
              max_height: int = 1200) -> bytes:
    """九宫格拼接:最多 9 格,宽 800、高 ≤ max_height 的 JPEG bytes"""
    cell = (800 - gap * (cols - 1)) // cols
    rows = (len(cells) + cols - 1) // cols
    height = min(rows * cell + (rows - 1) * gap, max_height)
    canvas = Image.new("RGB", (800, height), "white")
    for i, cb in enumerate(cells[: cols * rows]):
        img = _load(cb)
        img.thumbnail((cell - 4, cell - 4), Image.LANCZOS)
        r, c = divmod(i, cols)
        x = c * (cell + gap)
        y = r * (cell + gap)
        cell_canvas = Image.new("RGB", (cell, cell), "white")
        ox = (cell - img.width) // 2
        oy = (cell - img.height) // 2
        cell_canvas.paste(img, (ox, oy))
        canvas.paste(cell_canvas, (x, y))
    buf = BytesIO()
    canvas.save(buf, "JPEG", quality=90)
    return buf.getvalue()
