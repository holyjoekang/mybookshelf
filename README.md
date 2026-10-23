# 나의 서재

평생 읽어 온 책을 한곳에 모아 보는 **개인 가상 서재**입니다.
네이버 블로그에 23년 동안 쌓인 독서 기록과 집 책장 사진, 기억으로 되살린 학창 시절 책을 모아
three.js로 만든 도서관 안에 꽂아 둡니다.

- 서재에 꽂힌 책: 블로그 독후감 124권 + 책장 사진 151권 + 학창 시절 66권 (겹치는 책은 한 권으로 합침)
- 책마다 표지·저자·출판사·책 소개(카카오 책 검색)와 블로그 독후감 원문
- 설계와 진행 기록은 [PRD.md](PRD.md)에 있습니다.

## 주요 기능

- **첫 화면**: 도서관 홈페이지처럼 인사말, 소개(영/한), 장서 현황, 들어가기 버튼
- **2D / 3D 서고**
  - 2D: 모든 서고의 칸을 한 줄로 이어 붙인 긴 서가. 끌어서 밀고, 휠로 확대·축소
  - 3D: 분류마다 방이 하나씩 있고 방끼리 문간으로 이어짐. 바닥을 누르거나 방향키/WASD로 걷기
- **도서관 디자인 여섯 곳**: 런던 도서관(기본), 아드몬트 수도원, 트리니티 칼리지,
  왕립 포르투갈 독서실, 스트라호프 수도원, 슈투트가르트 시립도서관
- **설정**: 서고를 나누는 기준, 칸에 꽂는 순서, 칸 크기, 조명 밝기, 걷는 속도, 움직임 줄이기 (이 기기에 저장)
- **책 상세 패널**: 표지, 책 소개, 독후감, 제목·저자·분류·시기 수정
- **책갈피 색**으로 책 상태 구분, '확인 필요' 책은 앱에서 제목을 고치면 풀림
- **휴대폰 대응**: 서랍 메뉴, 아래에서 올라오는 상세 시트, 손가락 크기 버튼

## 폴더 구조

```
app/
  index.template.html   앱 원본 (HTML·CSS·JS 한 파일)
  index.html            빌드 결과 — 시작할 때 data/library.json 을 읽는 동적 앱
  data/library.json     빌드 결과 — 앱이 읽는 책 데이터
  covers/               빌드 결과 — 책 표지(<책 id>.jpg)
  img/                  첫 화면·도서관 그림
data/
  blog_posts.json       블로그 '독서,책' 카테고리 글 목록 (168편)
  blog_bodies.json      글 본문
  extracted/            블로그·사진에서 뽑은 책 후보
  books.json            합친 장서 목록
  memory_books.json     기억으로 복원한 학창 시절 책
  categories.json       책별 분류 (11개)
  book_ids.json         책 id 대장 (제목 → 번호, 번호가 밀리지 않게)
  book_info/            책마다 메타데이터(.json)와 표지 썸네일(.jpg)
pictures/               책장 사진 원본
scripts/                수집·가공·빌드 스크립트
```

## 실행하기

필요한 것: Python 3, Pillow

```bash
pip install pillow
```

사이트 전체 업데이트 (블로그 새 글 → 책 판정 → 서재 데이터 → 카카오 표지·소개 → 앱 파일):

```bash
KAKAO_REST_API_KEY=... python scripts/update_site.py          # 블로그부터 다시 받기
python scripts/update_site.py --no-fetch                         # 받은 데이터로 다시 빌드만
python scripts/update_site.py --covers                           # 표지 없는 책도 다시 찾기
```

새 글은 제목으로 판정합니다(『책 제목』 또는 `[독서노트] 제목`). 틀리면 `data/extracted/batch_auto.json`을 고치고 다시 돌리세요.
`.github/workflows/update.yml`이 매주 월요일 아침 자동으로 돌립니다(저장소 Secrets에 `KAKAO_REST_API_KEY` 필요).

로컬에서 열기:

```bash
python -m http.server 8777 --directory app
```

브라우저에서 http://localhost:8777 을 엽니다.

## 데이터 파이프라인

| 단계 | 스크립트 | 하는 일 |
|------|----------|---------|
| 1 | `fetch_blog_posts.py` | 네이버 블로그 '독서,책' 카테고리 글 목록 수집 |
| 2 | `fetch_blog_bodies.py` | 글 본문 수집 |
| 3 | `prepare_photos.py` | 책장 사진을 긴 변 1600px로 줄이고 회전 보정 |
| 4 | (LLM · 비전 모델) | 독후감 판정, 제목·저자 추출, 책등 읽기 → `data/extracted/` |
| 5 | `merge_extracted.py` | 블로그와 사진에서 나온 책을 합쳐 `books.json` 생성 |
| 6 | `book_info.py --all` | 카카오 책 검색으로 표지·소개글 받기 |
| 7 | `crop_home_images.py` | 첫 화면 그림 잘라 `app/img/`에 저장 |
| 8 | `build_app.py` | `app/index.html` · `app/data/library.json` · `app/covers/` 빌드 |
| ★ | `update_site.py` | 1·2·자동 판정·5(새 독후감만 덧붙임)·6·8을 한 번에 |

### 책 추가하기

제목(과 저자)만으로 책을 추가할 수 있습니다.

```bash
python scripts/book_info.py "제목 / 저자"
```

카카오 책 검색 키가 필요합니다. `KAKAO_REST_API_KEY` 환경변수에 REST API 키를 넣어 주세요.

> 알라딘 OpenAPI(2026-10-30 정지)와 네이버 책 검색 API(2026-07-31 종료)는 더 이상 쓸 수 없어 카카오 책 검색을 씁니다.

### 전자책 대출 이력

교보문고 전자도서관의 대출 목록을 `data/ebooks_kyobo.tsv`에 한 줄씩 붙여 넣고 돌립니다(제목|저자출판사|마지막 대출일|횟수|e·a|분류).

```bash
python scripts/import_ebooks.py && python scripts/update_site.py --no-fetch
```

이미 있는 책에는 '전자책' 출처만 덧붙고, 없는 책은 새로 꽂힙니다. 표지·저자·소개는 다음 자동 업데이트(카카오)가 채웁니다.

### 테스트

```bash
python scripts/test_book_info.py
```

## 주의할 점

- `app/index.html`은 빌드 결과물입니다. 수정은 `app/index.template.html`에 하고 다시 빌드하세요.
- 앱은 사용자가 고친 내용을 책 id(`b0`, `b1` …)에 저장합니다. 책 제목을 바로잡을 때는 `data/book_ids.json`의 키도 함께 바꿔야 수정 기록이 따라갑니다.
- 앱은 동적입니다: `index.html`은 화면만 담고, 책 데이터는 `data/library.json`, 표지는 `covers/`, 그림은 `img/`에서 읽습니다. 그래서 `app/` 폴더를 통째로 정적 호스팅(Vercel 등)해야 합니다. (예전 아티팩트 배포처럼 파일 하나로는 동작하지 않습니다.)

## 앞으로

- 바코드(ISBN) 스캔으로 책 등록
- 읽은 책 기반 추천, 베스트셀러 연동
- 인상 깊은 구절 하이라이트, 공유
