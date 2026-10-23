"""전자책은 서재에 꽂되 '전자책'이라는 표시는 화면에 내지 않는다(한 번만, 다시 돌려도 같은 결과).
- '남은 방식' 서고에서 전자책 묶음을 없앤다: 전자책만 있는 책은 '읽은 책', 독후감·실물이 있으면 그쪽으로
- 상세 패널의 '전자책 대출 N회' 배지와 전자책 안내 문구, 목록의 '전자책' 꼬리표를 뺀다"""
from pathlib import Path

def patch(old, new):
    p = Path("app/index.template.html"); t = p.read_text(encoding="utf-8")
    if new in t: return
    assert t.count(old) == 1, old[:60]
    p.write_text(t.replace(old, new), encoding="utf-8")

patch('''    e: ["전자책으로 읽은 책", "#3E6E8E"], be: ["기록과 전자책", "#6E4F8A"], ep: ["전자책과 실물", "#5B7F86"], bep: ["기록과 실물 둘 다", "#C9A04A"]
  };''', '''    r: ["읽은 책", "#3E6E8E"]
  };
  // 전자책(e)은 화면에 따로 드러내지 않는다: 남은 방식은 e 를 빼고 고르고, 전자책만 있으면 '읽은 책'
  function stateOf(s) { return s.replace("e", "") || "r"; }''')
patch('label: "남은 방식", of: function (b) { return (STATES[b.s] || STATES.b)[0]; },',
      'label: "남은 방식", of: function (b) { return (STATES[stateOf(b.s)] || STATES.b)[0]; },')
patch('''
    if (b.eb) h += '<span class="badge">' + esc(b.eb.k) + " 대출 " + b.eb.n + "회</span>";''', "")
patch('''      : b.s === "e" ? "교보문고 전자도서관에서 빌려 읽은 " + (b.eb ? b.eb.k : "전자책") + "입니다." + (b.eb ? " 마지막 대출 " + b.eb.d + "." : "")''',
      '''      : b.s === "e" ? "읽은 책입니다." + (b.eb ? " 마지막으로 읽은 때 " + b.eb.d + "." : "")''')
patch('b.s.indexOf("e") >= 0 ? "전자책" : "집 책장"', 'b.s === "e" ? "읽은 책" : "집 책장"')
print("전자책 표시 숨김 완료")

# 독후감+전자책(be)·실물+전자책(ep) 같은 책도 원래 꼬리표(독후감·집 책장…)를 받도록, 비교는 e 를 뺀 값으로 한다
p = Path("app/index.template.html"); t = p.read_text(encoding="utf-8")
for k in ("bp", "b", "i"):
    t = t.replace(f'b.s === "{k}"', f'stateOf(b.s) === "{k}"')
p.write_text(t, encoding="utf-8")
