"""
generator.py — Claude Haiku 슬라이드 콘텐츠 생성
"""

import os
import json
import logging
import re

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
GENERATION_MODEL = "claude-haiku-4-5-20251001"
MAX_GENERATION_ATTEMPTS = 3


def generate_slides(topic: str) -> list:
    """주제를 받아 슬라이드 JSON 리스트를 반환한다."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY 없음 → 데모 슬라이드 반환")
        return _demo_slides(topic)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    prompt = _build_generation_prompt(topic)

    last_error = None
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        try:
            response = client.messages.create(
                model=GENERATION_MODEL,
                max_tokens=2200,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            if getattr(response, "stop_reason", None) == "max_tokens":
                logger.warning("Claude 응답이 max_tokens에 도달했습니다. 출력이 잘렸을 수 있어요.")
            text = _extract_text_from_response(response)
            slides = _parse_slides_json(text)
            _validate_slides(slides)
            logger.info(f"슬라이드 {len(slides)}장 생성 완료")
            return slides
        except Exception as e:
            last_error = e
            preview = text[:240].replace("\n", "\\n") if "text" in locals() else ""
            if preview:
                logger.warning(f"응답 미리보기: {preview}")
            logger.warning(f"슬라이드 JSON 파싱 실패 (시도 {attempt}/{MAX_GENERATION_ATTEMPTS}): {e}")

    logger.error(f"슬라이드 생성 오류: {last_error}")
    return _demo_slides(topic)

def _build_generation_prompt(topic: str) -> str:
    return f"""당신은 인스타그램 카드뉴스 콘텐츠 작성자이다.

주제: {topic}

아래 규칙을 반드시 지켜라:
1. 슬라이드 5장을 만들어라
2. slides[0]은 썸네일이다:
   - badge: 카테고리 태그 (예: "자기계발", "건강") 8자 이내
   - title: 메인 제목, 반드시 20자 이내
   - subtitle: 부제목, 25자 이내
   - subtitle은 반드시 2줄 안에 들어갈 정도로 짧고 간단한 한 문장으로 작성
   - 수식어를 줄이고 핵심만 남겨라
   - image_prompt: 영어로 된 배경 이미지 프롬프트
   - image_prompt는 짧고 간단한 영어 장면 설명만 써라
   - image_prompt는 8~18개 영어 단어 정도의 짧은 프레이즈로 작성하라
   - 스타일, 금지어, 카메라 조건을 길게 반복하지 말고 장면 묘사만 남겨라
   - image_prompt는 주제를 직접 보여주는 실사형 장면이어야 한다
   - 가능하면 사람 얼굴, 인물 중심 구도, 초상화는 피하고 물건, 공간, 풍경, 책상 위 장면처럼 비인물 피사체를 우선하라
   - 인물이 꼭 필요할 때만 멀리서 작게 포함하고, 얼굴 클로즈업은 절대 피하라
   - 주제와 어울리는 자연스러운 실사 장면을 우선하라
   - 사물, 공간, 풍경, 도시 장면, 이동 장면, 생활 환경, 상징적인 디테일까지 다양하게 사용할 수 있다
   - 사람은 꼭 필요할 때만 보조적으로 사용하라
   - 사람이 필요할 때는 얼굴 정면이나 클로즈업 대신 뒷모습, 옆모습 일부, 실루엣 정도만 제한적으로 사용하라
   - 손 클로즈업이나 과장된 제스처는 기본 선택이 아니며, 주제를 표현하는 데 꼭 필요할 때만 사용하라
   - 이미지 톤은 주제의 분위기에 맞춰라
   - 아침, 식사, 건강, 습관, 회복, 루틴, 생산성처럼 밝은 생활형 주제는 밝고 산뜻한 자연광, 아침 햇살, 신선한 공기감이 느껴지게 구성하라
   - 위기, 불안, 범죄, 사고, 전쟁, 상실처럼 무거운 주제일 때만 어둡고 긴장감 있는 톤을 사용하라
   - 아침 식사나 건강 주제는 카페/매장보다 집 주방, 식탁, 창가, 햇빛이 드는 생활 공간을 우선하라
   - 매장, 식당, 거리 간판, 포스터 벽, 제품 포장, 라벨이 많은 진열 공간, 글자가 붙은 소품이 많은 장소는 피하라
   - 어떤 형태의 글자, 숫자, 로고, 라벨, 표지, 인쇄물, 손글씨, 화면 텍스트도 읽히면 안 된다
   - 텍스트가 생길 수 있는 요소가 나오더라도 카메라 심도, 거리, 각도, 가림, 빛 반사 등을 이용해 자연스럽게 흐릿하거나 읽을 수 없게 구성하라
   - illustration, painting, 3d render, cgi 느낌은 절대 피하라
   - 왼쪽 하단에 큰 제목이 들어갈 여백이 있도록 구성
   - 예시: "sunlit home breakfast table with toast fruit and orange juice"
