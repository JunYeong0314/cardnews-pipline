"""
image.py — 배경 이미지 생성
fal.ai FLUX 사용. API 없으면 Pillow로 데모 이미지 생성.
"""

import os
import base64
import logging
import math
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from image_style_config import get_image_style

load_dotenv()
logger = logging.getLogger(__name__)

IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1350
FAL_IMAGE_MODEL = "fal-ai/flux-1/schnell"
FAL_GUIDANCE_SCALE = 5.0
FAL_INFERENCE_STEPS = 12
FAL_ACCELERATION = "none"


def generate_image(
    prompt: str,
    output_dir: str,
    filename: str = "bg_image.png",
    image_style: Optional[dict] = None,
) -> str:
    """배경 이미지를 생성한다. 반환: 파일 경로"""
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        logger.info("FAL_KEY 없음 → Pillow 데모 이미지 생성")
        return _create_demo_image(output_dir, filename)

    try:
        import fal_client
        os.environ["FAL_KEY"] = fal_key
        style = image_style or get_image_style()
        result = fal_client.subscribe(
            FAL_IMAGE_MODEL,
            arguments={
                "prompt": _build_photoreal_prompt(prompt, style),
                "image_size": {"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
                "num_images": 1,
                "enable_safety_checker": True,
                "guidance_scale": FAL_GUIDANCE_SCALE,
                "num_inference_steps": FAL_INFERENCE_STEPS,
                "acceleration": FAL_ACCELERATION,
                "output_format": "png",
            },
        )
        import httpx
        resp = httpx.get(result["images"][0]["url"], timeout=30)
        resp.raise_for_status()
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "wb") as f:
            f.write(resp.content)
        logger.info(f"이미지 생성 완료: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"fal.ai 오류: {e}")
        return _create_demo_image(output_dir, filename)


def _build_photoreal_prompt(prompt: str, image_style: Optional[dict] = None) -> str:
    """저비용 모델에서도 실사감을 높이기 위한 공통 프롬프트 보강."""
    style = image_style or get_image_style()
    visual_direction = _infer_visual_direction(prompt)
    style_hint = style.get("image_prompt_hint", "").strip()
    short_style = " ".join(style_hint.split()[:5])
    style_fragment = f", {short_style}" if short_style else ""
    core = _compress_core_prompt(prompt)
    return (
        f"{core}, {visual_direction}{style_fragment}, "
        "objects only, no people, no hands, no readable text, blur any text"
    )


def _compress_core_prompt(prompt: str) -> str:
    tokens = re.findall(r"[0-9a-zA-Z가-힣_-]+", prompt.lower())
    banned = {
        "people", "person", "human", "man", "woman", "boy", "girl",
        "child", "children", "crowd", "face", "portrait", "selfie",
        "hand", "hands", "finger", "fingers", "arm", "arms", "palm", "palms",
        "point", "pointing", "hold", "holding", "touch", "touching",
        "grab", "grabbing", "pick", "picking", "gesture", "gesturing",
        "photorealistic", "real", "camera", "photo", "natural", "lighting",
        "clean", "composition", "scene", "visual", "summary", "practical",
        "everyday", "about", "using", "with", "caption", "only"
    }
    kept = [token for token in tokens if token not in banned][:8]
    if not kept:
        kept = ["objects", "environment"]
    return " ".join(kept)


def _infer_visual_direction(prompt: str) -> str:
    lowered = prompt.lower()

    bright_keywords = (
        "breakfast", "morning", "brunch", "healthy", "health", "wellness",
        "habit", "routine", "energy", "focus", "productivity", "recovery",
        "fresh", "sunlight", "kitchen", "dining table", "home meal", "food"
    )
    dark_keywords = (
        "crime", "war", "accident", "anxiety", "depression", "danger",
        "violence", "disaster", "fear", "loss", "scam", "fraud", "crisis"
    )

    breakfast_keywords = (
        "breakfast", "morning meal", "morning", "kitchen", "dining table",
        "toast", "egg", "fruit", "yogurt", "granola", "coffee", "orange juice"
    )

    if any(keyword in lowered for keyword in bright_keywords):
        direction = "bright morning light"
    elif any(keyword in lowered for keyword in dark_keywords):
        direction = "serious natural light"
    else:
        direction = "natural daylight"

    if any(keyword in lowered for keyword in breakfast_keywords):
        direction += ", home kitchen"

    return direction


def _create_demo_image(output_dir: str, filename: str = "bg_image.png") -> str:
    """Pillow로 시네마틱 그라데이션 배경 이미지를 생성한다."""
    from PIL import Image, ImageDraw, ImageFilter

    width, height = IMAGE_WIDTH, IMAGE_HEIGHT
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 시네마틱 그라데이션: 깊은 보라-파랑 → 하단 어둡게
    for y in range(height):
        ratio = y / height
        r = int(45 + 50 * math.sin(ratio * math.pi * 0.5))
        g = int(25 + 40 * math.sin(ratio * math.pi * 0.3))
        b = int(80 + 70 * (1 - ratio))
        # 하단으로 갈수록 어둡게
        dark = max(0, 1 - ratio * 0.6)
        r = int(r * dark)
        g = int(g * dark)
        b = int(b * dark)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 빛 원형 효과 (상단 중앙)
    light_img = Image.new("RGB", (width, height), (0, 0, 0))
    light_draw = ImageDraw.Draw(light_img)
    cx, cy = 540, 350
    for radius in range(400, 0, -2):
        alpha = int(35 * (1 - radius / 400))
        color = (alpha, int(alpha * 0.7), int(alpha * 1.2))
        light_draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill=color)

    # 합성
    from PIL import ImageChops
    img = ImageChops.add(img, light_img)

    # 약간의 블러
    img = img.filter(ImageFilter.GaussianBlur(radius=3))

    output_path = os.path.join(output_dir, filename)
    img.save(output_path, "PNG", quality=95)
    logger.info(f"데모 이미지 생성 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    os.makedirs("output/test", exist_ok=True)
    print(generate_image("test", "output/test"))
