from __future__ import annotations

import re
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urldefrag, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    GradeDiscoveredPage,
    GradeFeedbackItem,
    GradeRun,
    GradeSectionScore,
    GradeValidatorMessage,
)


import time


SEMANTIC_TAGS = frozenset({
    "header", "footer", "nav", "main", "section", "article", "aside", "figure", "figcaption", "details", "summary", "mark", "time",
})


@dataclass
class CrawledPage:
    url: str
    status_code: int | None
    is_html: bool
    html: str
    has_form: bool
    has_table: bool
    has_list: bool
    has_media: bool
    has_inline_media_query: bool
    stylesheets: list[str]
    internal_links: list[str]
    # Additional analysis fields for rubric alignment
    has_js: bool = False
    js_inline_count: int = 0
    js_external_count: int = 0
    js_has_validation: bool = False
    js_has_input_handling: bool = False
    semantic_tags_used: list[str] | None = None
    text_length: int = 0
    image_count: int = 0
    has_audio: bool = False
    has_video: bool = False
    audio_has_controls: bool = True
    video_has_controls: bool = True
    audio_has_autoplay: bool = False
    video_has_autoplay: bool = False


def _normalize_url(url: str) -> str:
    clean, _ = urldefrag(url)
    return clean.rstrip("/") if clean.endswith("/") and len(clean) > len(urlparse(clean).scheme) + 3 else clean


def _is_internal(candidate: str, root: str) -> bool:
    a = urlparse(candidate)
    b = urlparse(root)
    return a.scheme in {"http", "https"} and a.scheme == b.scheme and a.netloc == b.netloc


def _is_ignored_href(href: str) -> bool:
    lower = href.strip().lower()
    return lower.startswith("#") or lower.startswith("mailto:") or lower.startswith("tel:") or lower.startswith("javascript:")


