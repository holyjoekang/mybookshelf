"""서재 사이트를 한 번에 최신으로: 블로그 새 글 → 책 판정 → 서재 데이터 → 카카오 표지·소개 → 앱 파일.

1) fetch_blog_posts.py / fetch_blog_bodies.py 로 '독서,책' 카테고리 새 글을 받는다
2) 아직 판정하지 않은 글을 제목으로 판정해 data/extracted/batch_auto.json 에 적는다
   - 『책 제목』 이 있으면 그 책, '[독서노트] 제목 #태그' 꼴이면 제목, 아니면 책 글이 아님
   - 판정이 틀리면 batch_auto.json 을 고치고 다시 돌리면 된다(이미 적힌 글은 다시 판정하지 않는다)
3) data/books.json 에 새 독후감을 덧붙이고(기존 책·수정은 그대로), 새 책의 분류를 해시태그로 정한다
4) KAKAO_REST_API_KEY 가 있으면 book_info.py 로 표지·소개가 없는 책을 받는다(--covers 로 표지만 없는 책도)
5) build_app.py 로 app/data/library.json · app/covers/ · app/index.html 을 만든다

사용법: python scripts/update_site.py [--no-fetch] [--covers]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))
from merge_extracted import normalize  # noqa: E402
from book_info import OUT as INFO, slug  # noqa: E402

POSTS, BODIES, BOOKS = Path("data/blog_posts.json"), Path("data/blog_bodies.json"), Path("data/books.json")
EXTRACTED, AUTO, CATS = Path("data/extracted"), Path("data/extracted/batch_auto.json"), Path("data/categories.json")
# 해시태그·글 제목의 낱말 → 서재 분류. 앞에 있을수록 먼저 고른다.
CAT_HINTS = [
    ("소설·문학", ["노벨문학상", "소설", "문학", "시집", "시인"]), ("자기계발", ["자기계발", "습관", "모닝", "성공"]),
    ("경영·경제", ["경영", "경제", "투자", "마케팅", "리더십"]), ("과학·기술·AI", ["AI", "인공지능", "과학", "기술"]),
    ("인문·철학", ["인문", "철학", "역사"]), ("신앙·종교", ["신앙", "성경", "기독교"]), ("심리", ["심리"]),
    ("사회·트렌드", ["트렌드", "사회"]), ("중국·일본", ["중국", "일본"]), ("인생·에세이", ["에세이", "50플러스", "인생"]),
]


def run(*args: str) -> None:
    print("$", " ".join(args))
    subprocess.run([sys.executable, *args], check=True)


def verdict(title: str) -> dict:
    m = re.search(r"『([^』]+)』", title)
    if m:
        au = re.search(r"([가-힣A-Za-z·]+(?: [가-힣A-Za-z·]+)?)의\s*『", title)
        return {"isBook": True, "bookTitle": m.group(1).strip(), "author": au.group(1) if au else None}
    m = re.match(r"\s*\[독서노트\]\s*(.+?)\s*(?:#|$)", title)
    if m:
        return {"isBook": True, "bookTitle": m.group(1).strip(), "author": None}
    return {"isBook": False, "reason": "자동 판정: 제목에 책 표기(『』, [독서노트]) 없음"}


def judge_new_posts() -> list[str]:
    done = {v["logNo"] for f in EXTRACTED.glob("batch*.json") for v in json.loads(f.read_text(encoding="utf-8"))}
    auto = json.loads(AUTO.read_text(encoding="utf-8")) if AUTO.exists() else []
    posts = json.loads(POSTS.read_text(encoding="utf-8"))["posts"]
    new = [p for p in posts if p["logNo"] not in done]
    for p in new:
        auto.append({"logNo": p["logNo"], **verdict(p["title"])})
        print(f"  판정: {p['title'][:50]} -> {auto[-1].get('bookTitle') or '책 아님'}")
    if new:
        AUTO.write_text("[\n" + ",\n".join(json.dumps(v, ensure_ascii=False) for v in auto) + "\n]\n", encoding="utf-8")
    return [p["logNo"] for p in new]


def add_reviews() -> list[str]:
    """books.json 에 판정된 독후감 중 아직 없는 것만 덧붙인다. 새로 생긴 책 제목을 돌려준다."""
    bodies = json.loads(BODIES.read_text(encoding="utf-8"))
    data = json.loads(BOOKS.read_text(encoding="utf-8"))
    by_key = {normalize(b["title"]): b for b in data["books"]}
    have = {r["logNo"] for b in data["books"] for r in b["reviews"]}
    verdicts = [v for f in sorted(EXTRACTED.glob("batch*.json")) for v in json.loads(f.read_text(encoding="utf-8"))]
    created = []
    for v in verdicts:
        post = bodies.get(v["logNo"])
        if not v.get("isBook") or v["logNo"] in have or post is None:
            continue
        key = normalize(v["bookTitle"])
        b = by_key.get(key)
        if b is None:
            b = by_key[key] = {"title": v["bookTitle"], "author": v.get("author"), "sources": [], "reviews": [], "photos": []}
            data["books"].append(b); created.append(b["title"])
        if not b["author"] and v.get("author"):
            b["author"] = v["author"]
        if "blog" not in b["sources"]:
            b["sources"].append("blog")
        b["reviews"].append({"logNo": v["logNo"], "postTitle": post["title"], "date": post["date"], "url": post["url"], "chars": len(post["text"])})
        b["reviews"].sort(key=lambda r: r["date"])
        b["firstReadDate"] = b["reviews"][0]["date"]
        b["needsReview"] = False
        print(f"  독후감 추가: {b['title']} ({post['date']})")
    data["books"].sort(key=lambda b: (b["firstReadDate"] or "9999", b["title"]))
    BOOKS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    cats = json.loads(CATS.read_text(encoding="utf-8"))
    for b in data["books"]:
        if b["title"] in cats:
            continue
        text = " ".join(r["postTitle"] for r in b["reviews"]) + " " + b["title"]
        cats[b["title"]] = next((c for c, words in CAT_HINTS if any(w in text for w in words)), "그 밖의 책")
        print(f"  분류: {b['title']} -> {cats[b['title']]}")
    CATS.write_text(json.dumps(cats, ensure_ascii=False, indent=1), encoding="utf-8")
    return created


def update_covers(all_missing_covers: bool) -> None:
    data = json.loads(BOOKS.read_text(encoding="utf-8"))
    need = []
    for b in data["books"]:
        p = INFO / f"{slug(b['title'])}.json"
        if not p.exists():
            need.append(b)
        elif all_missing_covers and not json.loads(p.read_text(encoding="utf-8")).get("cover"):
            p.unlink(); need.append(b)   # 표지 없이 받아 둔 책은 다시 찾는다
    if not need:
        print("  표지·소개: 모두 있음"); return
    if not os.environ.get("KAKAO_REST_API_KEY"):
        print(f"  KAKAO_REST_API_KEY 가 없어 표지·소개를 받지 못한 책 {len(need)}권: {', '.join(b['title'] for b in need[:10])}")
        return
    run("scripts/book_info.py", *[f"{b['title']} / {b['author']}" if b["author"] else b["title"] for b in need])


def update_memory_covers(all_missing_covers: bool) -> None:
    """기억 서가(제목까지 기억나는 책)의 표지·소개. 서재 목록(books.json)에는 넣지 않고 정보만 받는다."""
    import time
    from book_info import fetch
    mem = json.loads(Path("data/memory_books.json").read_text(encoding="utf-8"))["books"]
    need = []
    for m in mem:
        if m["kind"] != "title":
            continue
        p = INFO / f"{slug(m['t'])}.json"
        if not p.exists():
            need.append(m)
        elif all_missing_covers and not json.loads(p.read_text(encoding="utf-8")).get("cover"):
            p.unlink(); need.append(m)
    if not need:
        print("  기억 서가 표지·소개: 모두 있음"); return
    key = os.environ.get("KAKAO_REST_API_KEY")
    if not key:
        print(f"  KAKAO_REST_API_KEY 가 없어 기억 서가 {len(need)}권의 표지·소개를 받지 못함"); return
    for n, m in enumerate(need, 1):
        print(f"  [{n}/{len(need)}] {fetch(m['t'], m.get('a'), key)}")
        time.sleep(0.1)


def main() -> None:
    if "--no-fetch" not in sys.argv:
        run("scripts/fetch_blog_posts.py")
        run("scripts/fetch_blog_bodies.py")
    print("새 글 판정:"); new = judge_new_posts()
    print("서재 데이터:"); created = add_reviews()
    print("표지·소개:"); update_covers("--covers" in sys.argv); update_memory_covers("--covers" in sys.argv)
    run("scripts/build_app.py")
    print(f"새 글 {len(new)}편 · 새 책 {len(created)}권{': ' + ', '.join(created) if created else ''}")


if __name__ == "__main__":
    main()
