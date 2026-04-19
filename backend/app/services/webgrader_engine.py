from __future__ import annotations

import ipaddress
import math
import re
import secrets
import socket
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Assignment, Submission
from ..schemas import RubricCheck, RubricDefinition


TICKET_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


@dataclass
class RubricPage:
    url: str
    status_code: int | None
    is_html: bool
    html: str = ""
    soup: BeautifulSoup | None = None
    css_urls: list[str] = field(default_factory=list)
    js_urls: list[str] = field(default_factory=list)
    css_content: str = ""
    js_content: str = ""
    internal_links: list[str] = field(default_factory=list)


@dataclass
class GradingContext:
    root_url: str
    pages: list[RubricPage]
    internal_links: set[str]
    link_statuses: dict[str, int | None]
    errors: list[str]


def generate_ticket_code(db: Session, length: int = 6) -> str:
    length = max(4, min(8, length))
    while True:
        code = "".join(secrets.choice(TICKET_ALPHABET) for _ in range(length))
        exists = db.query(Submission).filter(Submission.ticket_code == code).first()
        if not exists:
            return code


def _normalize_url(url: str) -> str:
    clean, _ = urldefrag(url)
    parsed = urlparse(clean)
    if clean.endswith("/") and parsed.path == "/":
        return clean.rstrip("/")
    return clean


def _is_ignored_href(href: str) -> bool:
    lower = href.strip().lower()
    return lower.startswith("#") or lower.startswith("mailto:") or lower.startswith("tel:") or lower.startswith("javascript:")


def _is_internal(candidate: str, root: str) -> bool:
    a = urlparse(candidate)
    b = urlparse(root)
    return a.scheme in {"http", "https"} and a.scheme == b.scheme and a.netloc == b.netloc


def _host_is_blocked(hostname: str | None) -> bool:
    if not hostname:
        return True
    if hostname.lower() in {"localhost", "localhost.localdomain"}:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_loopback or ip.is_link_local or ip.is_unspecified
    except ValueError:
        pass

    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
                return True
    except socket.gaierror:
        return False
    return False


def _validate_fetchable_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Project URL must be a valid HTTP or HTTPS URL")
    if _host_is_blocked(parsed.hostname):
        raise ValueError("Project URL cannot target localhost or loopback addresses")


def _is_html_response(resp: httpx.Response) -> bool:
    content_type = (resp.headers.get("content-type") or "").lower()
    if "text/html" in content_type or "application/xhtml+xml" in content_type:
        return True
    sample = resp.text[:1000].lower()
    return sample.lstrip().startswith("<!doctype html") or "<html" in sample


def _safe_get(client: httpx.Client, url: str) -> httpx.Response:
    _validate_fetchable_url(url)
    resp = client.get(url)
    final = str(resp.url)
    _validate_fetchable_url(final)
    return resp


def _extract_import_urls(css_text: str, base_url: str) -> list[str]:
    imports: list[str] = []
    for match in re.finditer(r"@import\s+(?:url\()?['\"]?([^'\"\);]+)", css_text, flags=re.IGNORECASE):
        imports.append(_normalize_url(urljoin(base_url, match.group(1).strip())))
    return imports


def _fetch_css_with_imports(client: httpx.Client, url: str, seen: set[str] | None = None) -> str:
    seen = seen or set()
    if url in seen:
        return ""
    seen.add(url)
    try:
        resp = _safe_get(client, url)
        if resp.status_code >= 400:
            return ""
        css_text = resp.text or ""
    except Exception:
        return ""

    imported = []
    for import_url in _extract_import_urls(css_text, url):
        imported.append(_fetch_css_with_imports(client, import_url, seen))
    return "\n".join([css_text, *imported])