def _fetch_with_retry(client: httpx.Client, url: str, retries: int = 3) -> httpx.Response:
    """Fetch a URL with retry logic to handle transient DNS/connection failures."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return client.get(url)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def crawl_site(root_url: str) -> dict[str, Any]:
    root = _normalize_url(root_url)
    max_pages = settings.grader_max_pages

    queue: deque[str] = deque([root])
    visited: set[str] = set()

    pages: list[CrawledPage] = []
    all_internal_links: set[str] = set()
    stylesheet_usage: Counter[str] = Counter()

    with httpx.Client(follow_redirects=True, timeout=settings.grader_http_timeout_seconds) as client:
        # Verify the root page is reachable before crawling.
        try:
            _fetch_with_retry(client, root)
        except Exception as exc:
            raise RuntimeError(f"Cannot reach root URL {root}: {exc}") from exc

        while queue and len(visited) < max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            status_code: int | None = None
            is_html = False
            html = ""
            has_form = has_table = has_list = has_media = False
            has_inline_media_query = False
            stylesheets: list[str] = []
            internal_links: list[str] = []
            has_js = False
            js_inline_count = 0
            js_external_count = 0
            js_has_validation = False
            js_has_input_handling = False
            semantic_tags_found: list[str] = []
            text_length = 0
            image_count = 0
            has_audio = False
            has_video = False
            audio_has_controls = True
            video_has_controls = True
            audio_has_autoplay = False
            video_has_autoplay = False

            try:
                resp = _fetch_with_retry(client, url)
                status_code = resp.status_code
                content_type = (resp.headers.get("content-type") or "").lower()
                if "text/html" in content_type or "application/xhtml+xml" in content_type:
                    is_html = True
                elif resp.text.lstrip().lower().startswith("<!doctype html") or "<html" in resp.text[:1000].lower():
                    is_html = True

                if is_html:
                    html = resp.text
                    soup = BeautifulSoup(html, "html.parser")

                    has_form = soup.find("form") is not None
                    has_table = soup.find("table") is not None and (
                        soup.find("tr") is not None and (soup.find("th") is not None or soup.find("td") is not None)
                    )
                    has_list = (soup.find("ul") is not None or soup.find("ol") is not None) and soup.find("li") is not None
                    has_media = any(soup.find(tag) is not None for tag in ("img", "video", "audio"))

                    # --- Text content length ---
                    body = soup.find("body")
                    text_length = len((body.get_text(separator=" ", strip=True)) if body else "")

                    # --- Images ---
                    image_count = len(soup.find_all("img"))

                    # --- Audio / Video with controls & autoplay checks ---
                    audio_tags = soup.find_all("audio")
                    video_tags = soup.find_all("video")
                    has_audio = len(audio_tags) > 0
                    has_video = len(video_tags) > 0
                    if has_audio:
                        audio_has_controls = all(a.has_attr("controls") for a in audio_tags)
                        audio_has_autoplay = any(a.has_attr("autoplay") for a in audio_tags)
                    if has_video:
                        video_has_controls = all(v.has_attr("controls") for v in video_tags)
                        video_has_autoplay = any(v.has_attr("autoplay") for v in video_tags)

                    # --- Semantic HTML tags ---
                    semantic_tags_found = list({tag.name for tag in soup.find_all(SEMANTIC_TAGS)})

                    # --- Inline media queries ---
                    for style in soup.find_all("style"):
                        if "@media" in (style.get_text() or ""):
                            has_inline_media_query = True
                            break

                    # --- Stylesheets ---
                    for link in soup.find_all("link"):
                        rel = [r.lower() for r in (link.get("rel") or [])]
                        if "stylesheet" in rel:
                            href = (link.get("href") or "").strip()
                            if not href:
                                continue
                            css_url = _normalize_url(urljoin(url, href))
                            stylesheets.append(css_url)
                            stylesheet_usage[css_url] += 1

                    # --- JavaScript detection ---
                    validation_patterns = re.compile(
                        r"(\.value\b|\.validity\b|checkValidity|reportValidity|setCustomValidity"
                        r"|\.required\b|\.pattern\b|\.min\b|\.max\b|\.minLength\b|\.maxLength\b"
                        r"|\.test\s*\(|RegExp|email.*valid|valid.*email|\.length\s*[<>=]"
                        r"|trim\s*\(\s*\)\s*===?\s*['\"]|isNaN|parseInt|parseFloat"
                        r"|addEventListener\s*\(\s*['\"]submit['\"])",
                        re.IGNORECASE,
                    )
                    input_handling_patterns = re.compile(
                        r"(getElementById|querySelector|getElementsByName|\.value\b"
                        r"|addEventListener\s*\(\s*['\"](?:input|change|submit|keyup|keydown|blur|focus)['\"]"
                        r"|\.preventDefault|\.elements\[)",
                        re.IGNORECASE,
                    )

                    for script in soup.find_all("script"):
                        src = (script.get("src") or "").strip()
                        if src:
                            js_external_count += 1
                            has_js = True
                            # Try to fetch and analyse external JS
                            try:
                                js_url = _normalize_url(urljoin(url, src))
                                if _is_internal(js_url, root):
                                    jr = client.get(js_url)
                                    if jr.status_code < 400:
                                        js_text = jr.text
                                        if validation_patterns.search(js_text):
                                            js_has_validation = True
                                        if input_handling_patterns.search(js_text):
                                            js_has_input_handling = True
                            except Exception:
                                pass
                        else:
                            inline_text = script.get_text() or ""
                            if inline_text.strip():
                                js_inline_count += 1
                                has_js = True
                                if validation_patterns.search(inline_text):
                                    js_has_validation = True
                                if input_handling_patterns.search(inline_text):
                                    js_has_input_handling = True

                    # --- Internal links ---
                    for a in soup.find_all("a"):
                        href = (a.get("href") or "").strip()
                        if not href or _is_ignored_href(href):
                            continue

                        resolved = _normalize_url(urljoin(url, href))
                        if not _is_internal(resolved, root):
                            continue

                        all_internal_links.add(resolved)
                        internal_links.append(resolved)
                        if resolved not in visited and resolved not in queue and len(visited) + len(queue) < max_pages:
                            queue.append(resolved)

            except Exception:
                pass

            pages.append(
                CrawledPage(
                    url=url,
                    status_code=status_code,
                    is_html=is_html,
                    html=html,
                    has_form=has_form,
                    has_table=has_table,
                    has_list=has_list,
                    has_media=has_media,
                    has_inline_media_query=has_inline_media_query,
                    stylesheets=stylesheets,
                    internal_links=internal_links,
                    has_js=has_js,
                    js_inline_count=js_inline_count,
                    js_external_count=js_external_count,
                    js_has_validation=js_has_validation,
                    js_has_input_handling=js_has_input_handling,
                    semantic_tags_used=semantic_tags_found,
                    text_length=text_length,
                    image_count=image_count,
                    has_audio=has_audio,
                    has_video=has_video,
                    audio_has_controls=audio_has_controls,
                    video_has_controls=video_has_controls,
                    audio_has_autoplay=audio_has_autoplay,
                    video_has_autoplay=video_has_autoplay,
                )
            )

    return {
        "root": root,
        "pages": pages,
        "internal_links": all_internal_links,
        "stylesheet_usage": stylesheet_usage,
    }


def check_link_statuses(urls: set[str]) -> dict[str, int | None]:
    statuses: dict[str, int | None] = {}
    with httpx.Client(follow_redirects=True, timeout=settings.grader_http_timeout_seconds) as client:
        for url in urls:
            try:
                r = _fetch_with_retry(client, url, retries=2)
                statuses[url] = r.status_code
            except Exception:
                statuses[url] = None
    return statuses


def validate_pages(page_urls: list[str]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    endpoint = settings.grader_validator_endpoint

    with httpx.Client(timeout=settings.grader_http_timeout_seconds) as client:
        for page_url in page_urls:
            try:
                r = client.get(endpoint, params={"doc": page_url, "out": "json"})
                if r.status_code >= 400:
                    continue
                payload = r.json()
                for m in payload.get("messages", []):
                    msg_type = str(m.get("type", ""))
                    subtype = str(m.get("subType", "") or m.get("subtype", "") or "")
                    message = str(m.get("message", ""))
                    extract = str(m.get("extract", "") or "")
                    line = m.get("lastLine") or m.get("firstLine")
                    col = m.get("lastColumn") or m.get("firstColumn")
                    messages.append(
                        {
                            "page_url": page_url,
                            "type": msg_type,
                            "subtype": subtype,
                            "message": message,
                            "extract": extract,
                            "line": int(line) if isinstance(line, int) else None,
                            "column": int(col) if isinstance(col, int) else None,
                        }
                    )
            except Exception:
                continue
    return messages


def _score_page_count(num_pages: int) -> float:
    if num_pages >= 5:
        return 10.0
    if num_pages == 4:
        return 7.0
    if num_pages == 3:
        return 4.0
    if num_pages == 2:
        return 2.0
    return 0.0


def _count_related_errors(messages: list[dict[str, Any]], keywords: list[str]) -> int:
    total = 0
    for m in messages:
        if m.get("type") != "error":
            continue
        text = (m.get("message", "") + " " + m.get("extract", "")).lower()
        if any(k in text for k in keywords):
            total += 1
    return total


def _has_media_query_in_external_css(urls: list[str]) -> bool:
    if not urls:
        return False

    media_re = re.compile(r"@media\s*[^{]+\{", re.IGNORECASE)
    with httpx.Client(follow_redirects=True, timeout=settings.grader_http_timeout_seconds) as client:
        for url in urls:
            try:
                r = client.get(url)
                if r.status_code >= 400:
                    continue
                text = r.text or ""
                if media_re.search(text):
                    return True
            except Exception:
                continue
    return False


# ---------------------------------------------------------------------------
# Rubric-aligned scoring  (5 sections × 100 pts = 500 total)
#
#  1. scope_theme_content       – 100 pts
#  2. navigation_semantic       – 100 pts
#  3. css_design_responsive     – 100 pts
#  4. required_elements         – 100 pts
#  5. js_validation_security    – 100 pts
# ---------------------------------------------------------------------------


def _score_scope_theme_content(html_pages: list[CrawledPage], main_count: int, num_pages: int) -> tuple[float, dict[str, Any]]:
    """Section 1: Project Scope, Theme, and Content Quality (100 pts)."""
    details: dict[str, Any] = {"num_pages": num_pages, "urls": [p.url for p in html_pages]}

    # --- Page count sub-score (up to 40 pts) ---
    if num_pages >= 5:
        page_pts = 40.0
    elif num_pages == 4:
        page_pts = 30.0
    elif num_pages == 3:
        page_pts = 20.0
    elif num_pages == 2:
        page_pts = 10.0
    else:
        page_pts = 0.0

    # --- Content depth sub-score (up to 30 pts) ---
    # Evaluate average text length across pages
    avg_text = sum(p.text_length for p in html_pages) / max(num_pages, 1)
    details["avg_text_length"] = round(avg_text, 1)
    if avg_text >= 300:
        content_pts = 30.0
    elif avg_text >= 150:
        content_pts = 22.0
    elif avg_text >= 50:
        content_pts = 14.0
    else:
        content_pts = 5.0

    # --- Theme cohesion sub-score (up to 30 pts) ---
    # Measured by shared stylesheet usage across pages
    if main_count >= num_pages and num_pages >= 5:
        theme_pts = 30.0
    elif main_count >= num_pages and num_pages >= 3:
        theme_pts = 25.0
    elif main_count >= 3:
        theme_pts = 20.0
    elif main_count >= 2:
        theme_pts = 12.0
    elif main_count >= 1:
        theme_pts = 5.0
    else:
        theme_pts = 0.0

    details["sub_scores"] = {"pages": page_pts, "content_depth": content_pts, "theme_cohesion": theme_pts}
    return round(page_pts + content_pts + theme_pts, 2), details


def _score_navigation_semantic(
    html_pages: list[CrawledPage],
    internal_links: set[str],
    broken_links: list[str],
    validator_messages: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """Section 2: Navigation, Organization, and Semantic HTML (100 pts)."""
    num_pages = len(html_pages)
    total_internal_links = len(internal_links)

    # --- Navigation sub-score (up to 40 pts) ---
    if total_internal_links < 4:
        nav_pts = 0.0
    elif len(broken_links) == 0:
        nav_pts = 40.0
    elif len(broken_links) <= 2:
        nav_pts = 30.0
    elif len(broken_links) <= 5:
        nav_pts = 17.0
    else:
        nav_pts = 0.0

    # --- Semantic HTML sub-score (up to 40 pts) ---
    all_semantic: set[str] = set()
    for p in html_pages:
        all_semantic.update(p.semantic_tags_used or [])
    num_semantic = len(all_semantic)

    if num_semantic >= 6:
        semantic_pts = 40.0
    elif num_semantic >= 4:
        semantic_pts = 30.0
    elif num_semantic >= 2:
        semantic_pts = 20.0
    elif num_semantic >= 1:
        semantic_pts = 10.0
    else:
        semantic_pts = 0.0

    # --- HTML validity sub-score (up to 20 pts) ---
    errors = [m for m in validator_messages if m.get("type") == "error"]
    warnings = [m for m in validator_messages if m.get("type") == "info" and m.get("subtype") == "warning"]
    validity_pts = max(0.0, 20.0 - float(len(errors)) - 0.25 * float(len(warnings)))

    details: dict[str, Any] = {
        "total_internal_links": total_internal_links,
        "broken_links": broken_links,
        "semantic_tags_found": sorted(all_semantic),
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "sub_scores": {"navigation": nav_pts, "semantic_html": semantic_pts, "validity": validity_pts},
    }
    return round(nav_pts + semantic_pts + validity_pts, 2), details


def _score_css_design_responsive(
    html_pages: list[CrawledPage],
    stylesheet_usage: Counter[str],
    main_stylesheet: str,
    main_count: int,
    num_pages: int,
) -> tuple[float, dict[str, Any]]:
    """Section 3: CSS, Visual Design, and Responsiveness (100 pts)."""
    unique_stylesheets = list(stylesheet_usage.keys())

    # --- External stylesheet usage (up to 40 pts) ---
    if main_count <= 0:
        css_pts = 0.0
    elif main_count >= num_pages and num_pages >= 5:
        css_pts = 40.0
    elif main_count >= num_pages and num_pages >= 3:
        css_pts = 34.0
    elif main_count >= 4:
        css_pts = 28.0
    elif main_count >= 2:
        css_pts = 17.0
    else:
        css_pts = 8.0

    # --- Responsiveness (up to 35 pts) ---
    external_media_query = _has_media_query_in_external_css(unique_stylesheets)
    inline_media_query = any(p.has_inline_media_query for p in html_pages)
    if external_media_query:
        resp_pts = 35.0
    elif inline_media_query:
        resp_pts = 20.0
    else:
        resp_pts = 0.0

    # --- Visual consistency (up to 25 pts) ---
    # Proxy: all pages use the same main stylesheet
    pages_with_main = sum(1 for p in html_pages if main_stylesheet in p.stylesheets) if main_stylesheet else 0
    if pages_with_main == num_pages and num_pages >= 5:
        visual_pts = 25.0
    elif pages_with_main >= num_pages - 1 and num_pages >= 4:
        visual_pts = 21.0
    elif pages_with_main >= 3:
        visual_pts = 15.0
    elif pages_with_main >= 1:
        visual_pts = 8.0
    else:
        visual_pts = 0.0

    details: dict[str, Any] = {
        "main_stylesheet": main_stylesheet,
        "main_stylesheet_usage_count": main_count,
        "pages_by_stylesheet": dict(stylesheet_usage),
        "external_media_query": external_media_query,
        "inline_media_query": inline_media_query,
        "stylesheets_checked": unique_stylesheets,
        "sub_scores": {"external_stylesheet": css_pts, "responsiveness": resp_pts, "visual_consistency": visual_pts},
    }
    return round(css_pts + resp_pts + visual_pts, 2), details


def _score_required_elements(
    html_pages: list[CrawledPage],
    validator_messages: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """Section 4: Required Elements and Media Integration (100 pts)."""
    presence = {
        "form": any(p.has_form for p in html_pages),
        "table": any(p.has_table for p in html_pages),
        "lists": any(p.has_list for p in html_pages),
        "images": any(p.image_count > 0 for p in html_pages),
    }

    related_error_counts = {
        "form": _count_related_errors(validator_messages, [" form", "<form", "input", "label", "textarea", "select", "fieldset", "legend"]),
        "table": _count_related_errors(validator_messages, ["table", "<tr", "<th", "<td", "caption", "thead", "tbody", "tfoot"]),
        "lists": _count_related_errors(validator_messages, ["<ul", "<ol", "<li", " list"]),
        "images": _count_related_errors(validator_messages, ["img", "image", "picture", "source"]),
    }

    # Each of the 4 elements is worth up to 20 pts
    element_scores: dict[str, float] = {}
    for key in ("form", "table", "lists", "images"):
        if not presence[key]:
            element_scores[key] = 0.0
        elif related_error_counts[key] == 0:
            element_scores[key] = 20.0
        elif related_error_counts[key] <= 2:
            element_scores[key] = 14.0
        else:
            element_scores[key] = 7.0

    # --- Media controls & autoplay (up to 20 pts) ---
    has_any_media = any(p.has_media for p in html_pages)
    total_images = sum(p.image_count for p in html_pages)
    has_audio = any(p.has_audio for p in html_pages)
    has_video = any(p.has_video for p in html_pages)
    all_controls = all(p.audio_has_controls and p.video_has_controls for p in html_pages if p.has_audio or p.has_video)
    any_autoplay = any(p.audio_has_autoplay or p.video_has_autoplay for p in html_pages)

    if has_any_media and total_images >= 3:
        media_pts = 20.0
    elif has_any_media and total_images >= 1:
        media_pts = 14.0
    elif has_any_media:
        media_pts = 8.0
    else:
        media_pts = 0.0

    # Penalise missing controls or autoplay on audio/video
    if (has_audio or has_video) and not all_controls:
        media_pts = max(0.0, media_pts - 8.0)
    if any_autoplay:
        media_pts = max(0.0, media_pts - 5.0)

    elements_total = sum(element_scores.values()) + media_pts

    details: dict[str, Any] = {
        "presence": presence,
        "element_scores": element_scores,
        "related_error_counts": related_error_counts,
        "total_images": total_images,
        "has_audio": has_audio,
        "has_video": has_video,
        "all_controls": all_controls,
        "any_autoplay": any_autoplay,
        "sub_scores": {**element_scores, "media_integration": media_pts},
    }
    return round(elements_total, 2), details


def _score_js_validation_security(html_pages: list[CrawledPage]) -> tuple[float, dict[str, Any]]:
    """Section 5: JavaScript, Input Validation, Security, Originality, and Explainability (100 pts)."""
    has_js = any(p.has_js for p in html_pages)
    has_validation = any(p.js_has_validation for p in html_pages)
    has_input_handling = any(p.js_has_input_handling for p in html_pages)
    total_inline = sum(p.js_inline_count for p in html_pages)
    total_external = sum(p.js_external_count for p in html_pages)
    total_scripts = total_inline + total_external

    # --- JS presence & integration (up to 40 pts) ---
    if not has_js:
        js_pts = 0.0
    elif total_scripts >= 2 and has_input_handling:
        js_pts = 40.0
    elif total_scripts >= 1 and has_input_handling:
        js_pts = 34.0
    elif total_scripts >= 1:
        js_pts = 20.0
    else:
        js_pts = 10.0

    # --- Input validation (up to 35 pts) ---
    if has_validation and has_input_handling:
        val_pts = 35.0
    elif has_validation:
        val_pts = 25.0
    elif has_input_handling:
        val_pts = 15.0
    else:
        val_pts = 0.0

    # --- Secure coding awareness (up to 25 pts) ---
    # Check for dangerous patterns in JS
    dangerous_patterns = re.compile(
        r"(innerHTML\s*=|document\.write\s*\(|eval\s*\(|\.outerHTML\s*=)", re.IGNORECASE
    )
    dangerous_found = False
    for p in html_pages:
        if not p.html:
            continue
        soup = BeautifulSoup(p.html, "html.parser")
        for script in soup.find_all("script"):
            text = script.get_text() or ""
            if dangerous_patterns.search(text):
                dangerous_found = True
                break
        if dangerous_found:
            break

    if has_validation and not dangerous_found:
        sec_pts = 25.0
    elif has_validation and dangerous_found:
        sec_pts = 15.0
    elif not dangerous_found:
        sec_pts = 12.0
    else:
        sec_pts = 0.0

    details: dict[str, Any] = {
        "has_js": has_js,
        "total_inline_scripts": total_inline,
        "total_external_scripts": total_external,
        "has_validation": has_validation,
        "has_input_handling": has_input_handling,
        "dangerous_patterns_found": dangerous_found,
        "sub_scores": {"js_integration": js_pts, "input_validation": val_pts, "security_awareness": sec_pts},
    }
    return round(js_pts + val_pts + sec_pts, 2), details


def score_run(analysis: dict[str, Any]) -> dict[str, Any]:
    pages: list[CrawledPage] = analysis["pages"]
    html_pages = [p for p in pages if p.is_html]
    num_pages = len(html_pages)

    stylesheet_usage: Counter[str] = analysis["stylesheet_usage"]
    main_stylesheet = ""
    main_count = 0
    if stylesheet_usage:
        main_stylesheet, main_count = stylesheet_usage.most_common(1)[0]

    validator_messages = validate_pages([p.url for p in html_pages])

    link_statuses = check_link_statuses(analysis["internal_links"])
    broken_links = [u for u, code in link_statuses.items() if code is None or not (200 <= code < 400)]

    # --- Section 1: Project Scope, Theme, and Content Quality (100 pts) ---
    s1_score, s1_details = _score_scope_theme_content(html_pages, main_count, num_pages)

    # --- Section 2: Navigation, Organization, and Semantic HTML (100 pts) ---
    s2_score, s2_details = _score_navigation_semantic(html_pages, analysis["internal_links"], broken_links, validator_messages)

    # --- Section 3: CSS, Visual Design, and Responsiveness (100 pts) ---
    s3_score, s3_details = _score_css_design_responsive(html_pages, stylesheet_usage, main_stylesheet, main_count, num_pages)

    # --- Section 4: Required Elements and Media Integration (100 pts) ---
    s4_score, s4_details = _score_required_elements(html_pages, validator_messages)

    # --- Section 5: JavaScript, Input Validation, Security (100 pts) ---
    s5_score, s5_details = _score_js_validation_security(html_pages)

    sections = {
        "scope_theme_content": {
            "score": s1_score,
            "max_score": 100.0,
            "details": s1_details,
        },
        "navigation_semantic": {
            "score": s2_score,
            "max_score": 100.0,
            "details": s2_details,
        },
        "css_design_responsive": {
            "score": s3_score,
            "max_score": 100.0,
            "details": s3_details,
        },
        "required_elements": {
            "score": s4_score,
            "max_score": 100.0,
            "details": s4_details,
        },
        "js_validation_security": {
            "score": s5_score,
            "max_score": 100.0,
            "details": s5_details,
        },
    }

    total_score = round(sum(v["score"] for v in sections.values()), 2)

    # --- Feedback generation ---
    feedback: list[str] = []

    # Section 1 feedback
    if s1_score < 100:
        if num_pages < 5:
            feedback.append(f"Section 1 – Scope: Found {num_pages} HTML pages; 5+ required for full credit.")
        if s1_details["avg_text_length"] < 150:
            feedback.append("Section 1 – Content: Pages have limited text content. Add more substantial content to each page.")
        if s1_details["sub_scores"]["theme_cohesion"] < 25:
            feedback.append("Section 1 – Theme: Ensure a shared external stylesheet is used across all pages for a cohesive theme.")

    # Section 2 feedback
    if s2_score < 100:
        if len(broken_links) > 0:
            feedback.append(f"Section 2 – Navigation: {len(broken_links)} broken internal link(s) detected.")
        if len(s2_details["semantic_tags_found"]) < 4:
            feedback.append(f"Section 2 – Semantic HTML: Only {len(s2_details['semantic_tags_found'])} semantic tag types found. Use header, nav, main, section, article, footer, etc.")
        if s2_details["sub_scores"]["validity"] < 20:
            feedback.append(f"Section 2 – Validity: {s2_details['total_errors']} HTML errors and {s2_details['total_warnings']} warnings from W3C validation.")

    # Section 3 feedback
    if s3_score < 100:
        if s3_details["sub_scores"]["external_stylesheet"] < 40:
            feedback.append("Section 3 – CSS: Reuse one external stylesheet across all pages.")
        if s3_details["sub_scores"]["responsiveness"] < 35:
            feedback.append("Section 3 – Responsiveness: Add @media queries in external stylesheet for responsive design.")

    # Section 4 feedback
    if s4_score < 100:
        missing = [k for k, v in s4_details["presence"].items() if not v]
        if missing:
            feedback.append(f"Section 4 – Missing required elements: {', '.join(missing)}.")
        if s4_details.get("any_autoplay"):
            feedback.append("Section 4 – Media: Autoplay detected on audio/video. Disable autoplay.")
        if not s4_details.get("all_controls") and (s4_details.get("has_audio") or s4_details.get("has_video")):
            feedback.append("Section 4 – Media: Audio/video elements should include controls attribute.")

    # Section 5 feedback
    if s5_score < 100:
        if not s5_details["has_js"]:
            feedback.append("Section 5 – JavaScript: No JavaScript detected. A simple, integrated script is required.")
        elif not s5_details["has_validation"]:
            feedback.append("Section 5 – Validation: JavaScript input validation not detected. All JS inputs must be verified/validated before use.")
        if s5_details.get("dangerous_patterns_found"):
            feedback.append("Section 5 – Security: Potentially unsafe patterns found (innerHTML=, eval, document.write). Use safer DOM methods.")

    return {
        "sections": sections,
        "total_score": total_score,
        "summary_feedback": feedback,
        "validator_messages": validator_messages,
    }


def run_grading(db: Session, run: GradeRun) -> dict[str, Any]:
    run.status = "running"
    run.started_at = datetime.utcnow()
    db.commit()

    # Clean up previous artifacts if re-run.
    db.query(GradeSectionScore).filter(GradeSectionScore.run_id == run.id).delete()
    db.query(GradeFeedbackItem).filter(GradeFeedbackItem.run_id == run.id).delete()
    db.query(GradeDiscoveredPage).filter(GradeDiscoveredPage.run_id == run.id).delete()
    db.query(GradeValidatorMessage).filter(GradeValidatorMessage.run_id == run.id).delete()
    db.commit()

    try:
        analysis = crawl_site(run.input_url)
        result = score_run(analysis)

        run.normalized_root = analysis["root"]
        run.total_score = result["total_score"]
        run.status = "completed"
        run.error_message = None
        run.finished_at = datetime.utcnow()

        for p in analysis["pages"]:
            db.add(
                GradeDiscoveredPage(
                    run_id=run.id,
                    url=p.url,
                    status_code=p.status_code,
                    is_html=p.is_html,
                    has_form=p.has_form,
                    has_table=p.has_table,
                    has_list=p.has_list,
                    has_media=p.has_media,
                )
            )

        for msg in result["validator_messages"]:
            db.add(
                GradeValidatorMessage(
                    run_id=run.id,
                    page_url=msg["page_url"],
                    message_type=msg["type"],
                    subtype=msg.get("subtype") or None,
                    line=msg.get("line"),
                    column_num=msg.get("column"),
                    message=msg["message"],
                    extract=msg.get("extract") or None,
                )
            )

        for section_key, section in result["sections"].items():
            db.add(
                GradeSectionScore(
                    run_id=run.id,
                    section_key=section_key,
                    score=section["score"],
                    max_score=section["max_score"],
                    details_json=section["details"],
                )
            )

        for i, text in enumerate(result["summary_feedback"], start=1):
            db.add(GradeFeedbackItem(run_id=run.id, order_index=i, feedback_text=text))

        db.commit()
        db.refresh(run)
        return result

    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
