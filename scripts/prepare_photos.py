"""책장 사진을 인식하기 좋은 크기로 줄인다.

원본 사진은 한 장에 2MB가 넘어 그대로 비전 모델에 넣기엔 크다.
가로 세로 긴 쪽을 1600px로 맞추고 품질 85로 다시 저장한다.

사용법: python scripts/prepare_photos.py [입력폴더] [출력폴더]
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

MAX_EDGE = 1600


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "pictures")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "data/photos_resized")
    dst.mkdir(parents=True, exist_ok=True)

    for path in sorted(src.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".heic", ".webp"}:
            continue
        with Image.open(path) as im:
            # 휴대폰 사진은 EXIF 회전 정보를 갖고 있어 그대로 열면 눕는다.
            im = ImageOps.exif_transpose(im).convert("RGB")
            before = im.size
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            out = dst / f"{path.stem}.jpg"
            im.save(out, "JPEG", quality=85)
        kb = out.stat().st_size // 1024
        print(f"{path.name}: {before[0]}x{before[1]} -> {im.size[0]}x{im.size[1]} ({kb}KB)")


if __name__ == "__main__":
    main()
