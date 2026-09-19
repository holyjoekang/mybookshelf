"""블로그 독후감과 책장 사진에서 뽑은 책을 하나의 서재 데이터로 합친다.

입력
  data/blog_bodies.json          블로그 글 본문
  data/extracted/batch*.json     블로그 글 → 책 판정 결과
  data/extracted/photos.json     책장 사진 → 책 판정 결과
출력
  data/books.json                책 단위로 묶인 서재 시드 데이터

사용법: python scripts/merge_extracted.py
"""

import json
import re
from pathlib import Path

BODIES = Path("data/blog_bodies.json")
EXTRACTED_DIR = Path("data/extracted")
OUT = Path("data/books.json")


def normalize(title: str) -> str:
    """같은 책의 표기 차이를 흡수해 한 권으로 묶기 위한 키.

    끝의 숫자는 남긴다. '트렌드 코리아 2014'와 '2025', '불편한 편의점'과 '2'는
    서로 다른 책이라 숫자를 떼면 엉뚱하게 한 권으로 합쳐진다.
    """
    return re.sub(r"[^\w가-힣]", "", title.lower())


def add_book(books: dict, title: str, author: str | None) -> dict:
    entry = books.setdefault(
        normalize(title),
        {"title": title, "author": author, "sources": [], "reviews": [], "photos": []},
    )
    if not entry["author"] and author:
        entry["author"] = author
    return entry


def main() -> None:
    bodies = json.loads(BODIES.read_text(encoding="utf-8"))
    books: dict[str, dict] = {}
    skipped = []

    # 1) 블로그 독후감
    verdicts = {}
    for f in sorted(EXTRACTED_DIR.glob("batch*.json")):
        for item in json.loads(f.read_text(encoding="utf-8")):
            verdicts[item["logNo"]] = item

    if missing := set(bodies) - set(verdicts):
        print(f"경고: 판정 누락 {len(missing)}편")

    for log_no, v in verdicts.items():
        post = bodies.get(log_no)
        if post is None:
            continue
        if not v.get("isBook"):
            skipped.append({"title": post["title"], "reason": v.get("reason", "")})
            continue
        entry = add_book(books, v["bookTitle"], v.get("author"))
        if "blog" not in entry["sources"]:
            entry["sources"].append("blog")
        entry["reviews"].append(
            {
                "logNo": log_no,
                "postTitle": post["title"],
                "date": post["date"],
                "url": post["url"],
                "chars": len(post["text"]),
            }
        )

    # 2) 책장 사진
    photos_file = EXTRACTED_DIR / "photos.json"
    if photos_file.exists():
        for item in json.loads(photos_file.read_text(encoding="utf-8")):
            entry = add_book(books, item["title"], item.get("author"))
            if "photo" not in entry["sources"]:
                entry["sources"].append("photo")
            entry["photos"].append(
                {
                    "photo": item["photo"],
                    "confidence": item.get("confidence", "medium"),
                    "type": item.get("type", "book"),
                }
            )

    for b in books.values():
        b["reviews"].sort(key=lambda r: r["date"])
        b["firstReadDate"] = b["reviews"][0]["date"] if b["reviews"] else None
        # 사진에만 있고 확신이 낮은 책은 사용자 확인이 꼭 필요하다.
        b["needsReview"] = not b["reviews"] and all(
            p["confidence"] != "high" for p in b["photos"]
        )

    result = sorted(books.values(), key=lambda b: (b["firstReadDate"] or "9999", b["title"]))
    OUT.write_text(
        json.dumps({"books": result, "skipped": skipped}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by = lambda s: [b for b in result if s in b["sources"]]  # noqa: E731
    both = [b for b in result if len(b["sources"]) > 1]
    print(f"총 {len(result)}권")
    print(f"  블로그 독후감에서: {len(by('blog'))}권")
    print(f"  책장 사진에서:     {len(by('photo'))}권")
    print(f"  양쪽 모두:         {len(both)}권 -> {', '.join(b['title'] for b in both)}")
    print(f"  확인 필요:         {sum(b['needsReview'] for b in result)}권")
    print(f"  블로그 글 제외:    {len(skipped)}편")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
