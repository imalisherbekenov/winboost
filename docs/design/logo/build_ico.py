"""Собирает многоразмерный WinBoost.ico из геометрии знака.

Знак — ломаная на сетке 24x24, та же что в mark.svg. Растеризатор SVG не нужен:
рисуем примитивами Pillow с четырёхкратным суперсэмплингом.

Штрих утолщается к мелким размерам, а не масштабируется: на 16 пикселях
пропорциональный штрих истончается до каши.
"""
from pathlib import Path

from PIL import Image, ImageDraw

# Вершины знака в долях от стороны. Центр поднят выше плеч — это и есть «boost».
VERTICES = [
    (0.200, 0.3333),
    (0.3667, 0.7500),
    (0.500, 0.2292),
    (0.6333, 0.7500),
    (0.800, 0.3333),
]

# На каждый размер: толщина штриха, радиус подложки, растяжение глифа.
#
# Мелкие размеры получают не более толстый штрих, а более крупный глиф.
# Толстый штрих на 16px закрывает просветы между линиями, и знак сползает
# в чёрное пятно; вместо этого раздвигаем вершины к краям подложки, чтобы
# при тонком штрихе просветы остались открытыми.
PROFILE = {
    16: (0.105, 0.10, 1.30),
    24: (0.100, 0.11, 1.22),
    32: (0.098, 0.12, 1.20),
    48: (0.098, 0.12, 1.10),
    64: (0.100, 0.125, 1.05),
    128: (0.103, 0.125, 1.00),
    256: (0.105, 0.125, 1.00),
}

SS = 4  # суперсэмплинг
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


def render(size: int) -> Image.Image:
    stroke_ratio, radius_ratio, spread = PROFILE[size]
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [(0, 0), (big - 1, big - 1)],
        radius=radius_ratio * big,
        fill=WHITE,
    )

    # Растягиваем от центра подложки, сохраняя пропорции знака.
    points = [
        ((0.5 + (x - 0.5) * spread) * big, (0.5 + (y - 0.5) * spread) * big)
        for x, y in VERTICES
    ]
    width = max(1, round(stroke_ratio * big))

    # joint="curve" сглаживает стыки; кружки на вершинах дают скруглённые концы,
    # которых у Pillow нет из коробки.
    draw.line(points, fill=BLACK, width=width, joint="curve")
    r = width / 2
    for x, y in points:
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=BLACK)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    out_dir = Path(__file__).parent
    sizes = sorted(PROFILE)
    frames = [render(s) for s in sizes]

    for size, frame in zip(sizes, frames):
        frame.save(out_dir / f"icon-{size}.png")

    ico_path = out_dir / "WinBoost.ico"
    frames[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"{ico_path}  ({ico_path.stat().st_size} байт, размеры: {sizes})")


if __name__ == "__main__":
    main()
