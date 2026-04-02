"""
이미지 분위기 설정 파일.

기본값은 현재 파이프라인의 톤을 최대한 유지한다.
원할 때 ACTIVE_IMAGE_STYLE만 바꾸면 이미지 분위기를 선택적으로 조정할 수 있다.
"""

from copy import deepcopy
from typing import Optional


IMAGE_STYLE_PRESETS = {
    "default": {
        "display_name": "Default",
        "generator_hint": (
            "이미지 분위기는 현재 기본 톤을 유지하라. 과한 스타일링보다 자연스러운 실사형 "
            "라이프스타일/에디토리얼 사진 느낌을 우선하라."
        ),
        "image_prompt_hint": (
            "natural editorial realism, balanced everyday atmosphere, believable light, "
            "subtle visual variation without changing the core scene"
        ),
    },
    "warm_lifestyle": {
        "display_name": "Warm Lifestyle",
        "generator_hint": (
            "따뜻하고 생활감 있는 라이프스타일 사진 톤을 반영하라. 집, 책상, 창가, 나무 질감, "
            "부드러운 햇살, 편안한 공기감이 느껴지게 구성하라."
        ),
        "image_prompt_hint": (
            "warm lifestyle editorial mood, sunlit home atmosphere, soft golden light, "
            "cozy textures, calm everyday warmth"
        ),
    },
    "clean_minimal": {
        "display_name": "Clean Minimal",
        "generator_hint": (
            "정돈되고 미니멀한 사진 톤을 반영하라. 여백이 많고 구성이 단정하며, 배경 요소는 "
            "필요 이상으로 복잡하지 않게 하라."
        ),
        "image_prompt_hint": (
            "clean minimal editorial mood, simplified composition, generous negative space, "
            "tidy environment, crisp modern realism"
        ),
    },
    "moody_editorial": {
        "display_name": "Moody Editorial",
        "generator_hint": (
            "차분하고 깊이 있는 에디토리얼 사진 톤을 반영하라. 어두운 그림자와 분위기 있는 "
            "빛을 쓰되, 과장되지 않은 실사 감각을 유지하라."
        ),
        "image_prompt_hint": (
            "moody editorial realism, richer shadows, cinematic depth, restrained contrast, "
            "thoughtful magazine-style atmosphere"
        ),
    },
    "bright_magazine": {
        "display_name": "Bright Magazine",
        "generator_hint": (
            "밝고 세련된 매거진 화보 같은 사진 톤을 반영하라. 깨끗한 광량, 산뜻한 색감, 선명한 "
            "공간감이 느껴지게 하라."
        ),
        "image_prompt_hint": (
            "bright magazine editorial mood, airy daylight, fresh color separation, "
            "clean polished realism, premium lifestyle photo feel"
        ),
    },
    "custom": {
        "display_name": "Custom",
        "generator_hint": "",
        "image_prompt_hint": "",
    },
}


ACTIVE_IMAGE_STYLE = "default"

CUSTOM_IMAGE_STYLE = {
    "display_name": "Custom",
    "generator_hint": (
        "원하는 분위기를 여기에 한국어로 적으면 슬라이드용 image_prompt 생성에 반영된다."
    ),
    "image_prompt_hint": (
        "write your custom visual mood in English here for the final image model prompt"
    ),
}


def get_image_style(style_name: Optional[str] = None) -> dict:
    selected_name = style_name or ACTIVE_IMAGE_STYLE
    preset = IMAGE_STYLE_PRESETS.get(selected_name, IMAGE_STYLE_PRESETS["default"])

    if selected_name == "custom":
        merged = deepcopy(preset)
        merged.update(CUSTOM_IMAGE_STYLE)
        merged["style_key"] = "custom"
        return merged

    resolved = deepcopy(preset)
    resolved["style_key"] = selected_name
    return resolved
