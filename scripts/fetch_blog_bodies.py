"""data/blog_posts.json의 각 글 본문을 수집한다.

사용법: python scripts/fetch_blog_bodies.py
결과: data/blog_bodies.json (이어받기 지원 — 이미 받은 글은 건너뛴다)
"""

import html
import json
import re
import time
import urllib.request
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    "Referer": "https://blog.naver.com/",
}
POSTS = Path("data/blog_posts.json")
OUT = Path("data/blog_bodies.json")
SCRIPT_RE = re.compile(r"<(script|style).*?</\1>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
# 최신 글은 SmartEditor ONE, 2008년 전후 글은 구형 에디터라 컨테이너가 다르다.
CONTAINERS = [
    r'<div[^>]*class="[^"]*se-main-container',
    r'<div[^>]*id="postViewArea',
    r'<div[^>]*class="[^"]*post_ct',
    r'<div[^>]*class="[^"]*se_component_wrap',
]


def extract_text(raw: str) -> str:
    # 스크립트를 먼저 걷어내지 않으면 스크립트 안의 셀렉터 문자열에 걸린다.
    raw = SCRIPT_RE.sub(" ", raw)
    seg = raw
    for pattern in CONTAINERS:
        m = re.search(pattern, raw)
        if m:
            seg = raw[m.start() : m.start() + 120000]
            break
    seg = TAG_RE.sub(" ", seg)
    seg = html.unescape(seg)
    seg = seg.replace("​", " ")
    return re.sub(r"\s+", " ", seg).strip()


def fetch_body(blog_id: str, log_no: str) -> str:
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return extract_text(resp.read().decode("utf-8", errors="replace"))


def main() -> None:
    data = json.loads(POSTS.read_text(encoding="utf-8"))
    blog_id = data["blogId"]
    posts = data["posts"]

    bodies = {}
    if OUT.exists():
        bodies = json.loads(OUT.read_text(encoding="utf-8"))
        # 파싱에 실패해 껍데기만 남은 항목은 버리고 다시 받는다.
        bodies = {k: v for k, v in bodies.items() if len(v["text"]) >= 300}

    for n, p in enumerate(posts, 1):
        log_no = p["logNo"]
        if log_no in bodies:
            continue
        try:
            text = fetch_body(blog_id, log_no)
        except Exception as e:  # 개별 글 실패가 전체 수집을 막지 않게 한다
            print(f"[{n}/{len(posts)}] 실패 {log_no}: {e}")
            continue
        bodies[log_no] = {
            "title": p["title"],
            "date": p["date"],
            "url": p["url"],
            "text": text,
        }
        print(f"[{n}/{len(posts)}] {len(text):>6}자  {p['title'][:40]}")
        if n % 20 == 0:
            OUT.write_text(
                json.dumps(bodies, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        time.sleep(0.3)

    OUT.write_text(json.dumps(bodies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {OUT} ({len(bodies)}편)")


if __name__ == "__main__":
    main()
