"""카카오·표지 서버 연결이 한 번 끊겨도 전체 업데이트가 멈추지 않게 한다(한 번만, 다시 돌려도 같은 결과).
book_info.fetch(): 연결 오류면 2초·5초 쉬고 다시, 세 번 다 실패하면 그 책만 건너뛴다(다음 실행 때 다시 찾는다)."""
import re
from pathlib import Path

p = Path(__file__).resolve().parent / "book_info.py"
t = p.read_text(encoding="utf-8")
old = '''def fetch(title: str, author: str | None, key: str) -> str:
    """책 정보를 받아 json·표지로 저장한다."""'''
new = '''def fetch(title: str, author: str | None, key: str) -> str:
    """책 정보를 받아 json·표지로 저장한다. 연결이 끊기면 두 번 더 해 보고, 그래도 안 되면 이 책만 건너뛴다."""
    for wait in (2, 5, None):
        try:
            return _fetch(title, author, key)
        except requests.RequestException as e:
            if wait is None:
                return f"건너뜀 {title} ({type(e).__name__})"
            time.sleep(wait)


def _fetch(title: str, author: str | None, key: str) -> str:'''
if new not in t:
    assert t.count(old) == 1
    t = t.replace(old, new)
    if not re.search(r"^import .*\btime\b", t, re.M):
        t = t.replace("import requests", "import time\n\nimport requests", 1)
    p.write_text(t, encoding="utf-8")
print("재시도 연결")
