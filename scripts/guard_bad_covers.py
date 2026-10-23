"""표지 서버가 그림이 아닌 것을 돌려줘도 업데이트가 멈추지 않게 한다(한 번만, 다시 돌려도 같은 결과).
- book_info: 받은 내용이 JPEG·PNG·GIF·WEBP 가 아니면 표지 없이 정보만 저장한다
- build_app: 열 수 없는 표지 파일은 건너뛰고 경고만 남긴다"""
from pathlib import Path

S = Path(__file__).resolve().parent
def patch(name, old, new):
    p = S / name; t = p.read_text(encoding="utf-8")
    if new in t: return
    assert t.count(old) == 1, f"{name}: {old[:50]}"
    p.write_text(t.replace(old, new), encoding="utf-8")

patch("book_info.py", '''    if info["thumbnail"]:
        img = path.with_suffix(".jpg")
        img.write_bytes(requests.get(info["thumbnail"], timeout=30).content)
        info["cover"] = img.name''', '''    if info["thumbnail"]:
        raw = requests.get(info["thumbnail"], timeout=30).content
        # 그림 파일일 때만 표지로 쓴다(서버가 오류 페이지를 돌려주는 때가 있다)
        if raw[:3] == b"\\xff\\xd8\\xff" or raw[:8] == b"\\x89PNG\\r\\n\\x1a\\n" or raw[:4] == b"GIF8" or raw[8:12] == b"WEBP":
            img = path.with_suffix(".jpg")
            img.write_bytes(raw)
            info["cover"] = img.name''')
patch("build_app.py", '''        buf = io.BytesIO()
        with Image.open(src) as im:
            im.convert("RGB").save(buf, "JPEG", quality=72, optimize=True)''', '''        buf = io.BytesIO()
        try:
            with Image.open(src) as im:
                im.convert("RGB").save(buf, "JPEG", quality=72, optimize=True)
        except OSError:
            print(f"경고: 표지를 열 수 없어 건너뜀 {src}")
            continue''')
print("잘못된 표지 대비 완료")
