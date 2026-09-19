"""book_info.py · build_app.py 테스트.  python scripts/test_book_info.py

실제 data/ 는 건드리지 않고 임시 폴더에서 돈다.
KAKAO_REST_API_KEY 가 있으면 실제 API로 한 권 받아보는 테스트까지 돈다.
"""

import io, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import book_info as bi
import build_app

DOC = {"title": "데미안", "authors": ["헤르만 헤세"], "translators": ["전영애"], "publisher": "민음사",
       "datetime": "2000-12-20T00:00:00.000+09:00", "isbn": "8937460440 9788937460449",
       "contents": "싱클레어의 성장기", "thumbnail": "https://img/x.jpg", "url": "https://daum/x"}
OTHER = {**DOC, "authors": ["다른 사람"], "contents": "엉뚱한 책"}


def jpg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (120, 174), "navy").save(buf, "JPEG")
    return buf.getvalue()


def fake_get(url, **kw):
    res = mock.Mock()
    res.raise_for_status = lambda: None
    res.json = lambda: {"documents": [OTHER, {**DOC, "contents": ""}, DOC]}
    res.content = jpg()
    return res


class Temp(unittest.TestCase):
    """data/ 대신 임시 폴더를 쓰게 경로를 바꿔 둔다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d / "books.json").write_text(json.dumps({"books": [], "skipped": []}), encoding="utf-8")
        self.patches = [mock.patch.object(bi, "OUT", d / "book_info"),
                        mock.patch.object(bi, "BOOKS", d / "books.json"),
                        mock.patch.object(build_app, "INFO", d / "book_info")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def books(self):
        return json.loads(bi.BOOKS.read_text(encoding="utf-8"))["books"]


class Offline(Temp):
    def test_parse_line(self):
        self.assertEqual(bi.parse_line(" 데미안 / 헤세 "), ("데미안", "헤세"))
        self.assertEqual(bi.parse_line("\ufeff데미안"), ("데미안", None))
        self.assertIsNone(bi.parse_line("   "))

    def test_pick(self):
        self.assertEqual(bi.pick([OTHER, {**DOC, "contents": ""}, DOC], "데미안", "헤세"), DOC)  # 저자 맞는 판본 중 소개 있는 것
        self.assertEqual(bi.pick([OTHER, DOC]), OTHER)  # 저자 모르면 소개 있는 첫 판본
        wrong = {**DOC, "title": "홍보의 신"}
        self.assertEqual(bi.pick([wrong, {**DOC, "title": "신 1"}], "신")["title"], "신 1")  # 제목이 다르게 시작하면 제외
        self.assertIsNone(bi.pick([]))

    @mock.patch.object(bi.requests, "get", side_effect=fake_get)
    def test_add_saves_json_and_adds_to_library(self, _):
        self.assertIn("서재에 추가", bi.add("데미안 / 헤세", "k"))
        info = json.loads((bi.OUT / "데미안.json").read_text(encoding="utf-8"))
        self.assertEqual((info["contents"], info["isbn"], info["pubdate"]),
                         ("싱클레어의 성장기", "9788937460449", "2000-12-20"))
        self.assertTrue((bi.OUT / info["cover"]).exists())
        self.assertEqual([(b["title"], b["author"], b["sources"]) for b in self.books()],
                         [("데미안", "헤세", ["input"])])
        self.assertIn("이미 서재에 있음", bi.add("데미안", "k"))  # 두 번 넣어도 한 권
        self.assertEqual(len(self.books()), 1)

    @mock.patch.object(bi.requests, "get", side_effect=fake_get)
    def test_build_reads_cover_and_contents(self, _):
        bi.add("데미안 / 헤세", "k")
        e = build_app.book_info("데미안")
        self.assertTrue(e["cv"].startswith("data:image/jpeg;base64,"))
        self.assertEqual((e["pb"], e["ds"]), ("민음사", "싱클레어의 성장기"))
        self.assertEqual(build_app.book_info("없는 책"), {})


@unittest.skipUnless(os.environ.get("KAKAO_REST_API_KEY"), "KAKAO_REST_API_KEY 없음")
class Ids(unittest.TestCase):
    """앱은 사용자가 고친 내용을 id에 저장하므로, 책이 늘거나 순서가 바뀌어도 기존 id는 그대로여야 한다."""

    def test_first_build_numbers_in_order(self):
        books = [{"t": "가"}, {"t": "나"}]
        self.assertEqual(build_app.assign_ids(books, ids := {}), ["가", "나"])
        self.assertEqual([b["i"] for b in books], [0, 1])
        self.assertEqual(ids, {"가": 0, "나": 1})

    def test_new_book_in_the_middle_keeps_old_ids(self):
        ids = {"가": 0, "다": 1, "빠진 책": 2}
        books = [{"t": "가"}, {"t": "나"}, {"t": "다"}]      # 제목순으로 '나'가 사이에 끼었다
        self.assertEqual(build_app.assign_ids(books, ids), ["나"])
        self.assertEqual([b["i"] for b in books], [0, 3, 1])  # 빠진 책의 2번은 다시 쓰지 않는다

    def test_duplicate_titles_stop_the_build(self):
        with self.assertRaises(SystemExit):
            build_app.assign_ids([{"t": "가"}, {"t": "가"}], {})


class Live(Temp):
    def test_real_book(self):
        print("\n  " + bi.add("협상의 법칙 / 허브 코헨", os.environ["KAKAO_REST_API_KEY"]))
        info = json.loads((bi.OUT / "협상의_법칙.json").read_text(encoding="utf-8"))
        self.assertIn("허브 코헨", info["authors"])
        self.assertTrue(info["contents"])
        self.assertGreater((bi.OUT / info["cover"]).stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
