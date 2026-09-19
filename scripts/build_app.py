"""data/books.json을 앱에 넣을 수 있게 압축해 index.html을 만든다.

app/index.template.html 안의 /*__BOOKS__*/ 자리에 책 데이터를 끼워 넣는다.
데이터를 파일로 따로 두면 아티팩트 CSP가 fetch를 막아 읽지 못하므로 인라인으로 박는다.

사용법: python scripts/build_app.py
결과: app/index.html
"""

import base64
import io
import json
import re
from pathlib import Path

from PIL import Image

from book_info import OUT as INFO, slug

BOOKS = Path("data/books.json")
CATEGORIES = Path("data/categories.json")
MEMORY = Path("data/memory_books.json")  # 블로그 이전 학창 시절 독서를 기억으로 복원한 목록
# 책 id 대장(제목 -> 번호). 앱은 사용자가 고친 내용을 이 번호("b"+번호)에 저장하므로,
# 책이 늘거나 제목이 바로잡혀 정렬 순서가 바뀌어도 번호는 그대로 가야 한다.
# 새 책은 끝 번호를 받고, 빠진 책의 번호는 다시 쓰지 않는다. 제목을 고칠 때는 이 대장의 키도 함께 고친다.
IDS = Path("data/book_ids.json")
TEMPLATE = Path("app/index.template.html")
IMG = Path("app/img")           # 첫 화면 그림(scripts/crop_home_images.py가 만든다)
OUT = Path("app/index.html")


def year_of(date: str | None) -> int | None:
    if not date:
        return None
    m = re.match(r"\s*(\d{4})", date)
    return int(m.group(1)) if m else None


def book_info(title: str) -> dict:
    """scripts/book_info.py가 받아 둔 표지·소개. 표지는 CSP 때문에 data URI로 박는다."""
    path = INFO / f"{slug(title)}.json"
    if not path.exists():
        return {}
    info = json.loads(path.read_text(encoding="utf-8"))
    entry = {"pb": info["publisher"] or None, "ds": info["contents"] or None,
             "au": (info["authors"] or [None])[0]}
    if info.get("cover") and (INFO / info["cover"]).exists():
        with Image.open(INFO / info["cover"]) as im:
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=72, optimize=True)
        entry["cv"] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return {k: v for k, v in entry.items() if v}


def inline_images(html: str) -> tuple[str, int]:
    """템플릿의 __IMG_이름__ 자리에 app/img/이름.webp를 data URI로 박는다.

    표지와 같은 이유(아티팩트 CSP가 파일 읽기를 막는다)로 그림도 파일로 두지 않고 안에 넣는다.
    """
    used = 0
    for path in sorted(IMG.glob("*.webp")):
        token = "__IMG_" + path.stem.replace("-", "_") + "__"
        if token not in html:
            continue
        uri = "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        html = html.replace(token, uri)
        used += path.stat().st_size
    left = re.search(r"__IMG_[a-z0-9_]+__", html)
    if left:
        raise SystemExit(f"그림을 찾지 못했습니다: {left.group(0)} (scripts/crop_home_images.py를 먼저 실행하세요)")
    return html, used


def assign_ids(books: list[dict], ids: dict[str, int]) -> list[str]:
    """책마다 대장의 번호를 "i"로 붙인다. 대장에 없는 책만 끝 번호를 새로 받고 대장에 적힌다.

    대장이 비어 있으면 지금 순서가 곧 번호다(예전 배열 순번 id와 같아진다). 새로 번호를 받은 제목을 돌려준다.
    """
    titles = [b["t"] for b in books]
    if len(set(titles)) != len(titles):
        raise SystemExit(f"제목이 겹치는 책이 있어 id를 매길 수 없습니다: {sorted({t for t in titles if titles.count(t) > 1})}")
    next_id = max(ids.values(), default=-1) + 1
    added = []
    for b in books:
        if b["t"] not in ids:
            ids[b["t"]] = next_id
            added.append(b["t"])
            next_id += 1
        b["i"] = ids[b["t"]]
    return added


