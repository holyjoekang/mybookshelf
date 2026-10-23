"""학창 시절 독서 목록(data/school_books.tsv)을 기억 서가(data/memory_books.json)에 넣는다.

- 같은 책의 다른 이름(백경=모비 딕, 장발장=레 미제라블 …)과 겹치는 줄은 한 권으로 묶고, 뒤 시기는 '다시 읽음'으로 적는다
- 이미 서재(독후감·사진·전자책)나 기억 서가에 있는 책은 새로 꽂지 않는다(서재에 있으면 시기 메모만 덧붙인다)
- '보완 후보'는 메모로 구분해 둔다. 실존이 확인되지 않는 제목은 넣지 않는다
- 이 스크립트가 넣은 줄에는 "src": "school-list" 를 달아, 다시 돌리면 지우고 새로 넣는다(같은 결과)
사용법: python scripts/import_school_books.py && python scripts/update_site.py --no-fetch
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from merge_extracted import normalize  # noqa: E402

TSV, MEM, BOOKS = ROOT / "data/school_books.tsv", ROOT / "data/memory_books.json", ROOT / "data/books.json"
SRC = "school-list"
ALIAS = {"백경": "모비 딕", "노틀담의 꼽추": "파리의 노트르담", "장발장": "레 미제라블", "로빈슨 표류기": "로빈슨 크루소",
         "마담 보바리": "보바리 부인", "이솝 이야기": "이솝 우화", "삼국지연의": "삼국연의", "비밀의 섬": "신비의 섬",
         "카네기 인간관계론": "인간관계론", "정글의 왕자": "정글북"}
SKIP = {"변성": "셰익스피어 작품 가운데 같은 제목이 없음"}
NO_AUTHOR = {"작자 미상", "여러 작가", "여러 저자", "여러 판본", "유교 경전"}
CAT = {}
for c, titles in {
    "중국·일본": "논어 맹자 대학 중용 도덕경 장자 손자병법 사기 삼국지(정사) 자치통감 사기열전 삼국연의 수호전 서유기 홍루몽 초한지 열국지 아Q정전 광인일기",
    "인문·철학": "국가|소크라테스의 변명|니코마코스 윤리학|군주론|삼국사기|삼국유사|열하일기|한중록|목민심서|난중일기|징비록|택리지|정감록|로마 제국 쇠망사|플루타르코스 영웅전|갈리아 전기|인간의 조건|자유로부터의 도피|철학의 위안|철학 이야기|서양철학사|철학의 문제들|정의란 무엇인가|문명의 충돌|역사의 연구|역사란 무엇인가|공산당 선언|프로테스탄티즘의 윤리와 자본주의 정신|사회계약론|에밀|리바이어던|통치론|자유론|군중심리|역사철학|차라투스트라는 이렇게 말했다|도덕의 계보|죽음에 이르는 병|존재와 시간|실존주의는 휴머니즘이다|방법서설|순수이성비판|팡세|시지프 신화|그리스 로마 신화|변신 이야기",
    "과학·기술·AI": "천문학의 역사|코스모스|이기적 유전자|종의 기원|인간의 유래|시간의 역사|상대성 이론|과학혁명의 구조|과학적 발견의 논리|침묵의 봄|인간 본성에 대하여",
    "심리": "꿈의 해석|정신분석 입문|심리학의 원리|심리학의 이해|사랑의 기술",
    "자기계발": "인간관계론|성공하는 사람들의 7가지 습관",
    "경영·경제": "자본론|국부론",
    "신앙·종교": "천로역정",
}.items():
    for t in (titles.split("|") if "|" in titles else titles.split()):
        CAT[t] = c

# 1) 목록 읽기: 처음 나온 시기 = 처음 읽은 때, 뒤에 다시 나오면 '다시 읽음'
seen, order, skipped = {}, [], []
period = None
for line in TSV.read_text(encoding="utf-8").splitlines():
    if line.startswith("#P "):
        period = line[3:].strip(); continue
    if not line.strip() or line.startswith("#"):
        continue
    t, a, tag = line.split("|")
    if t in SKIP:
        skipped.append(f"{t}({SKIP[t]})"); continue
    t = ALIAS.get(t, t)
    e = seen.get(t)
    if e is None:
        e = seen[t] = {"t": t, "a": None if a in NO_AUTHOR else a, "period": period, "tags": {tag}, "again": []}
        order.append(e)
    else:
        e["tags"].add(tag)
        if period != e["period"] and period not in e["again"]:
            e["again"].append(period)

# 2) 서재·기억 서가와 맞춰 보기
lib = {normalize(b["title"]): b["title"] for b in json.loads(BOOKS.read_text(encoding="utf-8"))["books"]}
mem = json.loads(MEM.read_text(encoding="utf-8"))
mem["books"] = [m for m in mem["books"] if m.get("src") != SRC]
have = {normalize(m["t"]) for m in mem["books"]}
added, linked, dup = [], [], []
for e in order:
    k = normalize(e["t"])
    memo = []
    if e["tags"] == {"s"}:
        memo.append("학창 시절 독서 보완 목록")
    if e["again"]:
        memo.append("·".join(e["again"]) + " 때 다시 읽음")
    if k in have:
        dup.append(e["t"]); continue
    if k in lib:
        mem["books"].append({"period": e["period"], "kind": "existing", "t": lib[k], "memo": f"{e['period']} 때 처음 읽음" + (". " + memo[-1] if e["again"] else ""), "src": SRC})
        linked.append(lib[k]); continue
    row = {"period": e["period"], "kind": "title", "t": e["t"], "a": e["a"], "c": CAT.get(e["t"], "소설·문학"), "src": SRC}
    if memo:
        row["memo"] = ". ".join(memo)
    mem["books"].append(row); added.append(e["t"]); have.add(k)

for p, d in {"중학교": "중학교 시절 — 청소년 문학과 세계 고전.", "고등학교": "고등학교 시절 — 한국 근현대 문학과 사상 입문."}.items():
    mem["periods"].setdefault(p, d)
body = ",\n".join("    " + json.dumps(m, ensure_ascii=False) for m in mem["books"])
head = json.dumps({k: v for k, v in mem.items() if k != "books"}, ensure_ascii=False, indent=2)[:-2]
MEM.write_text(head + ',\n  "books": [\n' + body + "\n  ]\n}\n", encoding="utf-8")
print(f"목록 400줄 → 서로 다른 책 {len(order)}권: 새로 꽂음 {len(added)} · 서재에 이미 있어 메모만 {len(linked)} · 기억 서가에 이미 있음 {len(dup)}")
print("서재에 이미 있음:", ", ".join(linked)); print("넣지 않음:", ", ".join(skipped))
