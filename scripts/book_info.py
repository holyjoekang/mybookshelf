"""카카오 책 검색으로 책 정보(표지 썸네일·소개글 등)를 받아 data/book_info/ 에 책마다 json으로 저장한다.

책 추가는 텍스트로 한다. 한 줄에 한 권, 저자를 붙이려면 "제목 / 저자".
추가한 책은 data/books.json 에도 들어가 앱 목록에 보인다 (python scripts/build_app.py 로 다시 빌드).
    python scripts/book_info.py "협상의 법칙" "데미안 / 헤세"   # 인자로
    python scripts/book_info.py < titles.txt                     # 텍스트 파일로
    python scripts/book_info.py                                  # 직접 입력 (빈 줄로 끝)
    python scripts/book_info.py --all                            # 등록된 모든 책의 정보 받기
환경변수 KAKAO_REST_API_KEY 필요. 이미 받은 책은 건너뛴다.
결과: data/book_info/<제목>.json, <제목>.jpg
"""

import datetime, json, os, re, sys, time
from pathlib import Path

import requests

OUT = Path("data/book_info")
BOOKS = Path("data/books.json")
MEMORY = Path("data/memory_books.json")


def parse_line(line: str) -> tuple[str, str | None] | None:
    line = line.lstrip("\ufeff")  # 메모장·PowerShell이 붙이는 BOM 제거
    # '제목 / 저자'. 『12 1/2 …』처럼 제목 안의 빗금(뒤가 숫자)은 나누지 않는다
    m = re.search(r"\s+/\s+", line) or re.search(r"/(?!\d)", line)
    title, author = (line[:m.start()], line[m.end():]) if m else (line, "")
    title, author = title.strip(), author.strip() or None
    return (title, author) if title else None


def slug(title: str) -> str:
    return re.sub(r"[^\w가-힣]+", "_", title).strip("_")


def norm(s: str) -> str:
    return re.sub(r"[^\w가-힣]", "", s).lower()


def pick(docs: list[dict], title: str | None = None, author: str | None = None) -> dict | None:
    # 제목이 우리 제목으로 시작하고("신" 검색에 "홍보의 신" 방지) 저자도 맞는 판본을 먼저 본다.
    # 둘 다 맞는 게 없으면 저자가 맞는 판본, 그다음 제목이 맞는 판본, 그것도 없으면 전부.
    tm = [d for d in docs if title and norm(d["title"]).startswith(norm(title))]
    am = [d for d in docs if author and any(norm(author) in norm(x) or norm(x) in norm(author)
                                            for x in d["authors"] if x)]
    docs = [d for d in tm if d in am] or am or tm or docs
    # 첫 결과는 소개글이 빈 판본인 경우가 많아, 소개글과 표지가 있는 첫 판본을 고른다.
    return next((d for d in docs if d.get("contents") and d.get("thumbnail")), docs[0] if docs else None)


def search(title: str, author: str | None, key: str) -> dict | None:
    docs = []
    # 제목으로 찾고, 저자를 알면 "제목 저자"로도 찾아 합친다(짧은 제목은 제목 검색만으로는 묻힌다).
    for params in [{"query": title, "target": "title"}] + ([{"query": f"{title} {author}"}] if author else []):
        r = requests.get("https://dapi.kakao.com/v3/search/book", params={**params, "size": 20},
                         headers={"Authorization": f"KakaoAK {key}"}, timeout=20)
        r.raise_for_status()
        docs += r.json().get("documents") or []
    d = pick(docs, title, author)
    if not d:
        return None
    return {
        "query": title,
        "title": d["title"],
        "authors": d["authors"],
        "translators": d["translators"],
        "publisher": d["publisher"],
        "pubdate": d["datetime"][:10],
        "isbn": d["isbn"].split()[-1] if d["isbn"] else None,
        "contents": d["contents"],
        "thumbnail": d["thumbnail"],
        "url": d["url"],
    }


def fetch(title: str, author: str | None, key: str) -> str:
    """책 정보를 받아 json·표지로 저장한다. 연결이 끊기면 두 번 더 해 보고, 그래도 안 되면 이 책만 건너뛴다."""
    for wait in (2, 5, None):
        try:
            return _fetch(title, author, key)
        except requests.RequestException as e:
            if wait is None:
                return f"건너뜀 {title} ({type(e).__name__})"
            time.sleep(wait)


def _fetch(title: str, author: str | None, key: str) -> str:
    path = OUT / f"{slug(title)}.json"
    if path.exists():
        return f"있음 {title}"
    info = search(title, author, key)
    if not info:
        return f"못 찾음 {title}"
    OUT.mkdir(parents=True, exist_ok=True)
    if info["thumbnail"]:
        raw = requests.get(info["thumbnail"], timeout=30).content
        # 그림 파일일 때만 표지로 쓴다(서버가 오류 페이지를 돌려주는 때가 있다)
        if raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:4] == b"GIF8" or raw[8:12] == b"WEBP":
            img = path.with_suffix(".jpg")
            img.write_bytes(raw)
            info["cover"] = img.name
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"저장 {title}"


def add(line: str, key: str) -> str:
    """텍스트 한 줄로 책을 서재(books.json)에 추가하고 정보를 받는다."""
    parsed = parse_line(line)
    if not parsed:
        return "skip"
    title, author = parsed
    data = json.loads(BOOKS.read_text(encoding="utf-8"))
    msg = fetch(title, author, key)
    if any(b["title"] == title for b in data["books"]):
        return msg + " (이미 서재에 있음)"
    info_path = OUT / f"{slug(title)}.json"
    if not author and info_path.exists():
        author = (json.loads(info_path.read_text(encoding="utf-8"))["authors"] or [None])[0]
    d = datetime.date.today()
    data["books"].append({"title": title, "author": author, "sources": ["input"], "reviews": [],
                          "photos": [], "firstReadDate": f"{d.year}. {d.month}. {d.day}.",
                          "needsReview": False})
    BOOKS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return msg + " + 서재에 추가"


def all_titles() -> list[tuple[str, str | None]]:
    """서재에 등록된 모든 책. 기억 목록은 제목까지 기억나는 책만."""
    books = [(b["title"], b["author"]) for b in json.loads(BOOKS.read_text(encoding="utf-8"))["books"]]
    if MEMORY.exists():
        books += [(m["t"], m.get("a")) for m in json.loads(MEMORY.read_text(encoding="utf-8"))["books"]
                  if m["kind"] == "title"]
    return books


def main() -> None:
    key = os.environ.get("KAKAO_REST_API_KEY") or sys.exit("KAKAO_REST_API_KEY 가 없습니다.")
    if sys.argv[1:] == ["--all"]:
        books = all_titles()
        for n, (t, a) in enumerate(books, 1):
            print(f"[{n}/{len(books)}] {fetch(t, a, key)}")
            time.sleep(0.1)
        print(f"정보 {len(list(OUT.glob('*.json')))}/{len(books)}권 -> {OUT}")
        return
    if sys.argv[1:]:
        lines = sys.argv[1:]
    elif sys.stdin.isatty():
        print("책 제목을 한 줄에 하나씩 입력하세요 (저자는 '제목 / 저자'). 빈 줄이면 끝.")
        lines = iter(lambda: input("> "), "")
    else:
        lines = sys.stdin.read().splitlines()
    for line in lines:
        if line.strip():
            print(add(line, key))


if __name__ == "__main__":
    main()