3. slides[1~4]는 콘텐츠이다:
   - title: 소제목, 반드시 20자 이내
   - body: 본문
   - body는 반드시 2줄 이상 3줄 이하가 되도록 작성
   - 본문은 두 문장으로 작성하고, 카드 안에서 자연스럽게 마무리될 정도의 길이로 설명하라
   - 문장이 중간에 끊긴 느낌 없이 끝까지 읽었을 때 자연스럽게 마무리되어야 한다
   - 본문은 최대한 영양가 있는 정보로 써라. 뻔한 조언이나 추상적인 자기계발 문구는 피하라
   - 최신 트렌드, 실제 행동 변화, 사회 분위기, 뉴스에서 다룰 법한 포인트를 우선 반영하라
   - 근거가 분명히 존재할 만한 정보, 사람들이 공감할 만한 현실적인 변화, 흥미로운 관찰 포인트를 담아라
   - 독자가 "그래서 요즘 이런 분위기구나" 하고 느낄 수 있는 구체성을 넣어라
   - 단, 숫자나 통계를 억지로 넣지 말고 짧은 문장 안에서 맥락이 느껴지게 써라
   - 말투는 친절하고 친근한 해요체로 쓰고, "~다", "~한다", "~된다" 같은 딱딱한 종결은 쓰지 마라
   - cta: 행동유도 문구, 15자 이내
   - image_prompt: 영어로 된 콘텐츠 배경 이미지 프롬프트
   - image_prompt는 짧고 간단한 영어 장면 설명만 써라
   - image_prompt는 8~18개 영어 단어 정도의 짧은 프레이즈로 작성하라
   - 스타일, 금지어, 카메라 조건을 길게 반복하지 말고 장면 묘사만 남겨라
   - image_prompt는 각 슬라이드 내용과 직접 관련된 실사형 장면이어야 한다
   - 실제 뉴스/다큐/라이프스타일 사진처럼 보일 장면 설명이어야 한다
   - 가능하면 사람보다 물건, 장소, 풍경, 환경 디테일을 우선하라
   - 인물이 꼭 필요할 때만 얼굴이 강조되지 않는 자연스러운 상황 컷으로 작성하라
   - 하단에 텍스트가 잘 보이도록 아래쪽 구도가 단순해야 한다
   - 주제와 어울리는 자연스러운 실사 장면을 우선하라
   - 사물, 공간, 풍경, 도시 장면, 이동 장면, 생활 환경, 상징적인 디테일까지 다양하게 사용할 수 있다
   - 사람은 꼭 필요할 때만 보조적으로 사용하라
   - 사람이 필요할 때는 얼굴 정면이나 클로즈업 대신 뒷모습, 옆모습 일부, 실루엣 정도만 제한적으로 사용하라
   - 손 클로즈업이나 과장된 제스처는 기본 선택이 아니며, 주제를 표현하는 데 꼭 필요할 때만 사용하라
   - 이미지 톤은 주제의 분위기에 맞춰라
   - 아침, 식사, 건강, 습관, 회복, 루틴, 생산성처럼 밝은 생활형 주제는 밝고 산뜻한 자연광, 아침 햇살, 신선한 공기감이 느껴지게 구성하라
   - 위기, 불안, 범죄, 사고, 전쟁, 상실처럼 무거운 주제일 때만 어둡고 긴장감 있는 톤을 사용하라
   - 아침 식사나 건강 주제는 카페/매장보다 집 주방, 식탁, 창가, 햇빛이 드는 생활 공간을 우선하라
   - 매장, 식당, 거리 간판, 포스터 벽, 제품 포장, 라벨이 많은 진열 공간, 글자가 붙은 소품이 많은 장소는 피하라
   - 어떤 형태의 글자, 숫자, 로고, 라벨, 표지, 인쇄물, 손글씨, 화면 텍스트도 읽히면 안 된다
   - 텍스트가 생길 수 있는 요소가 나오더라도 카메라 심도, 거리, 각도, 가림, 빛 반사 등을 이용해 자연스럽게 흐릿하거나 읽을 수 없게 구성하라
   - illustration, painting, 3d render, cgi 느낌은 절대 피하라
   - 예시: "bright home kitchen counter with yogurt berries and morning sunlight"
