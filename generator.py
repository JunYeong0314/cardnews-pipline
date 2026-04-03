"""
generator.py — Claude Haiku 슬라이드 콘텐츠 생성
"""

import os
import json
import logging
import re
from typing import Optional

from dotenv import load_dotenv
from image_style_config import get_image_style

load_dotenv()
logger = logging.getLogger(__name__)
GENERATION_MODEL = "claude-haiku-4-5-20251001"
MAX_GENERATION_ATTEMPTS = 3
DEFAULT_FEED_HASHTAGS = [
    "#기록공유",
    "#공유페이지",
    "#메모앱",
    "#기록앱",
    "#생산성앱",
    "#앱추천",
    "#디지털페이지",
    "#DigitalPage",
]


def generate_slides(topic: str, image_style: Optional[dict] = None) -> list:
    """주제를 받아 슬라이드 JSON 리스트를 반환한다."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY 없음 → 데모 슬라이드 반환")
        return _demo_slides(topic)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    style = image_style or get_image_style()
    prompt = _build_generation_prompt(topic, style)

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
            slides = _append_promo_slide(slides, topic)
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


def generate_feed_text(topic: str, slides: list) -> str:
    """슬라이드 내용을 바탕으로 인스타 피드용 평문 텍스트를 생성한다."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY 없음 → 데모 피드 텍스트 반환")
        return _build_demo_feed_text(topic, slides)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_feed_text_prompt(topic, slides)

    last_error = None
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        try:
            response = client.messages.create(
                model=GENERATION_MODEL,
                max_tokens=160,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = _extract_text_from_response(response)
            summary_line = _normalize_feed_text(text)
            composed = _compose_feed_text(summary_line, topic, slides)
            if composed:
                logger.info("피드 텍스트 생성 완료")
                return composed
            raise ValueError("빈 피드 텍스트가 생성되었습니다.")
        except Exception as e:
            last_error = e
            preview = text[:240].replace("\n", "\\n") if "text" in locals() else ""
            if preview:
                logger.warning(f"피드 텍스트 응답 미리보기: {preview}")
            logger.warning(f"피드 텍스트 생성 실패 (시도 {attempt}/{MAX_GENERATION_ATTEMPTS}): {e}")

    logger.error(f"피드 텍스트 생성 오류: {last_error}")
    return _build_demo_feed_text(topic, slides)


def _build_generation_prompt(topic: str, image_style: Optional[dict] = None) -> str:
    style = image_style or get_image_style()
    style_name = style.get("display_name", "Default")
    style_hint = style.get("generator_hint", "").strip()

    return f"""당신은 인스타그램 카드뉴스 콘텐츠 작성자이다.

주제: {topic}

현재 이미지 분위기 프리셋:
- 이름: {style_name}
- 가이드: {style_hint or "기본 실사형 에디토리얼 톤을 유지하라."}

아래 규칙을 반드시 지켜라:
1. 슬라이드 5장을 만들어라
2. slides[0]은 썸네일이다:
   - badge: 카테고리 태그 (예: "자기계발", "건강") 8자 이내
   - title: 메인 제목, 반드시 20자 이내
   - subtitle: 부제목, 25자 이내
   - subtitle은 가능하면 한 줄로 보이도록 아주 짧게 작성하고, 정말 필요할 때만 자연스럽게 2줄까지 허용하라
   - subtitle은 억지로 2줄 분량을 채우지 말고, 한 줄이면 한 줄로 끝내라
   - subtitle은 조사나 어미가 어색하게 잘리지 않는 자연스러운 완결형 한 문장으로 작성하라
   - 한 단어만 다음 줄에 덜렁 떨어질 수 있는 애매한 길이는 피하고 더 짧고 선명하게 압축하라
   - 수식어를 줄이고 핵심만 남겨라
   - image_prompt: 영어로 된 배경 이미지 프롬프트
   - image_prompt는 짧고 간단한 영어 장면 설명만 써라
   - image_prompt는 4~8개 영어 단어의 아주 짧은 명사형 프레이즈로 작성하라
   - 동작 묘사보다 사물, 공간, 풍경 같은 장면 핵심만 남겨라
   - 스타일, 금지어, 카메라 조건은 쓰지 말고 장면 단어만 남겨라
   - image_prompt는 위 이미지 분위기 프리셋의 감성을 반영하되, 장면의 핵심 대상과 맥락이 먼저 읽히게 작성하라
   - image_prompt는 주제를 직접 보여주는 실사형 장면이어야 한다
   - 사람, 얼굴, 손은 쓰지 말고 사물, 공간, 풍경 중심으로 작성하라
   - 주제와 어울리는 자연스러운 실사 장면을 우선하라
   - 이미지 톤은 주제의 분위기에 맞춰라
   - 아침, 식사, 건강, 습관, 회복, 루틴, 생산성처럼 밝은 생활형 주제는 밝고 산뜻한 자연광, 아침 햇살, 신선한 공기감이 느껴지게 구성하라
   - 위기, 불안, 범죄, 사고, 전쟁, 상실처럼 무거운 주제일 때만 어둡고 긴장감 있는 톤을 사용하라
   - 아침 식사나 건강 주제는 카페/매장보다 집 주방, 식탁, 창가, 햇빛이 드는 생활 공간을 우선하라
   - 간판, 포스터, 제품 포장, 라벨, 메뉴판처럼 글자가 생기기 쉬운 장면은 피하라
   - 글자, 숫자, 로고, 라벨, 인쇄물은 읽히면 안 되고 생기더라도 흐릿해야 한다
   - illustration, painting, 3d render, cgi 느낌은 절대 피하라
   - 왼쪽 하단에 큰 제목이 들어갈 여백이 있도록 구성
   - 예시: "sunlit home breakfast table with toast fruit and orange juice"
3. slides[1~4]는 콘텐츠이다:
   - title: 소제목, 반드시 20자 이내
   - body: 본문
   - body는 가능하면 2줄에서 3줄 안에 들어오도록 간결하게 작성하라
   - 다만 의미 전달에 꼭 필요하면 3줄을 넘어도 되며, 억지로 줄이느라 문장이 부자연스럽거나 정보가 빠지지 않게 하라
   - 본문은 두 문장을 기본으로 하되, 더 자연스러운 설명을 위해 약간 길어지는 것은 허용한다
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
   - image_prompt는 4~8개 영어 단어의 아주 짧은 명사형 프레이즈로 작성하라
   - 동작 묘사보다 사물, 공간, 풍경 같은 장면 핵심만 남겨라
   - 스타일, 금지어, 카메라 조건은 쓰지 말고 장면 단어만 남겨라
   - image_prompt는 위 이미지 분위기 프리셋의 감성을 반영하되, 장면의 핵심 대상과 맥락이 먼저 읽히게 작성하라
   - image_prompt는 각 슬라이드 내용과 직접 관련된 실사형 장면이어야 한다
   - 실제 뉴스/다큐/라이프스타일 사진처럼 보일 장면 설명이어야 한다
   - 사람, 얼굴, 손은 쓰지 말고 물건, 장소, 풍경, 환경 디테일을 우선하라
   - 하단에 텍스트가 잘 보이도록 아래쪽 구도가 단순해야 한다
   - 주제와 어울리는 자연스러운 실사 장면을 우선하라
   - 이미지 톤은 주제의 분위기에 맞춰라
   - 아침, 식사, 건강, 습관, 회복, 루틴, 생산성처럼 밝은 생활형 주제는 밝고 산뜻한 자연광, 아침 햇살, 신선한 공기감이 느껴지게 구성하라
   - 위기, 불안, 범죄, 사고, 전쟁, 상실처럼 무거운 주제일 때만 어둡고 긴장감 있는 톤을 사용하라
   - 아침 식사나 건강 주제는 카페/매장보다 집 주방, 식탁, 창가, 햇빛이 드는 생활 공간을 우선하라
   - 간판, 포스터, 제품 포장, 라벨, 메뉴판처럼 글자가 생기기 쉬운 장면은 피하라
   - 글자, 숫자, 로고, 라벨, 인쇄물은 읽히면 안 되고 생기더라도 흐릿해야 한다
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


def _build_feed_text_prompt(topic: str, slides: list) -> str:
    slide_summaries = []
    for index, slide in enumerate(slides):
        if slide.get("type") == "promo":
            continue
        if slide.get("type") == "thumbnail":
            slide_summaries.append(
                f"{index + 1}. 썸네일 - 제목: {slide.get('title', '')} / 부제: {slide.get('subtitle', '')}"
            )
            continue

        slide_summaries.append(
            f"{index + 1}. 본문 - 제목: {slide.get('title', '')} / 내용: {slide.get('body', '')}"
        )

    slides_text = "\n".join(slide_summaries)

    return f"""당신은 인스타그램 피드용 한 줄 요약문을 작성하는 에디터이다.

주제: {topic}

슬라이드 요약:
{slides_text}

아래 규칙을 반드시 지켜라:
1. 위 슬라이드 내용을 바탕으로 첫 줄에 들어갈 한국어 한 줄 요약만 작성하라
2. 전체 내용을 한 문장으로만 압축하라
3. 줄바꿈은 절대 넣지 마라
4. 해시태그, 번호, 불릿, 따옴표, 설명 문구를 쓰지 마라
5. 길이는 짧고 간결하게 유지하되 핵심이 바로 읽히게 하라
6. 말투는 친절하고 자연스러운 해요체로 작성하라
7. 인스타 피드 첫 줄처럼 저장하고 싶어지는 요약 느낌으로 작성하라
8. 마크다운, 설명, 코드펜스 없이 한 줄 문장만 출력하라"""


def _extract_text_from_response(response) -> str:
    parts = []
    for block in response.content:
        if getattr(block, "type", "") == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _normalize_feed_text(text: str) -> str:
    normalized = text.strip()
    if "```" in normalized:
        parts = [part.strip() for part in normalized.split("```") if part.strip()]
        normalized = next((part for part in parts if "\n" in part or len(part) > 20), normalized)
        if normalized.lower().startswith("text"):
            normalized = normalized[4:].strip()

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if not lines:
        return ""

    summary = lines[0]
    summary = re.sub(r"^[-*0-9.\s]+", "", summary).strip()
    summary = re.sub(r"#\S+", "", summary).strip()
    summary = " ".join(summary.split())
    return summary


def _compose_feed_text(summary_line: str, topic: str, slides: list) -> str:
    summary = summary_line.strip() if summary_line else ""
    if not summary:
        summary = _build_feed_summary_fallback(topic, slides)

    thumbnail_title = _get_thumbnail_title(slides, topic)
    hashtag_line = _build_demo_hashtags(topic, slides)
    return (
        f"{summary}\n"
        f"{thumbnail_title}, 공유하고 저장하세요!\n"
        "디지털페이지 다운로드는 프로필 링크에서\n\n"
        f"{hashtag_line}"
    )


def _ensure_hashtag_line(text: str, topic: str, slides: list) -> str:
    normalized = text.strip()
    if not normalized:
        return _build_demo_feed_text(topic, slides)

    lines = [line.rstrip() for line in normalized.splitlines()]
    non_empty_lines = [line for line in lines if line.strip()]
    if non_empty_lines and non_empty_lines[-1].lstrip().startswith("#"):
        for idx in range(len(lines) - 1, -1, -1):
            if lines[idx].strip():
                lines[idx] = _merge_default_hashtags(lines[idx], topic, slides)
                break
        return "\n".join(lines).strip()

    hashtag_line = _build_demo_hashtags(topic, slides)
    return f"{normalized}\n\n{hashtag_line}"


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

        if "image_prompt" in s and isinstance(s["image_prompt"], str):
            s["image_prompt"] = _sanitize_image_prompt(
                s["image_prompt"],
                s.get("type", ""),
                s.get("title", ""),
            )

        if s.get("type") == "thumbnail":
            s["subtitle"] = _normalize_sentence_ending(s.get("subtitle", ""))
            if len(s.get("title", "")) > 20:
                logger.warning(f"slides[{i}] title 20자 초과")
            if len(s.get("subtitle", "")) > 25:
                logger.warning(f"slides[{i}] subtitle 25자 초과")
        elif s.get("type") == "content":
            s["body"] = _rewrite_to_friendly_style(s.get("body", ""))
            if len(s.get("body", "")) < 38:
                s["body"] = _expand_short_body(s.get("title", ""), s.get("body", ""))
            s["body"] = _normalize_sentence_ending(s.get("body", ""))
            if len(s.get("title", "")) > 20:
                logger.warning(f"slides[{i}] title 20자 초과")
            if len(s.get("cta", "")) > 15:
                logger.warning(f"slides[{i}] cta 15자 초과")
        elif s.get("type") == "promo":
            s["subtitle"] = _normalize_sentence_ending(s.get("subtitle", ""))
            s["cta"] = _normalize_sentence_ending(s.get("cta", ""))


def _sanitize_image_prompt(prompt: str, slide_type: str, title: str) -> str:
    normalized = " ".join(prompt.split()).strip()
    lowered = normalized.lower()
    banned_words = {
        "hand", "hands", "finger", "fingers", "palm", "palms",
        "arm", "arms", "person", "people", "human", "man", "woman",
        "boy", "girl", "child", "children", "crowd", "face", "portrait",
        "selfie", "point", "pointing", "hold", "holding", "touch", "touching",
        "grab", "grabbing", "pick", "picking", "gesture", "gesturing",
        "planting", "farmer", "gardeners", "gardener",
        "photorealistic", "real", "camera", "photo", "natural", "lighting",
        "clean", "composition", "scene", "visual", "summary", "practical",
        "everyday", "about", "using", "with", "caption"
    }
    tokens = re.findall(r"[0-9a-zA-Z가-힣_-]+", lowered)
    kept = [token for token in tokens if token not in banned_words]
    kept = kept[:8]

    if not kept:
        kept = ["objects", "space"]
        if slide_type == "thumbnail":
            kept.insert(0, "symbolic")

    core = " ".join(kept)
    return f"{core}, objects only, no people, no hands, no text"


def _demo_slides(topic: str) -> list:
    """API 키 없을 때 사용할 데모 슬라이드"""
    short_title = topic or "오늘의 트렌드"
    slides = [
        {
            "type": "thumbnail",
            "badge": "TREND",
            "title": short_title,
            "subtitle": f"요즘 흐름을 빠르게 읽을 수 있게 정리했어요.",
            "image_prompt": f"symbolic objects for {topic}",
        },
        {
            "type": "content",
            "title": "핵심 포인트 정리",
            "body": f"{short_title}에서 먼저 봐야 할 핵심만 골라봤어요. 바로 이해할 수 있게 정리했어요",
            "cta": "핵심부터 확인!",
            "image_prompt": f"objects about {topic}",
        },
        {
            "type": "content",
            "title": "왜 주목받을까",
            "body": f"지금 이 주제가 더 중요해진 이유를 짚어봤어요. 흐름을 보면 더 쉽게 와닿아요",
            "cta": "이유 바로 보기",
            "image_prompt": f"environment for {topic}",
        },
        {
            "type": "content",
            "title": "실전 적용 팁",
            "body": f"이 주제를 일상에 자연스럽게 쓰는 방법을 담았어요. 바로 따라 하기 편하게 풀었어요",
            "cta": "바로 써먹기",
            "image_prompt": f"practical objects for {topic}",
        },
        {
            "type": "content",
            "title": "마무리 체크",
            "body": f"마지막으로 챙기면 좋은 포인트를 담았어요. 저장해두고 다시 보면 더 좋아요",
            "cta": "저장해두기",
            "image_prompt": f"calm objects for {topic}",
        },
    ]
    return _append_promo_slide(slides, topic)


def _append_promo_slide(slides: list, topic: str) -> list:
    if any(slide.get("type") == "promo" for slide in slides):
        return slides

    appended = list(slides)
    appended.append(_build_promo_slide(topic))
    return appended


def _build_promo_slide(topic: str) -> dict:
    return {
        "type": "promo",
        "title": "메모는 남기고\n정리는 AI에게 맡기세요",
        "subtitle": "중요한 내용만 더 또렷하게 정리되는\n디지털페이지의 마지막 한 장",
        "cta": "다운로드는 프로필에서 확인",
        "image_prompt": "",
        "reuse_image_from": 0,
    }


def _build_demo_feed_text(topic: str, slides: list) -> str:
    summary = _build_feed_summary_fallback(topic, slides)
    return _compose_feed_text(summary, topic, slides)


def _build_demo_hashtags(topic: str, slides: list) -> str:
    tags = []

    normalized_topic = re.sub(r"[^\w가-힣 ]+", " ", topic).strip()
    compact_topic = normalized_topic.replace(" ", "")
    if compact_topic:
        tags.append(f"#{compact_topic}")

    for slide in slides:
        if slide.get("type") != "content":
            continue

        title = re.sub(r"[^\w가-힣 ]+", " ", slide.get("title", "")).strip().replace(" ", "")
        if title:
            tags.append(f"#{title}")

    broad_tags = [
        "#인스타정보",
        "#카드뉴스",
        "#트렌드",
        "#상식",
        "#스토리",
        "#콘텐츠",
        "#인사이트",
        "#요즘이야기",
    ]
    tags.extend(broad_tags)
    tags.extend(DEFAULT_FEED_HASHTAGS)

    unique_tags = []
    seen = set()
    for tag in tags:
        if not tag or tag in seen:
            continue
        unique_tags.append(tag)
        seen.add(tag)

    return " ".join(unique_tags)


def _build_feed_summary_fallback(topic: str, slides: list) -> str:
    content_titles = []
    for slide in slides:
        if slide.get("type") != "content":
            continue
        title = slide.get("title", "").strip()
        if title:
            content_titles.append(title)

    if content_titles:
        return f"{topic}의 핵심은 {content_titles[0]}부터 가볍게 이해해보는 거예요."
    return f"{topic}의 핵심 흐름만 한 번에 이해할 수 있게 정리했어요."


def _get_thumbnail_title(slides: list, topic: str) -> str:
    for slide in slides:
        if slide.get("type") == "thumbnail":
            title = slide.get("title", "").strip()
            if title:
                return title
    return topic


def _merge_default_hashtags(existing_line: str, topic: str, slides: list) -> str:
    tags = []
    for token in existing_line.split():
        if token.startswith("#"):
            tags.append(token)

    tags.extend(_build_demo_hashtags(topic, slides).split())

    unique_tags = []
    seen = set()
    for tag in tags:
        if not tag or not tag.startswith("#") or tag in seen:
            continue
        unique_tags.append(tag)
        seen.add(tag)

    return " ".join(unique_tags)


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
