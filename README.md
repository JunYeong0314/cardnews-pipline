# 카드뉴스 생성 파이프라인

이 프로젝트는 로컬 환경에서 인스타그램 카드뉴스를 생성하는 파이프라인입니다.

권장 Python 버전:
- 최소: Python 3.10 이상
- 권장: Python 3.11 또는 3.12

입력:
- 직접 입력한 주제
- 또는 트렌드 기반으로 자동 선정한 주제

출력:
- 슬라이드 JSON
- 피드용 평문 텍스트 파일
- 카드 HTML
- 프리뷰 HTML
- Playwright가 설치되어 있으면 PNG 카드 이미지
- 업로드용 묶음 폴더 `feed_upload`

전체 흐름:
1. 주제를 받습니다.
2. 슬라이드 텍스트와 이미지 프롬프트를 생성합니다.
3. 슬라이드 내용을 요약한 피드용 평문 텍스트를 생성합니다.
   마지막 줄에는 관련 해시태그를 함께 붙입니다.
4. 슬라이드별 배경 이미지를 생성합니다.
5. 카드 HTML을 만듭니다.
6. 가능하면 PNG까지 렌더링합니다.

## 빠른 시작

처음 사용하는 팀원이라면 아래 순서만 그대로 따라 하면 됩니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
chmod +x install.sh
./install.sh
```

그다음 `.env`를 준비한 뒤 실행합니다.

```bash
python run.py "메모의 순기능"
```

디자인만 먼저 확인하고 싶다면:

```bash
python preview_demo.py "메모의 순기능"
```

## 1. 사전 준비

필요한 것:
- Python 3.10 이상
- 터미널 사용 가능 환경
- 프로젝트 루트 접근 권한

권장:
- Python 3.11 또는 3.12
- macOS 또는 Linux 계열 셸 환경

현재 위치가 프로젝트 루트인지 먼저 확인하세요.

```bash
pwd
```

예상 경로:

```text
<project-root>
```

## 2. 가상환경 만들기

처음 한 번만 하면 됩니다.

먼저 `python3 --version`으로 현재 버전을 확인하세요.

```bash
python3 --version
```

`Python 3.10` 이상이 아니라면 로컬 Python을 업데이트한 뒤 진행하는 것을 권장합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

정상 활성화되면 프롬프트 앞에 `(.venv)`가 붙습니다.

현재 어떤 파이썬을 쓰는지 확인하려면:

```bash
which python
```

정상이라면 아래와 비슷한 경로가 보여야 합니다.

```text
<project-root>/.venv/bin/python
```

## 3. 의존성 설치

가상환경이 활성화된 상태에서 아래 명령어를 실행하세요.

```bash
./install.sh
```

실행 권한이 없다면 한 번만 아래를 먼저 실행하세요.

```bash
chmod +x install.sh
./install.sh
```

이 스크립트는 아래 작업을 한 번에 처리합니다.
- `pip` 업그레이드
- [requirements.txt](./requirements.txt) 설치
- Playwright Chromium 설치

직접 설치 내용을 보고 싶다면 [install.sh](./install.sh)를 확인하면 됩니다.

## 4. 환경변수 준비

프로젝트 루트에 `.env` 파일을 두고 아래 값을 채워 사용합니다.

```env
ANTHROPIC_API_KEY=...
FAL_KEY=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

각 값의 용도:
- `ANTHROPIC_API_KEY`: 주제 선정, 슬라이드 텍스트 생성
- `FAL_KEY`: 슬라이드 배경 이미지 생성
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`: 네이버 트렌드 수집용, 없어도 실행 가능

주의:
- `.env`는 저장소에 커밋하지 않는 것을 권장합니다.
- API 키가 없는 경우 일부 단계는 데모 모드로 동작합니다.

## 5. 실행 방법

### 5-1. 주제를 직접 넣어 실행

```bash
python run.py "메모의 순기능"
```

이 방식은 특정 주제로 카드뉴스를 바로 만들 때 사용합니다.

### 5-2. 트렌드 기반으로 자동 실행

```bash
python run.py
```

이 방식은 트렌드 수집 후 주제를 자동 선정해서 카드뉴스를 생성합니다.

## 6. 디자인만 테스트하기

API 없이 카드 레이아웃과 디자인만 먼저 보고 싶다면 아래 명령어를 사용하세요.

```bash
python preview_demo.py "메모의 순기능"
```

이 명령어는 데모 슬라이드를 사용해 테스트용 결과물을 생성합니다.

생성 경로:

```text
output/test_content_design/
```

주요 결과물:
- `card_01_thumbnail.html`
- `card_02_content.html`
- `card_03_content.html`
- `card_04_content.html`
- `card_05_content.html`
- `preview.html`

브라우저에서 `preview.html`을 열면 카드 전체 디자인을 한 번에 확인할 수 있습니다.

참고:
- `pillow`가 설치되어 있으면 데모 배경 이미지도 함께 생성됩니다.
- Playwright가 없어도 HTML 프리뷰 자체는 확인할 수 있습니다.

## 7. 이미지 분위기 바꾸기

기본 이미지는 현재 기본 톤으로 생성됩니다. 분위기를 바꾸고 싶다면
[image_style_config.py](./image_style_config.py)에서
`ACTIVE_IMAGE_STYLE` 값을 바꾸면 됩니다.

예시:

```python
ACTIVE_IMAGE_STYLE = "warm_lifestyle"
```

기본 제공 프리셋:
- `default`: 현재 기본 톤 유지
- `warm_lifestyle`: 따뜻한 생활감, 햇살, 집/책상 중심
- `clean_minimal`: 정돈된 구성, 여백 많은 미니멀 톤
- `moody_editorial`: 더 깊은 그림자와 차분한 에디토리얼 톤
- `bright_magazine`: 밝고 세련된 매거진 화보 느낌
- `custom`: 직접 문구를 작성해서 사용

직접 지정하고 싶다면:

```python
ACTIVE_IMAGE_STYLE = "custom"

