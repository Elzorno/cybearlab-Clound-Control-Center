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


def crawl_site(root_url: str) -> dict[str, Any]:
    root = _normalize_url(root_url)
    max_pages = settings.grader_max_pages

    queue: deque[str] = deque([root])
    visited: set[str] = set()

    pages: list[CrawledPage] = []
    all_internal_links: set[str] = set()
    stylesheet_usage: Counter[str] = Counter()

    with httpx.Client(follow_redirects=True, timeout=settings.grader_http_timeout_seconds) as client:
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

            try:
                resp = client.get(url)
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

                    for style in soup.find_all("style"):
                        if "@media" in (style.get_text() or ""):
                            has_inline_media_query = True
                            break

                    for link in soup.find_all("link"):
                        rel = [r.lower() for r in (link.get("rel") or [])]
                        if "stylesheet" in rel:
                            href = (link.get("href") or "").strip()
                            if not href:
                                continue
                            css_url = _normalize_url(urljoin(url, href))
                            stylesheets.append(css_url)
                            stylesheet_usage[css_url] += 1

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
                r = client.get(url)
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


def _score_stylesheet_shared(main_count: int, num_pages: int, variant: str) -> float:
    if main_count <= 0:
        return 0.0
    if main_count == num_pages and num_pages > 0:
        return 15.0 if variant == "external" else 15.0
    if main_count >= 4:
        return 12.0
    if 2 <= main_count <= 3:
        return 7.0 if variant == "external" else 5.0
    return 0.0


def _structure_subscore(present: bool, related_errors: int) -> float:
    if not present:
        return 0.0
    if related_errors == 0:
        return 7.5
    if related_errors <= 2:
        return 4.0
    return 2.0


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
    errors = [m for m in validator_messages if m.get("type") == "error"]
    warnings = [m for m in validator_messages if m.get("type") == "info" and m.get("subtype") == "warning"]

    presence = {
        "form": any(p.has_form for p in html_pages),
        "table": any(p.has_table for p in html_pages),
        "lists": any(p.has_list for p in html_pages),
        "media": any(p.has_media for p in html_pages),
    }

    related_error_counts = {
        "form": _count_related_errors(validator_messages, [" form", "<form", "input", "label", "textarea", "select", "fieldset", "legend"]),
        "table": _count_related_errors(validator_messages, ["table", "<tr", "<th", "<td", "caption", "thead", "tbody", "tfoot"]),
        "lists": _count_related_errors(validator_messages, ["<ul", "<ol", "<li", " list"]),
        "media": _count_related_errors(validator_messages, ["img", "image", "video", "audio", "source", "picture", "track"]),
    }

    structure_sub_scores = {
        key: _structure_subscore(presence[key], related_error_counts[key]) for key in ("form", "table", "lists", "media")
    }

    unique_stylesheets = list(stylesheet_usage.keys())
    external_media_query = _has_media_query_in_external_css(unique_stylesheets)
    inline_media_query = any(p.has_inline_media_query for p in html_pages)

    link_statuses = check_link_statuses(analysis["internal_links"])
    broken_links = [u for u, code in link_statuses.items() if code is None or not (200 <= code < 400)]

    page_count_score = _score_page_count(num_pages)
    external_stylesheet_score = _score_stylesheet_shared(main_count, num_pages, variant="external")
    structures_score = sum(structure_sub_scores.values())

    if external_media_query:
        responsiveness_score = 10.0
    elif inline_media_query:
        responsiveness_score = 6.0
    else:
        responsiveness_score = 0.0

    theme_score = _score_stylesheet_shared(main_count, num_pages, variant="theme")

    total_internal_links = len(analysis["internal_links"])
    if total_internal_links < 4:
        navigation_score = 0.0
    elif len(broken_links) == 0:
        navigation_score = 10.0
    elif len(broken_links) <= 2:
        navigation_score = 7.0
    elif len(broken_links) <= 5:
        navigation_score = 4.0
    else:
        navigation_score = 0.0

    validity_score = max(0.0, 20.0 - float(len(errors)) - 0.25 * float(len(warnings)))

    sections = {
        "page_count": {
            "score": page_count_score,
            "max_score": 10.0,
            "details": {"num_pages": num_pages, "urls": [p.url for p in html_pages]},
        },
        "external_stylesheet": {
            "score": external_stylesheet_score,
            "max_score": 15.0,
            "details": {
                "main_stylesheet": main_stylesheet,
                "main_stylesheet_usage_count": main_count,
                "pages_by_stylesheet": dict(stylesheet_usage),
            },
        },
        "structures": {
            "score": structures_score,
            "max_score": 30.0,
            "details": {
                "presence": presence,
                "sub_scores": structure_sub_scores,
                "related_error_counts": related_error_counts,
            },
        },
        "responsiveness": {
            "score": responsiveness_score,
            "max_score": 10.0,
            "details": {
                "external_media_query": external_media_query,
                "inline_media_query": inline_media_query,
                "stylesheets_checked": unique_stylesheets,
            },
        },
        "theme": {
            "score": theme_score,
            "max_score": 15.0,
            "details": {
                "main_stylesheet": main_stylesheet,
                "main_stylesheet_usage_count": main_count,
            },
        },
        "navigation": {
            "score": navigation_score,
            "max_score": 10.0,
            "details": {
                "total_internal_links": total_internal_links,
                "broken_links": broken_links,
            },
        },
        "validity": {
            "score": validity_score,
            "max_score": 20.0,
            "details": {
                "total_errors": len(errors),
                "total_warnings": len(warnings),
                "errors": errors,
                "warnings": warnings,
            },
        },
    }

    total_score = round(sum(v["score"] for v in sections.values()), 2)

    feedback: list[str] = []
    if page_count_score < 10:
        feedback.append(f"Page count: {page_count_score}/10 - found {num_pages} HTML pages; target is at least 5.")
    if external_stylesheet_score < 15:
        feedback.append("External stylesheet usage can improve. Reuse one main stylesheet across all pages.")
    if structures_score < 30:
        missing = [k for k, v in presence.items() if not v]
        if missing:
            feedback.append(f"Add required structures: {', '.join(missing)}.")
        else:
            feedback.append("Fix validator errors around forms/tables/lists/media to improve structure score.")
    if responsiveness_score < 10:
        feedback.append("Add responsive CSS @media rules in external stylesheet for full responsiveness points.")
    if navigation_score < 10:
        feedback.append(f"Navigation issues: {len(broken_links)} broken internal links detected.")
    if validity_score < 20:
        feedback.append(f"Validity score reduced by {len(errors)} errors and {len(warnings)} warnings from W3C validation.")

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
