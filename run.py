"""
run.py — 카드뉴스 파이프라인 진입점
사용법:
  python run.py              # 트렌드 자동 분석 → 주제 자동 선정 → 카드 생성
  python run.py "주제"       # 주제 직접 지정 → 카드 생성
"""

import sys
import argparse
import os
import json
import shutil
import logging
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return None

load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")


def _build_feed_upload_bundle(output_dir: str, output_files: list, feed_text_path: str) -> str:
    """인스타 업로드용 PNG와 텍스트를 한 폴더에 모은다."""
    upload_dir = os.path.join(output_dir, "feed_upload")
    os.makedirs(upload_dir, exist_ok=True)

    png_files = [path for path in output_files if path.lower().endswith(".png")]
    for path in png_files:
        shutil.copy2(path, os.path.join(upload_dir, os.path.basename(path)))

    shutil.copy2(feed_text_path, os.path.join(upload_dir, os.path.basename(feed_text_path)))
    return upload_dir


def _parse_args():
    parser = argparse.ArgumentParser(description="인스타 카드뉴스 생성 파이프라인")
    parser.add_argument("topic", nargs="?", help="직접 생성할 주제")
    parser.add_argument(
        "--image-style",
        dest="image_style_name",
        help="이미지 분위기 프리셋 이름 (default, warm_lifestyle, clean_minimal, moody_editorial, bright_magazine, custom)",
    )
    parser.add_argument(
        "--generator-hint",
        dest="generator_hint",
        help="슬라이드 image_prompt 생성 시 반영할 한국어 분위기 힌트",
    )
    parser.add_argument(
        "--image-prompt-hint",
        dest="image_prompt_hint",
        help="최종 이미지 모델 프롬프트에 반영할 짧은 영어 힌트",
    )
    parser.add_argument(
        "--no-text",
        action="store_true",
        help="이미지에서 읽히는 글자, 로고, 간판을 강하게 배제",
    )
    parser.add_argument(
        "--image-mode",
        choices=["black_bg", "neutral_landscape"],
        help="이미지 생성 모드 강제 지정 (검정 배경 또는 주제 무관 풍경)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    logger.info("=" * 50)
    logger.info("카드뉴스 파이프라인 시작")
    logger.info("=" * 50)

    # ── Step 1: 주제 결정 ──
    if args.topic:
        topic = args.topic
        logger.info(f"[Step 1] 주제 직접 지정: {topic}")
    else:
        logger.info("[Step 1] 트렌드 분석으로 주제 자동 선정...")
        from trend import analyze_trends
        result = analyze_trends()
        topic = result["topic"]
        logger.info(f"[Step 1] 선정된 주제: {topic} (urgency: {result.get('urgency', 'N/A')})")

    # ── 출력 디렉토리 생성 ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = os.path.join(os.path.dirname(__file__), "output", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"출력 디렉토리: {output_dir}")

    # ── Step 2: 슬라이드 콘텐츠 생성 ──
    from image_style_config import build_image_style
    image_style = build_image_style(
        style_name=args.image_style_name,
        generator_hint=args.generator_hint,
        image_prompt_hint=args.image_prompt_hint,
        no_text=args.no_text,
        image_mode=args.image_mode,
    )
    logger.info(
        f"[Step 2] 이미지 분위기 프리셋: {image_style.get('display_name', image_style.get('style_key', 'default'))}"
    )
    logger.info("[Step 3] 슬라이드 콘텐츠 생성 중...")
    from generator import generate_slides, generate_feed_text
    slides = generate_slides(topic, image_style=image_style)
    logger.info(f"[Step 3] 슬라이드 {len(slides)}장 생성 완료")

    # 슬라이드 JSON 저장
    slides_path = os.path.join(output_dir, "slides.json")
    with open(slides_path, "w", encoding="utf-8") as f:
        json.dump(slides, f, ensure_ascii=False, indent=2)

    logger.info("[Step 3] 피드용 평문 텍스트 생성 중...")
    feed_text = generate_feed_text(topic, slides)
    feed_text_path = os.path.join(output_dir, "feed_text.txt")
    with open(feed_text_path, "w", encoding="utf-8") as f:
        f.write(feed_text)
    logger.info("[Step 3] 피드용 텍스트 저장 완료: feed_text.txt")

    # ── Step 3: 이미지 생성 ──
    logger.info("[Step 4] 슬라이드 이미지 생성 중...")
    from image import generate_image
    slide_image_paths = []
    for i, slide in enumerate(slides):
        reuse_index = slide.get("reuse_image_from")
        if isinstance(reuse_index, int) and 0 <= reuse_index < len(slide_image_paths):
            reused_path = slide_image_paths[reuse_index]
            slide_image_paths.append(reused_path)
            logger.info(f"[Step 4] slides[{i}] slides[{reuse_index}] 이미지 재사용")
            continue

        image_prompt = slide.get("image_prompt", "").strip()
        if not image_prompt:
            logger.info(f"[Step 4] slides[{i}] 이미지 프롬프트 없음 → 스킵")
            slide_image_paths.append("")
            continue

        image_filename = f"slide_{i+1:02d}.png"
        image_path = generate_image(image_prompt, output_dir, image_filename, image_style=image_style)
        slide_image_paths.append(image_path)
        logger.info(f"[Step 4] slides[{i}] 이미지 생성 완료: {image_filename}")

    # ── Step 4: PNG 렌더링 ──
    logger.info("[Step 5] PNG 렌더링 중...")
    from renderer import render_cards
    output_files = render_cards(slides, slide_image_paths, output_dir)
    output_files.append(feed_text_path)
    logger.info(f"[Step 5] 렌더링 완료: {len(output_files)}개 파일")

    logger.info("[Step 6] 업로드용 폴더 정리 중...")
    feed_upload_dir = _build_feed_upload_bundle(output_dir, output_files, feed_text_path)
    logger.info(f"[Step 6] 업로드용 폴더 생성 완료: {feed_upload_dir}")

    # ── 결과 요약 ──
    logger.info("=" * 50)
    logger.info("파이프라인 완료!")
    logger.info(f"주제: {topic}")
    logger.info(f"슬라이드: {len(slides)}장")
    logger.info(f"출력 폴더: {output_dir}")
    logger.info(f"업로드 폴더: {feed_upload_dir}")
    for f in output_files:
        logger.info(f"  → {os.path.basename(f)}")
    logger.info("=" * 50)

    return output_dir, output_files


if __name__ == "__main__":
    main()