CUSTOM_IMAGE_STYLE = {
    "display_name": "Custom",
    "generator_hint": "한국어로 원하는 분위기를 설명",
    "image_prompt_hint": "english visual mood for the final image model prompt",
}
```

이 설정은 두 단계에 같이 반영됩니다.
- 슬라이드 생성 시 LLM이 `image_prompt`를 만드는 방식
- 실제 이미지 모델이 최종 프롬프트를 보강하는 방식

## 8. 결과물 위치

실행 결과는 날짜별 폴더에 저장됩니다.

```text
output/YYYYMMDD_HHMM/
```

예상 결과물:
- `slides.json`
- `feed_text.txt`
- `card_01_thumbnail.html`
- `card_02_content.html`
- `card_03_content.html`
- `card_04_content.html`
- `card_05_content.html`
- `preview.html`
- Playwright가 정상 동작하면 PNG 파일들
- `feed_upload/`

`feed_upload/` 폴더에는 인스타 업로드에 바로 사용할 수 있도록 PNG 파일들과 `feed_text.txt`가 함께 복사됩니다.

## 9. 자주 있는 문제

### `ModuleNotFoundError`

대부분 가상환경이 비활성화되어 있거나 의존성이 설치되지 않은 경우입니다.

```bash
source .venv/bin/activate
./install.sh
```

### `python-dotenv` 같은 패키지 오류

현재 사용 중인 파이썬이 가상환경 파이썬인지 먼저 확인하세요.

```bash
which python
```

그다음 설치를 다시 실행하세요.

```bash
./install.sh
```

### `playwright` 관련 오류

브라우저 설치가 누락된 경우가 많습니다.

```bash
python -m playwright install chromium
```

### API 키가 없을 때

일부 단계는 데모 모드로 동작합니다.
- `ANTHROPIC_API_KEY`가 없으면 데모 주제 또는 데모 슬라이드를 사용
- `FAL_KEY`가 없으면 데모 이미지 생성 경로를 시도

### 디자인만 보고 싶은데 실제 API 호출이 부담될 때

아래 명령어로 충분합니다.

```bash
python preview_demo.py "메모의 순기능"
```

## 10. 프로젝트 파일 역할

주요 파일:
- [run.py](./run.py): 전체 파이프라인 진입점
- [trend.py](./trend.py): 트렌드 수집과 주제 선정
- [generator.py](./generator.py): 슬라이드 텍스트 및 `image_prompt` 생성
- [image.py](./image.py): 이미지 생성 모델 호출
- [renderer.py](./renderer.py): HTML과 PNG 렌더링
- [preview_demo.py](./preview_demo.py): 디자인 테스트용 데모 실행
- [image_style_config.py](./image_style_config.py): 이미지 분위기 프리셋 설정
- [install.sh](./install.sh): 설치 자동화 스크립트
- [requirements.txt](./requirements.txt): 파이썬 패키지 목록

## 11. 팀 공용 사용 팁

- 처음 세팅할 때는 반드시 가상환경부터 만든 뒤 설치를 진행하세요.
- Python 버전은 `3.10 이상`으로 맞추는 것을 권장합니다. 가장 무난한 선택은 `3.11` 또는 `3.12`입니다.
- 실행 전에는 항상 `source .venv/bin/activate`로 가상환경을 활성화하세요.
- 디자인만 확인할 때는 `preview_demo.py`를 우선 사용하면 API 비용을 아낄 수 있습니다.
- 이미지 톤을 바꿔야 할 때는 코드 여기저기를 수정하지 말고 `image_style_config.py`만 먼저 조정하세요.
- `.env` 파일은 팀 내부에서만 공유하고 저장소에는 올리지 않는 것을 권장합니다.
