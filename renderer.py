"""
renderer.py — 카드뉴스 렌더링
1080×1350 카드를 HTML로 생성하고, Playwright가 있으면 PNG 변환.
"""

import os
import io
import base64
import logging
from html import escape
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return None

load_dotenv()
logger = logging.getLogger(__name__)

BRAND = {
    "name": "MYPAGE",
    "accent": "#2D6AFF",
}
PROMO_TEXT = "AI 메모 앱은 디지털페이지"
PROMO_BRAND = "digitalpage"
PROMO_LOGO_PATH = os.path.join(
    os.path.dirname(__file__),
    "assets",
    "branding",
    "logo.png",
)

CARD_WIDTH = 1080
CARD_HEIGHT = 1350
PREVIEW_SCALE = 0.5

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_cards(slides: list, slide_image_paths: list, output_dir: str) -> list:
    """슬라이드 리스트를 카드 파일로 렌더링한다."""
    os.makedirs(output_dir, exist_ok=True)

    slide_bg_b64 = []
    for image_path in slide_image_paths:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                slide_bg_b64.append(base64.b64encode(f.read()).decode())
        else:
            slide_bg_b64.append("")

    output_files = []

    # 1) HTML 카드 생성 (항상 생성 — 이것이 핵심 결과물)
    for i, slide in enumerate(slides):
        bg_b64 = slide_bg_b64[i] if i < len(slide_bg_b64) else ""
        if slide.get("type") == "thumbnail":
            html = _build_thumbnail_html(slide, bg_b64)
            filename = f"card_{i+1:02d}_thumbnail.html"
        elif slide.get("type") == "promo":
            html = _build_promo_html(slide, bg_b64)
            filename = f"card_{i+1:02d}_promo.html"
        else:
            html = _build_content_html(slide, i, len(slides), bg_b64)
            filename = f"card_{i+1:02d}_content.html"

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        output_files.append(filepath)
        logger.info(f"HTML 카드 생성: {filename}")

    # 2) 프리뷰 페이지 생성
    preview_path = _build_preview_page(slides, slide_bg_b64, output_dir)
    output_files.append(preview_path)

    # 3) Playwright가 있으면 PNG도 생성
    try:
        from playwright.sync_api import sync_playwright
        logger.info("Playwright 발견 → PNG 렌더링 시작")
        png_files = _render_with_playwright(slides, slide_bg_b64, output_dir)
        output_files.extend(png_files)
    except ImportError:
        logger.info("Playwright 없음 → HTML만 생성 (브라우저에서 열어 확인)")
        # PNG 변환 스크립트 생성
        _create_png_converter(output_dir)

    return output_files


def _render_with_playwright(slides, slide_bg_b64, output_dir):
    """Playwright로 HTML → PNG 렌더링"""
    from playwright.sync_api import sync_playwright

    png_files = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": CARD_WIDTH, "height": CARD_HEIGHT})

        for i, slide in enumerate(slides):
            bg_b64 = slide_bg_b64[i] if i < len(slide_bg_b64) else ""
            if slide.get("type") == "thumbnail":
                html = _build_thumbnail_html(slide, bg_b64)
                filename = f"card_{i+1:02d}_thumbnail.png"
            elif slide.get("type") == "promo":
                html = _build_promo_html(slide, bg_b64)
                filename = f"card_{i+1:02d}_promo.png"
            else:
                html = _build_content_html(slide, i, len(slides), bg_b64)
                filename = f"card_{i+1:02d}_content.png"

            page.set_content(html)
            page.wait_for_timeout(1000)  # 폰트 로드 대기

            filepath = os.path.join(output_dir, filename)
            page.screenshot(path=filepath, type="png")
            png_files.append(filepath)
            logger.info(f"PNG 렌더링 완료: {filename}")

        browser.close()
    return png_files


