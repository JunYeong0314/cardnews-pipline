"""
preview_demo.py - One-command local design preview without API keys.

Usage:
  python3 preview_demo.py
  python3 preview_demo.py "원하는 테스트 주제"
"""

import sys
import argparse
import types
from pathlib import Path


def _install_dotenv_stub() -> None:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv


def _parse_args():
    parser = argparse.ArgumentParser(description="API 없이 카드 디자인 프리뷰 생성")
    parser.add_argument("topic", nargs="?", default="이란의 호르무즈 해협 봉쇄", help="테스트 주제")
    parser.add_argument(
        "--image-style",
        dest="image_style_name",
        help="이미지 분위기 프리셋 이름",
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


def main() -> None:
    args = _parse_args()
    topic = args.topic
    _install_dotenv_stub()

    import generator
    import image
    import renderer
    from image_style_config import build_image_style

    output_dir = Path("output/test_content_design")
    output_dir.mkdir(parents=True, exist_ok=True)
    image_style = build_image_style(
        style_name=args.image_style_name,
        generator_hint=args.generator_hint,
        image_prompt_hint=args.image_prompt_hint,
        no_text=args.no_text,
        image_mode=args.image_mode,
    )

    slides = generator._demo_slides(topic)

    slide_image_paths = []
    for index, slide in enumerate(slides, start=1):
        reuse_index = slide.get("reuse_image_from")
        if isinstance(reuse_index, int) and 0 <= reuse_index < len(slide_image_paths):
            slide_image_paths.append(slide_image_paths[reuse_index])
            continue

        prompt = slide.get("image_prompt", "").strip()
        if not prompt:
            slide_image_paths.append("")
            continue

        filename = f"slide_{index:02d}.png"
        try:
            image_path = image.generate_image(prompt, str(output_dir), filename, image_style=image_style)
        except Exception as exc:
            print(f"image fallback: slide_{index:02d} skipped ({exc})")
            image_path = ""
        slide_image_paths.append(image_path)

    files = renderer.render_cards(slides, slide_image_paths, str(output_dir))
    preview_path = output_dir / "preview.html"

    print(f"topic: {topic}")
    print(f"image_style: {image_style.get('display_name', image_style.get('style_key', 'default'))}")
    print(f"preview: {preview_path.resolve()}")
    print("files:")
    for path in files:
        print(path)


if __name__ == "__main__":
    main()
