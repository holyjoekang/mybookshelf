"""제목에 '/'가 든 책(『12 1/2 …』)이 '제목 / 저자'로 잘못 쪼개져 생긴 가짜 책을 지우고, 다시는 그렇게 쪼개지지 않게 한다.
- book_info.parse_line: ' / '(띄어 쓴 빗금)이 있으면 그것으로, 없으면 빗금 뒤가 숫자로 시작하지 않을 때만 나눈다
- data/books.json 의 가짜 책 '12 1' 과 그 정보 파일을 지운다(id 대장은 그대로 두어 번호를 다시 쓰지 않는다)
다시 돌려도 같은 결과."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
bi = ROOT / "scripts/book_info.py"
t = bi.read_text(encoding="utf-8")
old = '''    title, _, author = line.lstrip("\\ufeff").partition("/")  # 메모장·PowerShell이 붙이는 BOM 제거'''
new = '''    line = line.lstrip("\\ufeff")  # 메모장·PowerShell이 붙이는 BOM 제거
    # '제목 / 저자'. 『12 1/2 …』처럼 제목 안의 빗금(뒤가 숫자)은 나누지 않는다
    m = re.search(r"\\s+/\\s+", line) or re.search(r"/(?!\\d)", line)
    title, author = (line[:m.start()], line[m.end():]) if m else (line, "")'''
if new not in t:
    assert t.count(old) == 1
    bi.write_text(t.replace(old, new), encoding="utf-8")

books = ROOT / "data/books.json"
data = json.loads(books.read_text(encoding="utf-8"))
bad = [b for b in data["books"] if b["title"] == "12 1" and b["sources"] == ["input"]]
data["books"] = [b for b in data["books"] if b not in bad]
books.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
for f in (ROOT / "data/book_info").glob("12_1.*"):
    f.unlink()
print(f"가짜 책 {len(bad)}권 지움")
