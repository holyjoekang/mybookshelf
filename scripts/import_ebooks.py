"""교보문고 전자도서관 대출 이력(data/ebooks_kyobo.tsv)을 서재에 넣는다.

- 이미 서재에 있는 책(블로그 독후감·책장 사진)은 '전자책' 출처와 대출 기록만 덧붙인다
- 없는 책은 새로 꽂는다. 읽은 때 = 마지막 대출일, 분류 = TSV 마지막 칸
- 표지·저자·소개는 update_site.py 가 카카오 책 검색으로 채운다(KAKAO_REST_API_KEY)
다시 돌려도 같은 결과. 새 대출 이력을 붙여 넣으면 그 줄만 더해진다.

사용법: python scripts/import_ebooks.py && python scripts/update_site.py --no-fetch
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from merge_extracted import normalize  # noqa: E402

TSV, BOOKS, CATS = ROOT / "data/ebooks_kyobo.tsv", ROOT / "data/books.json", ROOT / "data/categories.json"
CAT = {"경": "경영·경제", "자": "자기계발", "소": "소설·문학", "인": "인문·철학", "신": "신앙·종교", "과": "과학·기술·AI",
       "사": "사회·트렌드", "중": "중국·일본", "에": "인생·에세이", "심": "심리", "교": "교재·실용"}
dot = lambda d: "{}. {}. {}.".format(*map(int, d.split("-")))  # 2026-10-05 -> 2026. 10. 5. (블로그 날짜 꼴)  # noqa: E731
key2 = lambda t: normalize(re.sub(r"\([^)]*\)$", "", t))       # '(10만 부 기념 …)' 같은 판 표기는 떼고도 맞춰 본다  # noqa: E731

data = json.loads(BOOKS.read_text(encoding="utf-8"))
cats = json.loads(CATS.read_text(encoding="utf-8"))
by = {}
for b in data["books"]:
    by.setdefault(normalize(b["title"]), b); by.setdefault(key2(b["title"]), b)
added, merged = [], []
for line in TSV.read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    title, raw, last, loans, kind, cat = line.split("|")
    eb = {"last": last, "loans": int(loans), "kind": "오디오북" if kind == "a" else "전자책", "raw": raw}
    b = by.get(normalize(title)) or by.get(key2(title))
    if b is None:
        b = {"title": title, "author": None, "sources": [], "reviews": [], "photos": [],
             "firstReadDate": dot(last), "needsReview": False}
        data["books"].append(b); by[normalize(title)] = by[key2(title)] = b; added.append(title)
    elif "ebook" not in b["sources"]:
        merged.append(b["title"])
    if "ebook" not in b["sources"]:
        b["sources"].append("ebook")
    b["ebook"] = eb
    if not b.get("firstReadDate"):
        b["firstReadDate"] = dot(last)
    cats.setdefault(b["title"], CAT[cat])
data["books"].sort(key=lambda b: (b["firstReadDate"] or "9999", b["title"]))
BOOKS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
CATS.write_text(json.dumps(cats, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"전자책: 새로 꽂음 {len(added)}권 · 기존 책에 덧붙임 {len(merged)}권{(' (' + ', '.join(merged) + ')') if merged else ''}")