def crawl_for_rubric(project_url: str, rubric: RubricDefinition) -> GradingContext:
    root = _normalize_url(project_url)
    _validate_fetchable_url(root)
    max_pages = rubric.maxPages or settings.grader_max_pages
    queue: deque[str] = deque([root])
    visited: set[str] = set()
    pages: list[RubricPage] = []
    internal_links: set[str] = set()
    link_statuses: dict[str, int | None] = {}
    errors: list[str] = []

    timeout = max(10, settings.grader_http_timeout_seconds)
    with httpx.Client(follow_redirects=True, max_redirects=3, timeout=timeout) as client:
        while queue and len(visited) < max_pages:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            page = RubricPage(url=current, status_code=None, is_html=False)
            try:
                resp = _safe_get(client, current)
                page.url = _normalize_url(str(resp.url))
                page.status_code = resp.status_code
                page.is_html = resp.status_code < 400 and _is_html_response(resp)
                if not page.is_html:
                    pages.append(page)
                    continue

                page.html = resp.text or ""
                page.soup = BeautifulSoup(page.html, "html.parser")

                for style in page.soup.find_all("style"):
                    page.css_content += "\n" + (style.get_text() or "")

                for link in page.soup.find_all("link"):
                    rel = [str(r).lower() for r in (link.get("rel") or [])]
                    if "stylesheet" not in rel:
                        continue
                    href = (link.get("href") or "").strip()
                    if not href:
                        continue
                    css_url = _normalize_url(urljoin(page.url, href))
                    page.css_urls.append(css_url)
                    page.css_content += "\n" + _fetch_css_with_imports(client, css_url)

                for script in page.soup.find_all("script"):
                    src = (script.get("src") or "").strip()
                    if src:
                        js_url = _normalize_url(urljoin(page.url, src))
                        page.js_urls.append(js_url)
                        try:
                            js_resp = _safe_get(client, js_url)
                            if js_resp.status_code < 400:
                                page.js_content += "\n" + (js_resp.text or "")
                        except Exception:
                            continue
                    else:
                        page.js_content += "\n" + (script.get_text() or "")

                for a in page.soup.find_all("a"):
                    href = (a.get("href") or "").strip()
                    if not href or _is_ignored_href(href):
                        continue
                    resolved = _normalize_url(urljoin(page.url, href))
                    if not _is_internal(resolved, root):
                        continue
                    internal_links.add(resolved)
                    page.internal_links.append(resolved)
                    if resolved not in visited and resolved not in queue and len(visited) + len(queue) < max_pages:
                        queue.append(resolved)
            except Exception as exc:
                errors.append(f"Failed to fetch {current}: {exc}")

            pages.append(page)

        for link in internal_links:
            try:
                resp = _safe_get(client, link)
                link_statuses[link] = resp.status_code
            except Exception:
                link_statuses[link] = None

    return GradingContext(root_url=root, pages=pages, internal_links=internal_links, link_statuses=link_statuses, errors=errors)


def _resolve_scope(ctx: GradingContext, scope: Any) -> list[RubricPage]:
    html_pages = [p for p in ctx.pages if p.is_html]
    if not html_pages:
        return []
    if scope in (None, "index"):
        return [html_pages[0]]
    if scope == "all_pages":
        return html_pages
    if scope == "any_page":
        return html_pages
    if isinstance(scope, dict) and scope.get("page"):
        suffix = "/" + scope["page"].lstrip("/")
        return [p for p in html_pages if urlparse(p.url).path.endswith(suffix)]
    return [html_pages[0]]


def _aggregate_scope(scope: Any, per_page_passes: list[bool]) -> bool:
    if not per_page_passes:
        return False
    if scope == "all_pages":
        return all(per_page_passes)
    return any(per_page_passes)


def _regex_flags(flags: str | None) -> int:
    value = 0
    flags = flags or "i"
    if "i" in flags:
        value |= re.IGNORECASE
    if "m" in flags:
        value |= re.MULTILINE
    if "s" in flags:
        value |= re.DOTALL
    return value


def _match_value(actual: str, expected: str | None) -> bool:
    if expected is None:
        return True
    return actual == expected or re.search(expected, actual, flags=re.IGNORECASE) is not None


