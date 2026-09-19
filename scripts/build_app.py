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
TEMPLATE = Path("app/index.template.html")
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

    # 텍스트로 추가한 책은 추가한 순서대로 맨 끝에. 그래야 기존 책의 id가 밀리지 않는다.
    compact += typed

    payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__BOOKS__*/[]", payload)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    dated = sum(1 for b in compact if b["y"])
    with_cover = sum(1 for b in compact if b.get("cv"))
    no_author = sum(1 for b in compact if not b["a"])
    print(f"책 {len(compact)}권 (연도 있음 {dated}, 기억으로 복원 {added_memory}, 텍스트로 추가 {len(typed)})")
    print(f"표지 {with_cover}권 · 소개 {sum(1 for b in compact if b.get('ds'))}권 · 저자 미상 {no_author}권")
    print(f"데이터 {len(payload) // 1024}KB / 전체 {OUT.stat().st_size // 1024}KB -> {OUT}")


if __name__ == "__main__":
    main()
