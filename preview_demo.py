"""
preview_demo.py - One-command local design preview without API keys.

Usage:
  python3 preview_demo.py
  python3 preview_demo.py "원하는 테스트 주제"
"""

import sys
import types
from pathlib import Path


def _install_dotenv_stub() -> None:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv


def main() -> None:
    topic = sys.argv[1] if len(sys.argv) > 1 else "이란의 호르무즈 해협 봉쇄"
    _install_dotenv_stub()

    import generator
    import image
    import renderer
    from image_style_config import get_image_style

    output_dir = Path("output/test_content_design")
    output_dir.mkdir(parents=True, exist_ok=True)
    image_style = get_image_style()

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
