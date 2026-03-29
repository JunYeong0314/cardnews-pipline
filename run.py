"""
run.py — 카드뉴스 파이프라인 진입점
사용법:
  python run.py              # 트렌드 자동 분석 → 주제 자동 선정 → 카드 생성
  python run.py "주제"       # 주제 직접 지정 → 카드 생성
"""

import sys
import os
import json
import logging
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")


def main():
    logger.info("=" * 50)
    logger.info("카드뉴스 파이프라인 시작")
    logger.info("=" * 50)

    # ── Step 1: 주제 결정 ──
    if len(sys.argv) > 1:
        topic = sys.argv[1]
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
    logger.info("[Step 3] 슬라이드 콘텐츠 생성 중...")
    from generator import generate_slides
    slides = generate_slides(topic)
    logger.info(f"[Step 3] 슬라이드 {len(slides)}장 생성 완료")

    # 슬라이드 JSON 저장
    slides_path = os.path.join(output_dir, "slides.json")
    with open(slides_path, "w", encoding="utf-8") as f:
        json.dump(slides, f, ensure_ascii=False, indent=2)

    # ── Step 3: 이미지 생성 ──
    logger.info("[Step 4] 슬라이드 이미지 생성 중...")
    from image import generate_image
    slide_image_paths = []
    for i, slide in enumerate(slides):
        image_prompt = slide.get("image_prompt", "").strip()
        if not image_prompt:
            logger.info(f"[Step 4] slides[{i}] 이미지 프롬프트 없음 → 스킵")
            slide_image_paths.append("")
            continue

        image_filename = f"slide_{i+1:02d}.png"
        image_path = generate_image(image_prompt, output_dir, image_filename)
        slide_image_paths.append(image_path)
        logger.info(f"[Step 4] slides[{i}] 이미지 생성 완료: {image_filename}")

    # ── Step 4: PNG 렌더링 ──
    logger.info("[Step 5] PNG 렌더링 중...")
    from renderer import render_cards
    output_files = render_cards(slides, slide_image_paths, output_dir)
    logger.info(f"[Step 5] 렌더링 완료: {len(output_files)}개 파일")

    # ── 결과 요약 ──
    logger.info("=" * 50)
    logger.info("파이프라인 완료!")
    logger.info(f"주제: {topic}")
    logger.info(f"슬라이드: {len(slides)}장")
    logger.info(f"출력 폴더: {output_dir}")
    for f in output_files:
        logger.info(f"  → {os.path.basename(f)}")
    logger.info("=" * 50)

    return output_dir, output_files


if __name__ == "__main__":
    main()