def _build_thumbnail_html(slide: dict, bg_b64: str) -> str:
    """썸네일 카드 HTML"""
    bg_url = f"data:image/png;base64,{bg_b64}" if bg_b64 else ""
    background_style = _background_style(slide, bg_url, "#d7d0c3")
    title = escape(slide.get("title", ""))
    subtitle = escape(slide.get("subtitle", ""))

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: {CARD_WIDTH}px;
    height: {CARD_HEIGHT}px;
    overflow: hidden;
    font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .card {{
    position: relative;
    width: {CARD_WIDTH}px;
    height: {CARD_HEIGHT}px;
    {background_style}
  }}
  .overlay {{
    position: absolute;
    inset: 0;
    background:
      linear-gradient(
        180deg,
        rgba(0,0,0,0.10) 0%,
        rgba(0,0,0,0.14) 38%,
        rgba(0,0,0,0.34) 100%
      ),
      linear-gradient(
        90deg,
        rgba(0,0,0,0.12) 0%,
        rgba(0,0,0,0.00) 42%
      );
  }}
  .grain {{
    position: absolute;
    inset: 0;
    background-image:
      radial-gradient(rgba(255,255,255,0.08) 0.7px, transparent 0.7px);
    background-size: 7px 7px;
    mix-blend-mode: soft-light;
    opacity: 0.28;
    pointer-events: none;
  }}
  .promo-strip {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #7553C4;
    color: #ffffff;
    font-size: 30px;
    font-weight: 900;
    letter-spacing: -0.02em;
    z-index: 3;
  }}
  .content {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 96px 72px;
    z-index: 1;
  }}
  .headline-shell {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 24px;
    width: min(920px, 100%);
    padding: 0;
  }}
  .bottom {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    max-width: 100%;
  }}
  .title {{
    font-size: 102px;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.06;
    letter-spacing: -0.06em;
    text-align: center;
    text-shadow:
      0 12px 34px rgba(0,0,0,0.42),
      0 4px 12px rgba(0,0,0,0.26),
      0 1px 0 rgba(0,0,0,0.28);
    -webkit-text-stroke: 1px rgba(0,0,0,0.12);
    word-break: keep-all;
  }}
  .meta {{
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255,255,255,0.94);
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.02em;
    text-shadow:
      0 8px 24px rgba(0,0,0,0.34),
      0 2px 6px rgba(0,0,0,0.24);
    max-width: 100%;
    text-align: center;
  }}
  .meta-text {{
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    line-height: 1.38;
    word-break: keep-all;
    max-width: 100%;
    text-wrap: balance;
  }}
  .subtitle {{
    display: none;
  }}
  .title-wrap {{
    display: flex;
    flex-direction: column;
    gap: 18px;
    align-items: center;
  }}
  .title-wrap.no-subtitle .meta {{
    display: none;
  }}
  .safe-shadow {{
    position: absolute;
    inset: 28% 14% 28% 14%;
    border-radius: 50%;
    background: radial-gradient(
      ellipse at center,
      rgba(0,0,0,0.14) 0%,
      rgba(0,0,0,0.08) 42%,
      rgba(0,0,0,0.00) 76%
    );
    filter: blur(32px);
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="promo-strip">{escape(PROMO_TEXT)}</div>
    <div class="overlay"></div>
    <div class="safe-shadow"></div>
    <div class="grain"></div>
    <div class="content">
      <div class="headline-shell">
        <div class="bottom">
          <div class="title-wrap {'no-subtitle' if not subtitle else ''}">
            <div class="title">{title}</div>
            <div class="meta">
              <span class="meta-text">{subtitle}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""


def _build_content_html(slide: dict, index: int, total: int, bg_b64: str) -> str:
    """콘텐츠 카드 HTML"""
    bg_url = f"data:image/png;base64,{bg_b64}" if bg_b64 else ""
    background_style = _background_style(slide, bg_url, "#2b2b2b")
    title = escape(slide.get("title", ""))
    body = escape(slide.get("body", ""))

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: {CARD_WIDTH}px;
    height: {CARD_HEIGHT}px;
    overflow: hidden;
    font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    -webkit-font-smoothing: antialiased;
    background: #111;
  }}
  .card {{
    position: relative;
    width: {CARD_WIDTH}px;
    height: {CARD_HEIGHT}px;
    {background_style}
    overflow: hidden;
  }}
  .overlay {{
    position: absolute;
    inset: 0;
    background:
      linear-gradient(
        180deg,
        rgba(0,0,0,0.05) 0%,
        rgba(0,0,0,0.08) 38%,
        rgba(0,0,0,0.30) 68%,
        rgba(0,0,0,0.64) 100%
      );
  }}
  .safe-shadow {{
    position: absolute;
    inset: auto 0 0 0;
    height: 42%;
    background: linear-gradient(
      180deg,
      rgba(0,0,0,0.00) 0%,
      rgba(0,0,0,0.18) 35%,
      rgba(0,0,0,0.54) 100%
    );
  }}
  .promo-strip {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #7553C4;
    color: #ffffff;
    font-size: 30px;
    font-weight: 900;
    letter-spacing: -0.02em;
    z-index: 3;
  }}
  .content {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 72px 48px 72px;
    z-index: 1;
  }}
  .bottom {{
    display: flex;
    flex-direction: column;
    gap: 24px;
    max-width: 78%;
    margin-left: 30px;
  }}
  .title {{
    font-size: 72px;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.16;
    letter-spacing: -0.055em;
    text-shadow:
      0 6px 18px rgba(0,0,0,0.46),
      0 2px 4px rgba(0,0,0,0.32);
    -webkit-text-stroke: 1px rgba(0,0,0,0.10);
    word-break: keep-all;
  }}
  .body {{
    font-size: 28px;
    font-weight: 500;
    color: rgba(255,255,255,0.96);
    line-height: 1.56;
    max-width: 92%;
    text-shadow:
      0 4px 14px rgba(0,0,0,0.5),
      0 1px 2px rgba(0,0,0,0.32);
    word-break: keep-all;
  }}
  .body-wrap {{
    display: flex;
    flex-direction: column;
    gap: 0;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="promo-strip">{escape(PROMO_TEXT)}</div>
    <div class="overlay"></div>
    <div class="safe-shadow"></div>
    <div class="content">
      <div class="bottom">
        <div class="title">{title}</div>
        <div class="body-wrap">
          <div class="body">{body}</div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""


def _build_promo_html(slide: dict, bg_b64: str) -> str:
    """마지막 디지털페이지 홍보 카드 HTML"""
    bg_url = f"data:image/png;base64,{bg_b64}" if bg_b64 else ""
    title = escape(slide.get("title", "")).replace("\n", "<br>")
    subtitle = escape(slide.get("subtitle", "")).replace("\n", "<br>")
    cta = escape(slide.get("cta", ""))
    template_path = Path(TEMPLATES_DIR) / "promo.html"
    template = template_path.read_text(encoding="utf-8")
    frame_style = _frame_style(slide, bg_url)
    logo_src = _file_to_data_url(PROMO_LOGO_PATH)
    if logo_src:
        brand_block = (
            f'<img class="brand-logo" src="{escape(logo_src, quote=True)}" '
            f'alt="{escape(PROMO_BRAND)}">'
        )
    else:
        brand_block = f'<div class="brand-text">{escape(PROMO_BRAND)}</div>'

    return (
        template
        .replace("{{BG_IMAGE}}", escape(bg_url, quote=True))
        .replace("{{FRAME_STYLE}}", frame_style)
        .replace("{{PROMO_BRAND_BLOCK}}", brand_block)
        .replace("{{TITLE_HTML}}", title)
        .replace("{{SUBTITLE_HTML}}", subtitle)
        .replace("{{CTA}}", cta)
    )


def _background_style(slide: dict, bg_url: str, default_color: str) -> str:
    mode = slide.get("background_mode")
    if mode == "solid_black":
        return "background-color: #000000;"
    if bg_url:
        return (
            f"background-color: {default_color};"
            f"background-image: url('{bg_url}');"
            "background-size: cover;"
            "background-position: center;"
        )
    return f"background-color: {default_color};"


def _frame_style(slide: dict, bg_url: str) -> str:
    mode = slide.get("background_mode")
    if mode == "solid_black":
        return "background-color:#000000;"
    if bg_url:
        return f'background:url("{bg_url}") center bottom/cover no-repeat;'
    return "background:#f0ece5;"


def _file_to_data_url(image_path: str) -> str:
    if not image_path or not os.path.exists(image_path):
        return ""

    suffix = Path(image_path).suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{encoded}"


def _build_preview_page(slides: list, slide_bg_b64: list, output_dir: str) -> str:
    """모든 카드를 한눈에 볼 수 있는 프리뷰 페이지"""
    cards_html = ""
    for i, slide in enumerate(slides):
        bg_b64 = slide_bg_b64[i] if i < len(slide_bg_b64) else ""
        if slide.get("type") == "thumbnail":
            card_html = _build_thumbnail_html(slide, bg_b64)
            label = "썸네일"
        elif slide.get("type") == "promo":
            card_html = _build_promo_html(slide, bg_b64)
            label = "프로모션"
        else:
            card_html = _build_content_html(slide, i, len(slides), bg_b64)
            label = f"슬라이드 {i}"

        # iframe으로 각 카드를 표시
        escaped_html = escape(card_html, quote=True)
        cards_html += f"""
        <div class="card-wrapper">
          <div class="card-label">{label}</div>
          <iframe srcdoc="{escaped_html}"
                  width="{CARD_WIDTH}" height="{CARD_HEIGHT}"
                  style="border:none; transform-origin:0 0; transform:scale({PREVIEW_SCALE});"
                  sandbox="allow-same-origin">
          </iframe>
        </div>"""

    preview_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>카드뉴스 프리뷰</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Sans KR', sans-serif;
    background: #f5f5f7;
    padding: 40px;
  }}
  h1 {{
    text-align: center;
    font-size: 28px;
    color: #1a1a2e;
    margin-bottom: 12px;
  }}
  .meta {{
    text-align: center;
    color: #888;
    font-size: 14px;
    margin-bottom: 40px;
  }}
  .grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    justify-content: center;
  }}
  .card-wrapper {{
    width: {int(CARD_WIDTH * PREVIEW_SCALE)}px;
    height: {int(CARD_HEIGHT * PREVIEW_SCALE) + 36}px;
    overflow: hidden;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    background: white;
  }}
  .card-label {{
    font-size: 13px;
    font-weight: 700;
    color: {BRAND['accent']};
    padding: 12px 16px 0;
    letter-spacing: 1px;
  }}
  .tip {{
    text-align: center;
    margin-top: 40px;
    padding: 20px;
    background: white;
    border-radius: 12px;
    color: #666;
    font-size: 14px;
    line-height: 1.8;
  }}
  .tip strong {{ color: {BRAND['accent']}; }}