4. 반드시 유효한 JSON 배열만 출력하라
5. 문자열 안에 줄바꿈을 넣지 말고, 큰따옴표를 JSON 규칙에 맞게 이스케이프하라
6. 마크다운, 설명, 코드펜스 없이 순수 JSON만 출력하라

반드시 아래 JSON 형식으로만 응답하라:
[
  {{"type": "thumbnail", "badge": "...", "title": "...", "subtitle": "...", "image_prompt": "..."}},
  {{"type": "content", "title": "...", "body": "...", "cta": "...", "image_prompt": "..."}},
  {{"type": "content", "title": "...", "body": "...", "cta": "...", "image_prompt": "..."}},
  {{"type": "content", "title": "...", "body": "...", "cta": "...", "image_prompt": "..."}},
  {{"type": "content", "title": "...", "body": "...", "cta": "...", "image_prompt": "..."}}
]"""


def _extract_text_from_response(response) -> str:
    parts = []
    for block in response.content:
        if getattr(block, "type", "") == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _parse_slides_json(text: str) -> list:
    candidate = _extract_json_candidate(text)
    try:
        parsed = json.loads(candidate)
    except Exception:
        sanitized = _sanitize_json_candidate(candidate)
        parsed = json.loads(sanitized)
    return _coerce_slides_payload(parsed)


def _extract_json_candidate(text: str) -> str:
    cleaned = text.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        cleaned = next((part for part in parts if ("[" in part and "]" in part) or ("{" in part and "}" in part)), cleaned)
        cleaned = cleaned.replace("json", "", 1).strip()

    starts = []
    array_start = cleaned.find("[")
    object_start = cleaned.find("{")
    if array_start != -1:
        starts.append(array_start)
    if object_start != -1:
        starts.append(object_start)
    if not starts:
        raise ValueError("JSON 배열을 찾지 못했습니다.")

    start = min(starts)
    candidate = _extract_balanced_json(cleaned[start:])
    if not candidate:
        raise ValueError("균형 잡힌 JSON 본문을 찾지 못했습니다.")
    return candidate


def _sanitize_json_candidate(text: str) -> str:
    sanitized = text.replace("\r", "")
    sanitized = sanitized.replace("“", '"').replace("”", '"')
    sanitized = sanitized.replace("’", "'").replace("‘", "'")
    sanitized = _escape_newlines_in_json_strings(sanitized)
    sanitized = re.sub(r",(\s*[}\]])", r"\1", sanitized)
    return sanitized


def _coerce_slides_payload(payload) -> list:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("slides", "cards", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    raise ValueError("슬라이드 배열 형태로 변환하지 못했습니다.")


def _escape_newlines_in_json_strings(text: str) -> str:
    result = []
    in_string = False
    escaped = False

    for ch in text:
        if ch == '"' and not escaped:
            in_string = not in_string
            result.append(ch)
            continue

        if ch == "\\" and not escaped:
            escaped = True
            result.append(ch)
            continue

        if ch in ("\n", "\t") and in_string:
            result.append("\\n" if ch == "\n" else "\\t")
        else:
            result.append(ch)

        escaped = False

    return "".join(result)


def _extract_balanced_json(text: str) -> str:
    """문자열 내부 괄호를 무시하고 첫 번째 완전한 JSON 덩어리를 추출한다."""
    if not text:
        return ""

    opening = text[0]
    if opening not in "[{":
        return ""
    closing = "]" if opening == "[" else "}"

    depth = 0
    in_string = False
    escaped = False

    for index, ch in enumerate(text):
        if ch == '"' and not escaped:
            in_string = not in_string
        elif not in_string:
            if ch == opening:
                depth += 1
            elif ch == closing:
                depth -= 1
                if depth == 0:
                    return text[:index + 1]

        if ch == "\\" and not escaped:
            escaped = True
        else:
            escaped = False

    return ""


def _validate_slides(slides: list):
    """슬라이드 텍스트를 정리하고 문장 끝맺음을 자연스럽게 맞춘다."""
    for i, s in enumerate(slides):
        for key in ("title", "subtitle", "body", "cta"):
            if key in s and isinstance(s[key], str):
                s[key] = " ".join(s[key].split())

        if s.get("type") == "thumbnail":
            s["subtitle"] = _normalize_sentence_ending(s.get("subtitle", ""))
            if len(s.get("title", "")) > 20:
                logger.warning(f"slides[{i}] title 20자 초과")
            if len(s.get("subtitle", "")) > 25:
                logger.warning(f"slides[{i}] subtitle 25자 초과")
        else:
            s["body"] = _rewrite_to_friendly_style(s.get("body", ""))
            if len(s.get("body", "")) < 38:
                s["body"] = _expand_short_body(s.get("title", ""), s.get("body", ""))
            s["body"] = _normalize_sentence_ending(s.get("body", ""))
            if len(s.get("title", "")) > 20:
                logger.warning(f"slides[{i}] title 20자 초과")
            if len(s.get("cta", "")) > 15:
                logger.warning(f"slides[{i}] cta 15자 초과")


def _demo_slides(topic: str) -> list:
    """API 키 없을 때 사용할 데모 슬라이드"""
    short_title = topic or "오늘의 트렌드"
    return [
        {
            "type": "thumbnail",
            "badge": "TREND",
            "title": short_title,
            "subtitle": f"요즘 흐름을 빠르게 읽을 수 있게 정리했어요.",
            "image_prompt": f"photorealistic, real camera photo, object-focused scene, natural lighting, clean composition, negative space on left bottom, no people if possible, no face close-up, no readable text, no readable letters, no readable numbers, no readable signage, no readable logo, no watermark, no poster, no cover design, no illustration, no cgi, no 3d render, any possible text must be naturally blurred or unreadable, visually represent the topic with objects, space, or environment: {topic}",
        },
        {
            "type": "content",
            "title": "핵심 포인트 정리",
            "body": f"{short_title}에서 먼저 봐야 할 핵심만 골라봤어요. 바로 이해할 수 있게 정리했어요",
            "cta": "핵심부터 확인!",
            "image_prompt": f"photorealistic, real camera photo, object-focused or environment-focused scene, natural lighting, no people if possible, no face close-up, no readable text, no readable letters, no readable numbers, no readable signage, no readable logo, no watermark, no poster, no cover design, no illustration, no cgi, no 3d render, any possible text must be naturally blurred or unreadable, clean lower area for Korean caption, visual summary of {topic}",
        },
        {
            "type": "content",
            "title": "왜 주목받을까",
            "body": f"지금 이 주제가 더 중요해진 이유를 짚어봤어요. 흐름을 보면 더 쉽게 와닿아요",
            "cta": "이유 바로 보기",
            "image_prompt": f"photorealistic, real camera photo, object-focused or environment-focused scene, natural lighting, no people if possible, no face close-up, no readable text, no readable letters, no readable numbers, no readable signage, no readable logo, no watermark, no poster, no cover design, no illustration, no cgi, no 3d render, any possible text must be naturally blurred or unreadable, clean lower area for Korean caption, explain why {topic} is important using environment or objects",
        },
        {
            "type": "content",
            "title": "실전 적용 팁",
            "body": f"이 주제를 일상에 자연스럽게 쓰는 방법을 담았어요. 바로 따라 하기 편하게 풀었어요",
            "cta": "바로 써먹기",
            "image_prompt": f"photorealistic, real camera photo, object-focused or environment-focused scene, natural lighting, no people if possible, no face close-up, no readable text, no readable letters, no readable numbers, no readable signage, no readable logo, no watermark, no poster, no cover design, no illustration, no cgi, no 3d render, any possible text must be naturally blurred or unreadable, clean lower area for Korean caption, practical everyday scene about {topic} using tools, desk, or space",
        },
        {
            "type": "content",
            "title": "마무리 체크",
            "body": f"마지막으로 챙기면 좋은 포인트를 담았어요. 저장해두고 다시 보면 더 좋아요",
            "cta": "저장해두기",
            "image_prompt": f"photorealistic, real camera photo, object-focused or environment-focused scene, natural lighting, no people if possible, no face close-up, no readable text, no readable letters, no readable numbers, no readable signage, no readable logo, no watermark, no poster, no cover design, no illustration, no cgi, no 3d render, any possible text must be naturally blurred or unreadable, clean lower area for Korean caption, closing summary visual for {topic} with calm realistic composition",
        },
    ]


def _rewrite_to_friendly_style(text: str) -> str:
    """딱딱한 종결을 가볍게 해요체로 바꾼다."""
    if not text:
        return text

    replacements = [
        (r"입니다\.", "이에요."),
        (r"입니다$", "이에요"),
        (r"합니다\.", "해요."),
        (r"합니다$", "해요"),
        (r"해야 한다\.", "해야 해요."),
        (r"해야 한다$", "해야 해요"),
        (r"해야 합니다\.", "해야 해요."),
        (r"해야 합니다$", "해야 해요"),
        (r"놓치지 않게 한다\.", "놓치지 않게 도와줘요."),
        (r"놓치지 않게 한다$", "놓치지 않게 도와줘요"),
        (r"못한다\.", "못해요."),
        (r"못한다$", "못해요"),
        (r"된다\.", "돼요."),
        (r"된다$", "돼요"),
        (r"좋다\.", "좋아요."),
        (r"좋다$", "좋아요"),
        (r"있다\.", "있어요."),
        (r"있다$", "있어요"),
        (r"없다\.", "없어요."),
        (r"없다$", "없어요"),
        (r"보인다\.", "보여요."),
        (r"보인다$", "보여요"),
        (r"기억하지 못한다\.", "기억하지 못해요."),
        (r"기억하지 못한다$", "기억하지 못해요"),
        (r"정리된다\.", "정리돼요."),
        (r"정리된다$", "정리돼요"),
        (r"유지된다\.", "유지돼요."),
        (r"유지된다$", "유지돼요"),
        (r"만든다\.", "만들어요."),
        (r"만든다$", "만들어요"),
    ]

    normalized = text.strip()
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)
    return normalized


def _expand_short_body(title: str, body: str) -> str:
    """너무 짧은 본문은 두 줄 정도 보이도록 살짝 확장한다."""
    if not body:
        body = f"{title}을 더 현실적으로 이해할 수 있게 풀어봤어요."

    if body.endswith("."):
        body = body[:-1]

    if len(body) >= 28:
        return body

    extra = "요즘 흐름까지 같이 보면 더 선명하게 읽혀요."
    if body.endswith("요"):
        return f"{body}. {extra}"
    return f"{body}예요. {extra}"


def _normalize_sentence_ending(text: str) -> str:
    """문장이 어색하게 끊기지 않도록 끝맺음을 가볍게 정리한다."""
    if not text:
        return text

    normalized = text.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.rstrip(",;:")
    if normalized.endswith("..."):
        normalized = normalized[:-3].rstrip()
    if normalized.endswith(".."):
        normalized = normalized[:-2].rstrip()

    if normalized.endswith(("요", "죠", "돼", "돼요", "이에요", "예요", "합니다", "해요")):
        return normalized + "." if not normalized.endswith(".") else normalized

    if normalized.endswith((".", "!", "?")):
        return normalized

    return normalized


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    slides = generate_slides("2026 직장인 아침 루틴 5가지")
    print(json.dumps(slides, ensure_ascii=False, indent=2))
