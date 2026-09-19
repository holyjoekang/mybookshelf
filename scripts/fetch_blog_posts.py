"""네이버 블로그 '독서,책' 카테고리 글 목록을 수집한다.

사용법: python scripts/fetch_blog_posts.py [blogId] [categoryNo]
결과: data/blog_posts.json
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

LIST_URL = (
    "https://blog.naver.com/PostTitleListAsync.naver"
    "?blogId={blog_id}&viewdate=&currentPage={page}"
    "&categoryNo={category_no}&parentCategoryNo=&countPerPage={per_page}"
)
PER_PAGE = 30
# Naver는 Referer 없이 호출하면 csrf 에러를 돌려준다.
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://blog.naver.com/"}

# 응답 JSON에 잘못된 escape가 섞여 있어 json.loads가 실패한다. 필요한 필드만 정규식으로 뽑는다.
ITEM_RE = re.compile(
    r'"logNo":"(?P<log_no>\d+)","title":"(?P<title>.*?)","categoryNo".*?"addDate":"(?P<add_date>[^"]*)"'
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_page(blog_id: str, category_no: int, page: int) -> list[dict]:
    raw = fetch(
        LIST_URL.format(
            blog_id=blog_id, page=page, category_no=category_no, per_page=PER_PAGE
        )
    )
    posts = []
    for m in ITEM_RE.finditer(raw):
        posts.append(
            {
                "logNo": m.group("log_no"),
                "title": urllib.parse.unquote_plus(m.group("title")),
                "date": m.group("add_date"),
                "url": f"https://blog.naver.com/{blog_id}/{m.group('log_no')}",
            }
        )
    return posts


def main() -> None:
    blog_id = sys.argv[1] if len(sys.argv) > 1 else "joekang"
    category_no = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    all_posts: list[dict] = []
    seen: set[str] = set()
    page = 1
    while True:
        posts = fetch_page(blog_id, category_no, page)
        fresh = [p for p in posts if p["logNo"] not in seen]
        if not fresh:
            break
        for p in fresh:
            seen.add(p["logNo"])
        all_posts.extend(fresh)
        print(f"page {page}: +{len(fresh)} (총 {len(all_posts)})")
        page += 1
        time.sleep(0.4)

    out = Path("data/blog_posts.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"blogId": blog_id, "categoryNo": category_no, "posts": all_posts},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"저장: {out} ({len(all_posts)}편)")


if __name__ == "__main__":
    main()