</style>
</head>
<body>
  <h1>카드뉴스 프리뷰</h1>
  <div class="meta">생성 시간: {output_dir.split('/')[-1]} | 슬라이드 {len(slides)}장</div>
  <div class="grid">
    {cards_html}
  </div>
  <div class="tip">
    <strong>PNG 변환 방법:</strong> 각 HTML 파일을 브라우저에서 열고 → 개발자 도구(F12) →
    디바이스 모드에서 1080×1350 설정 → 스크린샷 캡처<br>
    또는 로컬에서 <code>playwright install chromium && python run.py</code> 실행
  </div>
</body>
</html>"""

    preview_path = os.path.join(output_dir, "preview.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(preview_html)
    logger.info("프리뷰 페이지 생성 완료: preview.html")
    return preview_path


def _create_png_converter(output_dir: str):
    """로컬에서 PNG 변환하는 스크립트를 생성한다."""
    script = """#!/usr/bin/env python3
\"\"\"
HTML 카드를 PNG로 변환하는 스크립트.
사용법: python convert_to_png.py
필요: pip install playwright && playwright install chromium
\"\"\"
import os, glob
from playwright.sync_api import sync_playwright

CARD_WIDTH = {card_width}
CARD_HEIGHT = {card_height}

def main():
    html_files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "card_*.html")))
    if not html_files:
        print("변환할 HTML 파일이 없습니다.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={{"width": CARD_WIDTH, "height": CARD_HEIGHT}})

        for html_path in html_files:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            page.set_content(html)
            page.wait_for_timeout(1500)  # 폰트 로드 대기

            png_path = html_path.replace(".html", ".png")
            page.screenshot(path=png_path, type="png")
            print(f"변환 완료: {{os.path.basename(png_path)}}")

        browser.close()
    print("모든 카드 PNG 변환 완료!")

if __name__ == "__main__":
    main()
""".format(card_width=CARD_WIDTH, card_height=CARD_HEIGHT)
    script_path = os.path.join(output_dir, "convert_to_png.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    logger.info("PNG 변환 스크립트 생성: convert_to_png.py")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from generator import _demo_slides
    slides = _demo_slides("테스트")
    render_cards(slides, [""] * len(slides), "output/test")
