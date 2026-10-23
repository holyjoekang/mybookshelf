"""update_site.py 가 기억 서가(memory_books.json)의 책도 카카오로 표지·소개를 받게 한다(한 번만, 다시 돌려도 같은 결과).
기억 서가의 책은 books.json 에 넣지 않아야 하므로 book_info.add() 대신 fetch() 만 부른다."""
from pathlib import Path

p = Path(__file__).resolve().parent / "update_site.py"
t = p.read_text(encoding="utf-8")
old = '''    run("scripts/book_info.py", *[f"{b['title']} / {b['author']}" if b["author"] else b["title"] for b in need])
'''
new = '''    run("scripts/book_info.py", *[f"{b['title']} / {b['author']}" if b["author"] else b["title"] for b in need])


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
'''
if new not in t:
    assert t.count(old) == 1
    t = t.replace(old, new)
    t = t.replace('    print("표지·소개:"); update_covers("--covers" in sys.argv)\n',
                  '    print("표지·소개:"); update_covers("--covers" in sys.argv); update_memory_covers("--covers" in sys.argv)\n')
    assert "update_memory_covers(\"--covers\"" in t
    p.write_text(t, encoding="utf-8")
print("기억 서가 표지 받기 연결")