def main() -> None:
    data = json.loads(BOOKS.read_text(encoding="utf-8"))
    cats = json.loads(CATEGORIES.read_text(encoding="utf-8"))
    missing_cat = [b["title"] for b in data["books"] if b["title"] not in cats]
    if missing_cat:
        print(f"경고: 분류 없는 책 {len(missing_cat)}권 -> {', '.join(missing_cat[:5])}")

    compact, typed = [], []
    for b in data["books"]:
        year = year_of(b.get("firstReadDate"))
        reviews = [
            {"d": r["date"].replace(" ", ""), "u": r["url"], "c": r["chars"]}
            for r in b["reviews"]
        ]
        entry = book_info(b["title"])
        # 우리가 이미 아는 저자가 있으면 그대로 두고, 모를 때만 검색 결과의 첫 저자를 쓴다.
        author = b["author"] or entry.pop("au", None)
        entry.pop("au", None)

        # 텍스트로 추가한 책은 맨 뒤에 붙이려고 따로 모은다(아래 기억 목록 주석 참고).
        (typed if b["sources"] == ["input"] else compact).append(
            {
                **entry,
                "t": b["title"],
                "a": author,
                "y": year,
                "c": cats.get(b["title"], "그 밖의 책"),
                "s": "".join(sorted(s[0] for s in b["sources"])),  # b / p / bp / i(텍스트로 추가)
                "r": reviews,
                "n": 1 if b["needsReview"] else 0,
            }
        )

    # 연도가 있는 책(블로그 기록)을 먼저 시간순으로, 사진에만 있는 책은 뒤에 제목순으로.
    compact.sort(key=lambda b: (b["y"] is None, b["y"] or 0, b["t"]))

    # 기억으로 복원한 책은 맨 뒤에 붙인다. 앱은 책 id를 배열 순번("b"+i)으로 매기고
    # 사용자가 고친 내용도 그 id에 저장되므로, 기존 책 사이에 끼우면 수정 기록이 엉뚱한 책에 붙는다.
    memory = json.loads(MEMORY.read_text(encoding="utf-8")) if MEMORY.exists() else {"books": []}
    by_title = {b["t"]: b for b in compact}
    added_memory = 0
    for m in memory["books"]:
        if m["kind"] == "existing":
            # 이미 서재에 있는 책은 새로 꽂지 않고 사연만 덧붙인다.
            target = by_title.get(m["t"])
            if target is None:
                print(f"경고: 기억 목록의 '{m['t']}'이(가) 서재에 없습니다")
                continue
            target["m"] = m["memo"]
            continue
        entry = {**(book_info(m["t"]) if m["kind"] == "title" else {}),
                 "t": m["t"], "a": m.get("a"), "y": None, "c": m["c"], "s": "m", "r": [],
                 # 서명까지 기억나지 않는 책은 '확인 필요'로 꽂아 두고 앱에서 고치게 한다.
                 "n": 0 if m["kind"] == "title" else 1,
                 "p": m["period"], "k": m["kind"]}
        if m.get("memo"):
            entry["m"] = m["memo"]
        entry.pop("au", None)
        compact.append(entry)
        added_memory += 1

    # 텍스트로 추가한 책은 추가한 순서대로 맨 끝에.
    compact += typed

    ids = json.loads(IDS.read_text(encoding="utf-8")) if IDS.exists() else {}
    new_ids = assign_ids(compact, ids)
    IDS.write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")

    payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__BOOKS__*/[]", payload)
    html, img_bytes = inline_images(html)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    dated = sum(1 for b in compact if b["y"])
    with_cover = sum(1 for b in compact if b.get("cv"))
    no_author = sum(1 for b in compact if not b["a"])
    print(f"책 {len(compact)}권 (연도 있음 {dated}, 기억으로 복원 {added_memory}, 텍스트로 추가 {len(typed)})")
    print(f"표지 {with_cover}권 · 소개 {sum(1 for b in compact if b.get('ds'))}권 · 저자 미상 {no_author}권")
    if new_ids:
        print(f"새 id {len(new_ids)}개: {', '.join(new_ids[:8])}{' …' if len(new_ids) > 8 else ''}")
    print(f"데이터 {len(payload) // 1024}KB · 첫 화면 그림 {img_bytes // 1024}KB / 전체 {OUT.stat().st_size // 1024}KB -> {OUT}")


if __name__ == "__main__":
    main()