def _html_element(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    tag = str(params.get("tag", "")).strip()
    min_count = int(params.get("minCount", 1))
    max_count = params.get("maxCount")
    if tag.lower() == "!doctype":
        count = 1 if re.search(r"<!doctype\s+html", page.html, flags=re.IGNORECASE) else 0
    elif page.soup:
        count = len(page.soup.find_all(tag))
    else:
        count = 0
    passed = count >= min_count and (max_count is None or count <= int(max_count))
    return passed, {"tag": tag, "count": count, "minCount": min_count, "maxCount": max_count}


def _html_attribute(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    tag = str(params.get("tag", "")).strip()
    attribute = str(params.get("attribute", "")).strip()
    expected = params.get("value")
    matches: list[str] = []
    if page.soup:
        for el in page.soup.find_all(tag):
            if not el.has_attr(attribute):
                continue
            actual = " ".join(el.get(attribute)) if isinstance(el.get(attribute), list) else str(el.get(attribute))
            if _match_value(actual, str(expected) if expected is not None else None):
                matches.append(actual)
    return bool(matches), {"tag": tag, "attribute": attribute, "matches": matches}


def _css_property(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    prop = re.escape(str(params.get("property", "")).strip())
    expected = params.get("value")
    pattern = rf"{prop}\s*:\s*([^;}}]+)"
    values = [m.group(1).strip() for m in re.finditer(pattern, page.css_content, flags=re.IGNORECASE)]
    passed = any(_match_value(value, str(expected) if expected is not None else None) for value in values)
    return passed, {"property": params.get("property"), "values": values[:20]}


def _css_selector(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    selector = str(params.get("selector", "")).strip()
    pattern = re.escape(selector) + r"\s*\{"
    passed = re.search(pattern, page.css_content, flags=re.IGNORECASE) is not None
    return passed, {"selector": selector}


def _js_file(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    filename = params.get("filename")
    if not filename:
        return bool(page.js_urls), {"jsFiles": page.js_urls}
    matches = [url for url in page.js_urls if str(urlparse(url).path).endswith(str(filename))]
    return bool(matches), {"filename": filename, "matches": matches}


def _js_function(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    name = re.escape(str(params.get("functionName", "")).strip())
    pattern = rf"(function\s+{name}\s*\(|(?:const|let|var)\s+{name}\s*=\s*(?:function|\([^)]*\)\s*=>|[^=]+=>))"
    passed = re.search(pattern, page.js_content, flags=re.IGNORECASE) is not None
    return passed, {"functionName": params.get("functionName")}


def _js_dom_event(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    event_type = params.get("eventType")
    if event_type:
        event = re.escape(str(event_type))
        pattern = rf"(addEventListener\s*\(\s*['\"]{event}['\"]|on{event}\s*=)"
    else:
        pattern = r"(addEventListener\s*\(\s*['\"][a-z]+['\"]|on[a-z]+\s*=)"
    passed = re.search(pattern, page.js_content + "\n" + page.html, flags=re.IGNORECASE) is not None
    return passed, {"eventType": event_type}


def _meta_tag(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    if not page.soup:
        return False, params
    name = params.get("name")
    prop = params.get("property")
    matches = []
    for meta in page.soup.find_all("meta"):
        if name and str(meta.get("name", "")).lower() == str(name).lower():
            matches.append(str(meta))
        if prop and str(meta.get("property", "")).lower() == str(prop).lower():
            matches.append(str(meta))
    return bool(matches), {"matches": matches[:10]}


def _file_exists(client: httpx.Client, root_url: str, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    path = str(params.get("path", "")).lstrip("/")
    target = _normalize_url(urljoin(root_url.rstrip("/") + "/", path))
    try:
        resp = _safe_get(client, target)
        passed = 200 <= resp.status_code < 400
        return passed, {"url": target, "statusCode": resp.status_code}
    except Exception as exc:
        return False, {"url": target, "error": str(exc)}


def _custom_regex(page: RubricPage, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    target = str(params.get("target", "html")).lower()
    pattern = str(params.get("pattern", ""))
    if target == "css":
        text = page.css_content
    elif target == "js":
        text = page.js_content
    else:
        text = page.html
    passed = re.search(pattern, text, flags=_regex_flags(params.get("flags"))) is not None
    return passed, {"target": target, "pattern": pattern}


def _validate_html_page(client: httpx.Client, page: RubricPage) -> tuple[bool, float | None, dict[str, Any], str]:
    try:
        resp = client.get(settings.grader_validator_endpoint, params={"doc": page.url, "out": "json"})
        if resp.status_code >= 400:
            return True, None, {"warning": f"Validator returned HTTP {resp.status_code}"}, "W3C validator unavailable; check skipped with credit."
        messages = resp.json().get("messages", [])
        errors = [m for m in messages if m.get("type") == "error"]
        warnings = [m for m in messages if m.get("type") == "info" and (m.get("subType") or m.get("subtype")) == "warning"]
        return len(errors) == 0, float(len(errors)), {"errors": errors, "warnings": warnings}, f"Found {len(errors)} HTML error(s)."
    except Exception as exc:
        return True, None, {"warning": str(exc)}, "W3C validator unavailable; check skipped with credit."


def _validate_css_urls(client: httpx.Client, urls: list[str]) -> tuple[bool, int | None, dict[str, Any], str]:
    total_errors = 0
    checked: list[dict[str, Any]] = []
    try:
        for url in urls:
            resp = client.get(settings.grader_css_validator_endpoint, params={"uri": url, "output": "json"})
            if resp.status_code >= 400:
                return True, None, {"warning": f"CSS validator returned HTTP {resp.status_code}"}, "W3C CSS validator unavailable; check skipped with credit."
            payload = resp.json()
            errors = payload.get("cssvalidation", {}).get("errors", [])
            total_errors += len(errors)
            checked.append({"url": url, "errors": errors})
        return total_errors == 0, total_errors, {"stylesheets": checked}, f"Found {total_errors} CSS validation error(s)."
    except Exception as exc:
        return True, None, {"warning": str(exc)}, "W3C CSS validator unavailable; check skipped with credit."


def _evaluate_binary_check(check: RubricCheck, page: RubricPage, ctx: GradingContext, client: httpx.Client) -> tuple[bool, dict[str, Any], str]:
    params = check.params or {}
    if check.type == "html_element":
        passed, details = _html_element(page, params)
    elif check.type == "html_attribute":
        passed, details = _html_attribute(page, params)
    elif check.type == "css_property":
        passed, details = _css_property(page, params)
    elif check.type == "css_selector":
        passed, details = _css_selector(page, params)
    elif check.type == "js_file":
        passed, details = _js_file(page, params)
    elif check.type == "js_function":
        passed, details = _js_function(page, params)
    elif check.type == "js_dom_event":
        passed, details = _js_dom_event(page, params)
    elif check.type == "meta_tag":
        passed, details = _meta_tag(page, params)
    elif check.type == "file_exists":
        passed, details = _file_exists(client, ctx.root_url, params)
    elif check.type == "custom_regex":
        passed, details = _custom_regex(page, params)
    else:
        return False, {"unsupportedType": check.type}, f"Unsupported check type: {check.type}"
    return passed, details, "Passed." if passed else "Requirement not met."


def _score_w3c(points: float, error_count: float | None) -> float:
    if error_count is None:
        return points
    return max(0.0, float(math.floor(points * (1 - error_count * 0.10))))


def evaluate_check(check: RubricCheck, ctx: GradingContext) -> dict[str, Any]:
    pages = _resolve_scope(ctx, check.scope)
    timeout = max(10, settings.grader_http_timeout_seconds)
    with httpx.Client(follow_redirects=True, max_redirects=3, timeout=timeout) as client:
        if check.type == "page_count":
            html_count = len([p for p in ctx.pages if p.is_html])
            minimum = int(check.params.get("min", 1))
            maximum = check.params.get("max")
            passed = html_count >= minimum and (maximum is None or html_count <= int(maximum))
            details = {"pagesFound": html_count, "min": minimum, "max": maximum}
            message = f"Found {html_count} HTML page(s)."
            earned = check.points if passed else 0.0
        elif check.type == "link_crawl":
            total = len(ctx.link_statuses)
            accessible = len([code for code in ctx.link_statuses.values() if code is not None and 200 <= code < 400])
            passed = total == accessible
            earned = check.points if total == 0 else math.floor(check.points * (accessible / total))
            details = {"totalLinks": total, "accessibleLinks": accessible, "statuses": ctx.link_statuses}
            message = "All local links are reachable." if passed else f"{total - accessible} local link(s) were not reachable."
        elif check.type == "w3c_html":
            page_results = [_validate_html_page(client, page) for page in pages]
            per_page_passes = [item[0] for item in page_results]
            passed = _aggregate_scope(check.scope, per_page_passes)
            total_errors = sum(item[1] or 0 for item in page_results)
            earned = _score_w3c(check.points, total_errors)
            details = {"pages": [{"url": pages[i].url, **page_results[i][2]} for i in range(len(page_results))]}
            message = "HTML passed W3C validation." if passed else f"Found {int(total_errors)} HTML validation error(s)."
        elif check.type == "w3c_css":
            css_urls = sorted({url for page in pages for url in page.css_urls})
            passed, error_count, details, message = _validate_css_urls(client, css_urls)
            earned = _score_w3c(check.points, float(error_count) if error_count is not None else None)
        else:
            page_results = [_evaluate_binary_check(check, page, ctx, client) for page in pages]
            per_page_passes = [item[0] for item in page_results]
            passed = _aggregate_scope(check.scope, per_page_passes)
            earned = check.points if passed else 0.0
            details = {"pages": [{"url": pages[i].url, "passed": page_results[i][0], "details": page_results[i][1]} for i in range(len(page_results))]}
            message = "Passed." if passed else "Requirement not met."

    return {
        "checkId": check.id,
        "type": check.type,
        "description": check.description,
        "passed": passed,
        "required": check.required,
        "pointsEarned": round(float(earned), 2),
        "pointsPossible": float(check.points),
        "message": message,
        "details": details,
    }


def grade_submission_with_rubric(submission: Submission, assignment: Assignment) -> dict[str, Any]:
    rubric = RubricDefinition.model_validate(assignment.rubric_json)
    ctx = crawl_for_rubric(submission.project_url, rubric)
    sections: list[dict[str, Any]] = []
    total_earned = 0.0
    total_possible = 0.0
    incomplete = False

    for section in rubric.sections:
        checks = [evaluate_check(check, ctx) for check in section.checks]
        section_earned = round(sum(check["pointsEarned"] for check in checks), 2)
        section_possible = round(sum(check["pointsPossible"] for check in checks), 2)
        total_earned += section_earned
        total_possible += section_possible
        incomplete = incomplete or any(check["required"] and not check["passed"] for check in checks)
        sections.append(
            {
                "sectionId": section.id,
                "title": section.title,
                "description": section.description,
                "pointsEarned": section_earned,
                "pointsPossible": section_possible,
                "checks": checks,
            }
        )

    percent = round((total_earned / total_possible) * 100, 2) if total_possible else 0.0
    graded_at = datetime.utcnow()
    return {
        "submissionId": submission.id,
        "assignmentName": assignment.name,
        "studentName": submission.student_name,
        "projectUrl": submission.project_url,
        "pagesFound": [p.url for p in ctx.pages if p.is_html],
        "totalPointsEarned": round(total_earned, 2),
        "totalPointsPossible": round(total_possible, 2),
        "percentScore": percent,
        "passed": percent >= rubric.passingScore,
        "incomplete": incomplete,
        "gradedAt": graded_at.isoformat() + "Z",
        "sections": sections,
        "errors": ctx.errors,
    }
