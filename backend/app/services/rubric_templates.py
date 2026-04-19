from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import Assignment


BASIC_HTML_CSS_RUBRIC: dict[str, Any] = {
    "version": "1.0",
    "title": "Basic HTML/CSS Website",
    "description": "Single-page website demonstrating semantic HTML and CSS styling.",
    "totalPoints": 100,
    "passingScore": 70,
    "requiresJavaScript": False,
    "minPages": 1,
    "maxPages": 20,
    "sections": [
        {
            "id": "structure",
            "title": "HTML Structure",
            "checks": [
                {
                    "id": "s1",
                    "type": "html_element",
                    "description": "Has DOCTYPE declaration",
                    "points": 5,
                    "params": {"tag": "!DOCTYPE"},
                    "scope": "index",
                },
                {
                    "id": "s2",
                    "type": "html_element",
                    "description": "Uses <header>",
                    "points": 5,
                    "params": {"tag": "header"},
                    "scope": "index",
                },
                {
                    "id": "s3",
                    "type": "html_element",
                    "description": "Uses <nav>",
                    "points": 5,
                    "params": {"tag": "nav"},
                    "scope": "index",
                },
                {
                    "id": "s4",
                    "type": "html_element",
                    "description": "Uses <main>",
                    "points": 5,
                    "params": {"tag": "main"},
                    "scope": "index",
                },
                {
                    "id": "s5",
                    "type": "html_element",
                    "description": "Uses <footer>",
                    "points": 5,
                    "params": {"tag": "footer"},
                    "scope": "index",
                },
                {
                    "id": "s6",
                    "type": "html_element",
                    "description": "Has at least one <h1>",
                    "points": 5,
                    "params": {"tag": "h1", "minCount": 1},
                    "scope": "index",
                },
                {
                    "id": "s7",
                    "type": "meta_tag",
                    "description": "Has viewport meta tag",
                    "points": 5,
                    "params": {"name": "viewport"},
                    "scope": "index",
                },
            ],
        },
        {
            "id": "css",
            "title": "CSS Styling",
            "checks": [
                {
                    "id": "c1",
                    "type": "html_element",
                    "description": "Links external CSS file",
                    "points": 10,
                    "params": {"tag": "link"},
                    "scope": "index",
                },
                {
                    "id": "c2",
                    "type": "css_property",
                    "description": "Sets font-family",
                    "points": 5,
                    "params": {"property": "font-family"},
                    "scope": "index",
                },
                {
                    "id": "c3",
                    "type": "css_property",
                    "description": "Uses flexbox or grid",
                    "points": 10,
                    "params": {"property": "display", "value": "(flex|grid)"},
                    "scope": "index",
                },
                {
                    "id": "c4",
                    "type": "css_property",
                    "description": "Sets background color",
                    "points": 10,
                    "params": {"property": "background"},
                    "scope": "index",
                },
            ],
        },
        {
            "id": "validation",
            "title": "Validation & Links",
            "checks": [
                {
                    "id": "v1",
                    "type": "w3c_html",
                    "description": "Passes W3C HTML Validation",
                    "points": 20,
                    "params": {},
                    "scope": "index",
                },
                {
                    "id": "v2",
                    "type": "link_crawl",
                    "description": "All local links accessible",
                    "points": 10,
                    "params": {},
                    "scope": "all_pages",
                },
            ],
        },
    ],
}


MULTI_PAGE_WEB_PROJECT_RUBRIC: dict[str, Any] = {
    "version": "1.0",
    "title": "Multi-Page HTML/CSS/JavaScript Website",
    "description": "Rubric for a multi-page student website with shared styling, required structures, validation, and basic JavaScript.",
    "totalPoints": 100,
    "passingScore": 70,
    "requiresJavaScript": True,
    "minPages": 5,
    "maxPages": 30,
    "sections": [
        {
            "id": "scope_theme_content",
            "title": "Scope, Theme, and Content",
            "checks": [
                {"id": "scope-pages", "type": "page_count", "description": "At least five crawlable HTML pages", "points": 10, "scope": "all_pages", "params": {"min": 5}},
            ],
        },
        {
            "id": "structure",
            "title": "Required HTML Structures",
            "checks": [
                {"id": "structure-form", "type": "html_element", "description": "Includes a form", "points": 10, "scope": "any_page", "params": {"tag": "form"}},
                {"id": "structure-table", "type": "html_element", "description": "Includes a table", "points": 10, "scope": "any_page", "params": {"tag": "table"}},
                {"id": "structure-list", "type": "html_element", "description": "Includes an ordered or unordered list", "points": 10, "scope": "any_page", "params": {"tag": "li"}},
                {"id": "structure-media", "type": "html_element", "description": "Includes image, audio, or video media", "points": 10, "scope": "any_page", "params": {"tag": "img"}},
            ],
        },
        {
            "id": "css_responsive",
            "title": "CSS and Responsiveness",
            "checks": [
                {"id": "css-external", "type": "html_element", "description": "Links an external stylesheet", "points": 10, "scope": "all_pages", "params": {"tag": "link", "minCount": 1}},
                {"id": "css-media", "type": "custom_regex", "description": "Uses a media query for responsive design", "points": 10, "scope": "any_page", "params": {"pattern": "@media\\s*[^{]+\\{", "target": "css"}},
            ],
        },
        {
            "id": "navigation_validation",
            "title": "Navigation and Validation",
            "checks": [
                {"id": "nav-links", "type": "link_crawl", "description": "Internal links are reachable", "points": 10, "scope": "all_pages", "params": {}},
                {"id": "valid-html", "type": "w3c_html", "description": "HTML validates with W3C", "points": 20, "scope": "all_pages", "params": {}},
            ],
        },
    ],
}


def get_rubric_templates() -> list[dict[str, Any]]:
    return [
        {"name": "Basic HTML/CSS Website", "rubric": BASIC_HTML_CSS_RUBRIC},
        {"name": "Multi-Page Web Project", "rubric": MULTI_PAGE_WEB_PROJECT_RUBRIC},
    ]


def bootstrap_default_assignments(db: Session) -> None:
    if db.query(Assignment).count() > 0:
        return

    for index, template in enumerate(get_rubric_templates()):
        rubric = template["rubric"]
        db.add(
            Assignment(
                name=rubric["title"],
                description=rubric.get("description"),
                rubric_json=rubric,
                is_active=index == 0,
            )
        )
    db.commit()
