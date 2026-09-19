"""첫 화면에 쓸 그림을 원본 두 장에서 잘라 낸다.

원본: pictures/home_reader.webp (수채화 표지 그림), pictures/home_room.webp (열람실 그림)
결과: app/img/*.webp — build_app.py가 이 파일들을 index.html 안에 data URI로 박는다.

사용법: python scripts/crop_home_images.py
"""

from pathlib import Path

from PIL import Image

SRC = Path("pictures")
OUT = Path("app/img")

# (원본, 자를 곳(왼,위,오른,아래), 가로 크기, 품질)
CROPS = {
    # 사람과 강아지 — 첫 화면 인사말 옆. 오른쪽 끝의 원본 제목 글자는 잘라 낸다.
    "reader":       ("home_reader", (0, 8, 448, 620), 480, 68),
    # 열람실에서 책을 읽는 그림 — 도서관 디자인 안내 옆. 위아래의 원본 제목·본문은 잘라 낸다.
    "room":         ("home_room", (0, 250, 768, 1150), 470, 68),
    # 도서관 여섯 곳의 섬네일 — 첫 화면 띠와 설정의 디자인 카드에서 함께 쓴다.
    "lib-london":   ("home_reader", (30, 1256, 180, 1368), 190, 72),
    "lib-admont":   ("home_reader", (481, 1257, 577, 1367), 190, 72),
    "lib-trinity":  ("home_reader", (590, 1257, 686, 1367), 190, 72),
    "lib-portugal": ("home_reader", (693, 1257, 789, 1367), 190, 72),
    "lib-strahov":  ("home_reader", (795, 1257, 891, 1367), 190, 72),
    "lib-stuttgart":("home_reader", (897, 1257, 994, 1367), 190, 72),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, (src, box, width, q) in CROPS.items():
        with Image.open(SRC / f"{src}.webp") as im:
            crop = im.convert("RGB").crop(box)
        h = round(crop.height * width / crop.width)
        crop = crop.resize((width, h), Image.LANCZOS)
        path = OUT / f"{name}.webp"
        crop.save(path, "WEBP", quality=q, method=6)
        total += path.stat().st_size
        print(f"{path}  {crop.width}x{crop.height}  {path.stat().st_size // 1024}KB")
    print(f"합계 {total // 1024}KB")


if __name__ == "__main__":
    main()
