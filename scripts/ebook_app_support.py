"""앱과 빌드가 '전자책' 출처(e)를 알아보게 한다(한 번만, 다시 돌려도 같은 결과)."""
from pathlib import Path

def patch(path, old, new):
    p = Path(path); t = p.read_text(encoding="utf-8")
    if new in t: return
    assert t.count(old) == 1, f"{path}: {old[:50]}"
    p.write_text(t.replace(old, new), encoding="utf-8")

B = "scripts/build_app.py"
patch(B, '''                "n": 1 if b["needsReview"] else 0,
            }
        )''', '''                "n": 1 if b["needsReview"] else 0,
                # 전자도서관 대출 기록: 마지막 대출일 · 횟수 · 전자책/오디오북
                **({"e": {"d": b["ebook"]["last"], "n": b["ebook"]["loans"], "k": b["ebook"]["kind"]}} if b.get("ebook") else {}),
            }
        )''')
patch(B, '"s": "".join(sorted(s[0] for s in b["sources"])),  # b / p / bp / i(텍스트로 추가)',
      '"s": "".join(sorted(s[0] for s in b["sources"])),  # b / p / bp / i(텍스트로 추가) / e(전자책)')

T = "app/index.template.html"
patch(T, 'var RIBBON = { b: 0x8A3330, p: 0x7E7A66, bp: 0xC9A04A, m: 0x4A6B8A, i: 0x4F7A55 };',
      'var RIBBON = { b: 0x8A3330, p: 0x7E7A66, bp: 0xC9A04A, m: 0x4A6B8A, i: 0x4F7A55, e: 0x3E6E8E, be: 0x6E4F8A, ep: 0x5B7F86, bep: 0xC9A04A };')
patch(T, '''    m: ["기억으로 넣은 책", "#4A6B8A"], i: ["직접 추가한 책", "#4F7A55"]
  };''', '''    m: ["기억으로 넣은 책", "#4A6B8A"], i: ["직접 추가한 책", "#4F7A55"],
    e: ["전자책으로 읽은 책", "#3E6E8E"], be: ["기록과 전자책", "#6E4F8A"], ep: ["전자책과 실물", "#5B7F86"], bep: ["기록과 실물 둘 다", "#C9A04A"]
  };''')
patch(T, 'cv: b.cv || null, pb: b.pb || null, period: b.p || null, mine: b.s === "m",',
      'cv: b.cv || null, pb: b.pb || null, period: b.p || null, mine: b.s === "m", eb: b.e || null,')
patch(T, '''    if (b.s.indexOf("p") >= 0) h += '<span class="badge own">집에 있는 책</span>';''',
      '''    if (b.s.indexOf("p") >= 0) h += '<span class="badge own">집에 있는 책</span>';
    if (b.eb) h += '<span class="badge">' + esc(b.eb.k) + " 대출 " + b.eb.n + "회</span>";''')
patch(T, '''      : b.s === "b" ? "블로그에 기록만 남아 있습니다. 실물은 더 이상 갖고 있지 않습니다."''',
      '''      : b.s === "b" ? "블로그에 기록만 남아 있습니다. 실물은 더 이상 갖고 있지 않습니다."
      : b.s === "e" ? "교보문고 전자도서관에서 빌려 읽은 " + (b.eb ? b.eb.k : "전자책") + "입니다." + (b.eb ? " 마지막 대출 " + b.eb.d + "." : "")''')
patch(T, 'b.s === "bp" ? "독후감 + 실물" : b.s === "b" ? "독후감" : "집 책장"',
      'b.s === "bp" ? "독후감 + 실물" : b.s === "b" ? "독후감" : b.s.indexOf("e") >= 0 ? "전자책" : "집 책장"')
print("전자책 출처 지원 완료")
