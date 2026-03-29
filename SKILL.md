# 인스타그램 카드뉴스 자동화 파이프라인

## 목적
주제 입력 → 트렌드 분석 → 카드뉴스 생성 → 로컬 파일 저장
실제 인스타그램 업로드는 사람이 직접 검수 후 수행한다.
백엔드 서버 없이 로컬에서만 동작한다.

---

## 프로젝트 구조

```
cardnews/
├── .env                  ← API 키 (절대 수정 금지)
├── run.py                ← 진입점. 여기만 실행하면 된다
├── trend.py              ← 트렌드 수집 + Claude 주제 선정
├── generator.py          ← Claude Haiku 슬라이드 콘텐츠 생성
├── image.py              ← fal.ai FLUX 이미지 생성
├── renderer.py           ← Playwright PNG 렌더링 + 템플릿 분기
└── templates/
    ├── thumbnail.html    ← 썸네일 카드 (이미지 배경 + 임팩트 텍스트)
    └── content.html      ← 콘텐츠 카드 (흰 배경 + 미니멀 레이아웃)
```

---

## 실행 방법

```bash
# 방법 1: 트렌드 자동 분석 → 주제 자동 선정 → 카드 생성
python run.py

# 방법 2: 주제 직접 지정 → 카드 생성
python run.py "2025 홈트 루틴 5가지"
```

결과물은 `output/YYYYMMDD_HHMM/` 폴더에 날짜별로 저장된다.

---

## 파이프라인 단계별 설명

### Step 1 — 주제 결정 (run.py)
- 터미널 인자가 있으면 그 주제를 사용한다
- 인자가 없으면 trend.py를 호출해 트렌드 기반으로 자동 선정한다

### Step 2 — 트렌드 분석 (trend.py)
세 가지 소스에서 트렌드를 수집한다:
- 네이버 DataLab API: 검색어 트렌드 점수 (NAVER_CLIENT_ID/SECRET 필요)
- Google Trends (pytrends): 실시간 급상승 + 연관 키워드
- RSS 뉴스피드: 최신 기사 제목 키워드

수집 후 Claude Haiku가 채널 니치와 urgency 기준으로 Top 3 주제를 선정한다.
urgency=high인 주제를 자동 선택하고, 없으면 첫 번째를 선택한다.

### Step 3 — 슬라이드 생성 (generator.py)
모델: claude-haiku-4-5-20251001 (비용 절감)
슬라이드 구성:
- slides[0]: 썸네일 (badge + title 20자 이내 + subtitle + image_prompt)
- slides[1~N]: 콘텐츠 (title 20자 이내 + body 40자 이내 + cta 15자 이내)

글자 수 제한을 반드시 지킨다. 초과 시 카드에서 텍스트가 잘린다.

### Step 4 — 이미지 생성 (image.py)
모델: fal-ai/flux/schnell (장당 약 $0.003)
썸네일 배경용 이미지 1장만 생성한다.
프롬프트 조건: cinematic, minimal, dark gradient bottom for text readability

### Step 5 — PNG 렌더링 (renderer.py)
Playwright headless Chromium으로 1080×1080 PNG를 생성한다.
- slides[0] → thumbnail.html 템플릿 적용 → card_01_thumbnail.png
- slides[1~N] → content.html 템플릿 적용 → card_02_content.png ~

브랜드 설정은 renderer.py 상단 BRAND 딕셔너리에서 관리한다:
```python
BRAND = {
    "name": "MYPAGE",      # 카드에 표시될 브랜드명
    "accent": "#2D6AFF",   # 포인트 컬러
}
```

---

## 디자인 원칙

### 썸네일 (thumbnail.html)
- 목적: 피드에서 클릭 유도
- 배경: fal.ai가 생성한 이미지 + 어두운 오버레이
- 텍스트: 크고 임팩트 있게, 최소화
- 구성: 브랜드명 + 뱃지 + 메인 제목 + 부제목

### 콘텐츠 (content.html)
- 목적: 정보 전달, 가독성 최우선
- 배경: 흰색 단색
- 텍스트: 짧고 핵심만 (body 한 줄 원칙)
- 구성: 상단 컬러바 + 브랜드 + 슬라이드 번호 + 제목 + 본문 + CTA

---

## 비용 구조 (카드 1세트 기준)

| 항목 | 도구 | 비용 |
|---|---|---|
| 트렌드 주제 선정 | Claude Haiku | ~$0.001 |
| 슬라이드 콘텐츠 생성 | Claude Haiku | ~$0.002 |
| 배경 이미지 1장 | FLUX Schnell | ~$0.003 |
| PNG 렌더링 | Playwright 로컬 | $0 |
| 합계 | | ~$0.006 / 세트 |

---

## 필요한 API 키 (.env)

```
ANTHROPIC_API_KEY=sk-ant-...
FAL_KEY=...
NAVER_CLIENT_ID=...          # 선택 사항 (없으면 해당 소스 스킵)
NAVER_CLIENT_SECRET=...      # 선택 사항
```

---

## 패키지 설치

```bash
pip install anthropic fal-client playwright pytrends feedparser python-dotenv httpx
playwright install chromium
```

---

## Cowork 작업 지시 방법

아래 형식으로 지시하면 된다:

```
SKILL.md를 읽고 파이프라인 구조를 파악한 뒤:
1. .env 파일에 API 키가 제대로 설정됐는지 확인해줘
2. python run.py "주제" 를 실행해줘
3. output/ 폴더에 PNG가 정상 생성됐는지 확인해줘
4. 오류가 있으면 원인 분석 후 수정하고 재실행해줘
```

---

## 오류 대응 원칙

- ImportError: 패키지 설치 명령 실행 후 재시도
- API 인증 오류: .env 키 확인 요청 (직접 수정하지 않음)
- 렌더링 오류: Playwright 브라우저 재설치 후 재시도
- JSON 파싱 오류: Claude 응답에 마크다운이 섞인 경우 → generator.py 프롬프트에 "JSON만 반환" 조건 강화
- 네이버 API 없을 시: 해당 소스 스킵하고 Google Trends + RSS만으로 진행

---

## 하지 말아야 할 것

- 인스타그램 자동 업로드 구현 (사람이 직접 해야 함)
- 백엔드 서버 구축 (로컬 전용)
- .env 파일 내용 출력 또는 수정
- output/ 폴더 외부에 파일 저장
