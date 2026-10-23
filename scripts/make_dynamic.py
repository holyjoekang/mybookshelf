"""앱을 동적으로 바꾼다: 책 데이터·표지·그림을 index.html 안에 박지 않고 파일로 두고, 앱이 fetch로 읽는다.

- app/index.template.html: 책 데이터를 data/library.json 에서 읽도록 시작부를 바꾼다
- scripts/build_app.py: library.json · covers/*.jpg 를 쓰고, 그림은 img/*.webp 를 가리키게 한다
한 번만 돌리면 되고, 다시 돌려도 같은 결과.
"""
from pathlib import Path

def patch(path: Path, old: str, new: str) -> None:
    t = path.read_text(encoding="utf-8")
    if new in t:
        return
    assert t.count(old) == 1, f"{path}: 바꿀 자리를 찾지 못함: {old[:60]}"
    path.write_text(t.replace(old, new), encoding="utf-8")

T = Path("app/index.template.html")
patch(T, '(function () {\n  "use strict";\n\n  var BOOKS = /*__BOOKS__*/[];',
      '(async function () {\n  "use strict";\n\n'
      '  // 책 데이터는 data/library.json 에서 읽는다(scripts/update_site.py 가 만든다). __VER__ 는 빌드 때 내용 해시로 바뀐다.\n'
      '  var BOOKS = await fetch("data/library.json?v=__VER__").then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; });')
# 데이터를 기다리는 사이 load 이벤트가 이미 지나갔을 수 있다
patch(T, '    addEventListener("load", function () { refit(); });',
      '    if (document.readyState === "complete") refit(); else addEventListener("load", function () { refit(); });')

B = Path("scripts/build_app.py")
patch(B, '"""data/books.json을 앱에 넣을 수 있게 압축해 index.html을 만든다.\n\napp/index.template.html 안의 /*__BOOKS__*/ 자리에 책 데이터를 끼워 넣는다.\n데이터를 파일로 따로 두면 아티팩트 CSP가 fetch를 막아 읽지 못하므로 인라인으로 박는다.\n\n사용법: python scripts/build_app.py\n결과: app/index.html\n"""',
      '"""data/books.json을 앱이 읽는 파일로 만든다(동적 사이트).\n\n'
      '앱(app/index.html)은 시작할 때 data/library.json 을 fetch 하고, 표지는 covers/<id>.jpg, 그림은 img/*.webp 를 읽는다.\n\n'
      '사용법: python scripts/build_app.py   (보통은 scripts/update_site.py 가 부른다)\n'
      '결과: app/index.html · app/data/library.json · app/covers/*.jpg\n"""')
patch(B, 'import base64\nimport io\nimport json\n', 'import hashlib\nimport io\nimport json\n')
patch(B, 'OUT = Path("app/index.html")', 'OUT = Path("app/index.html")\nLIBRARY = Path("app/data/library.json")\nCOVERS = Path("app/covers")')
patch(B, '''    """scripts/book_info.py가 받아 둔 표지·소개. 표지는 CSP 때문에 data URI로 박는다."""''',
      '''    """scripts/book_info.py가 받아 둔 표지·소개. 표지는 id가 정해진 뒤 covers/<id>.jpg 로 쓴다."""''')
patch(B, '''    if info.get("cover") and (INFO / info["cover"]).exists():
        with Image.open(INFO / info["cover"]) as im:
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=72, optimize=True)
        entry["cv"] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")''',
      '''    if info.get("cover") and (INFO / info["cover"]).exists():
        entry["cvsrc"] = str(INFO / info["cover"])''')
patch(B, '''def inline_images(html: str) -> tuple[str, int]:
    """템플릿의 __IMG_이름__ 자리에 app/img/이름.webp를 data URI로 박는다.

    표지와 같은 이유(아티팩트 CSP가 파일 읽기를 막는다)로 그림도 파일로 두지 않고 안에 넣는다.
    """''', '''def inline_images(html: str) -> tuple[str, int]:
    """템플릿의 __IMG_이름__ 자리를 app/img/이름.webp 를 가리키는 상대 경로로 바꾼다."""''')
patch(B, '''        uri = "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        html = html.replace(token, uri)''', '''        html = html.replace(token, f"img/{path.name}")''')
patch(B, '''    payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__BOOKS__*/[]", payload)
    html, img_bytes = inline_images(html)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")''', '''    # 표지: covers/<id>.jpg. 빠진 책의 옛 표지는 지운다.
    COVERS.mkdir(parents=True, exist_ok=True)
    keep = set()
    for b in compact:
        src = b.pop("cvsrc", None)
        if not src:
            continue
        dst = COVERS / f"{b['i']}.jpg"
        buf = io.BytesIO()
        with Image.open(src) as im:
            im.convert("RGB").save(buf, "JPEG", quality=72, optimize=True)
        if not dst.exists() or dst.read_bytes() != buf.getvalue():
            dst.write_bytes(buf.getvalue())
        b["cv"] = f"covers/{dst.name}?v={hashlib.md5(buf.getvalue()).hexdigest()[:8]}"
        keep.add(dst.name)
    for old in COVERS.glob("*.jpg"):
        if old.name not in keep:
            old.unlink()

    payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY.write_text(payload, encoding="utf-8")
    ver = hashlib.md5(payload.encode()).hexdigest()[:10]
    html = TEMPLATE.read_text(encoding="utf-8").replace("__VER__", ver)
    html, img_bytes = inline_images(html)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")''')
patch(B, '''    print(f"데이터 {len(payload) // 1024}KB · 첫 화면 그림 {img_bytes // 1024}KB / 전체 {OUT.stat().st_size // 1024}KB -> {OUT}")''',
      '''    print(f"데이터 {len(payload) // 1024}KB -> {LIBRARY} · 표지 {len(keep)}장 -> {COVERS}/ · 앱 {OUT.stat().st_size // 1024}KB -> {OUT}")''')
print("동적 전환 완료")
