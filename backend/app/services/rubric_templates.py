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


ISCS_1800_FINAL_PROJECT_RUBRIC: dict[str, Any] = {
    "version": "1.0",
    "title": "ISCS 1800 Final Project",
    "description": "Final project rubric aligned to the 500-point ISCS 1800 grading criteria.",
    "totalPoints": 500,
    "passingScore": 70,
    "requiresJavaScript": True,
    "minPages": 5,
    "maxPages": 30,
    "sections": [
        {
            "id": "project_scope_theme_content_quality",
            "title": "Project Scope, Theme, and Content Quality",
            "description": "100 pts: Website has 5 or more complete pages, a strong cohesive theme, substantial content on every page, clear purpose, and strong evidence of effort and creativity. 85 pts: Website has 5 complete pages, a clear theme, and solid content on most pages. 70 pts: Website has 5 pages, theme is mostly clear, and content is adequate but basic. 50 pts: Website is underdeveloped, theme is weak or inconsistent, and content is limited. 0 pts: Project does not meet basic scope.",
            "checks": [
                {
                    "id": "fp1-pages",
                    "type": "page_count",
                    "description": "Has at least five crawlable HTML pages",
                    "points": 40,
                    "scope": "all_pages",
                    "params": {"min": 5},
                },
                {
                    "id": "fp1-title",
                    "type": "html_element",
                    "description": "Each page includes a <title>",
                    "points": 10,
                    "scope": "all_pages",
                    "params": {"tag": "title", "minCount": 1},
                },
                {
                    "id": "fp1-heading",
                    "type": "html_element",
                    "description": "Each page includes a top-level heading",
                    "points": 15,
                    "scope": "all_pages",
                    "params": {"tag": "h1", "minCount": 1},
                },
                {
                    "id": "fp1-content",
                    "type": "html_element",
                    "description": "Each page includes paragraph content",
                    "points": 15,
                    "scope": "all_pages",
                    "params": {"tag": "p", "minCount": 1},
                },
                {
                    "id": "fp1-theme",
                    "type": "html_element",
                    "description": "All pages link an external stylesheet for cohesive theme",
                    "points": 20,
                    "scope": "all_pages",
                    "params": {"tag": "link", "minCount": 1},
                },
            ],
        },
        {
            "id": "navigation_organization_semantic_html",
            "title": "Navigation, Organization, and Semantic HTML",
            "description": "100 pts: Navigation is clear, consistent, and fully functional across the site. Semantic tags are used correctly and extensively. 85 pts: Navigation works well with only minor issues and semantic tags are mostly correct. 70 pts: Navigation mostly works and semantic use is inconsistent. 50 pts: Navigation is confusing or partly broken and structure is weak. 0 pts: Navigation and semantic structure are largely missing or broken.",
            "checks": [
                {
                    "id": "fp2-link-crawl",
                    "type": "link_crawl",
                    "description": "Internal links are reachable",
                    "points": 30,
                    "scope": "all_pages",
                    "params": {},
                },
                {
                    "id": "fp2-nav",
                    "type": "html_element",
                    "description": "Navigation element present on all pages",
                    "points": 20,
                    "scope": "all_pages",
                    "params": {"tag": "nav", "minCount": 1},
                },
                {
                    "id": "fp2-header",
                    "type": "html_element",
                    "description": "Header element used on all pages",
                    "points": 10,
                    "scope": "all_pages",
                    "params": {"tag": "header", "minCount": 1},
                },
                {
                    "id": "fp2-main",
                    "type": "html_element",
                    "description": "Main element used on all pages",
                    "points": 10,
                    "scope": "all_pages",
                    "params": {"tag": "main", "minCount": 1},
                },
                {
                    "id": "fp2-footer",
                    "type": "html_element",
                    "description": "Footer element used on all pages",
                    "points": 10,
                    "scope": "all_pages",
                    "params": {"tag": "footer", "minCount": 1},
                },
                {
                    "id": "fp2-semantic-section",
                    "type": "html_element",
                    "description": "Semantic sectional content (section/article/aside) is present",
                    "points": 10,
                    "scope": "any_page",
                    "params": {"tag": "section", "minCount": 1},
                },
                {
                    "id": "fp2-html-validity",
                    "type": "w3c_html",
                    "description": "HTML structure validates with W3C",
                    "points": 10,
                    "scope": "all_pages",
                    "params": {},
                },
            ],
        },
        {
            "id": "css_visual_design_responsiveness",
            "title": "CSS, Visual Design, and Responsiveness",
            "description": "100 pts: Entire site is styled with an external stylesheet and has polished, consistent, readable, responsive design. 85 pts: External stylesheet is used correctly with minor layout issues. 70 pts: Styling and responsive behavior are basic. 50 pts: Styling is inconsistent and responsiveness is weak. 0 pts: External stylesheet and/or responsive requirements are completely missed.",
            "checks": [
                {
                    "id": "fp3-external-css",
                    "type": "html_element",
                    "description": "All pages link an external stylesheet",
                    "points": 25,
                    "scope": "all_pages",
                    "params": {"tag": "link", "minCount": 1},
                },
                {
                    "id": "fp3-typography",
                    "type": "css_property",
                    "description": "CSS defines typography (font-family)",
                    "points": 15,
                    "scope": "any_page",
                    "params": {"property": "font-family"},
                },
                {
                    "id": "fp3-color",
                    "type": "css_property",
                    "description": "CSS sets color styles",
                    "points": 10,
                    "scope": "any_page",
                    "params": {"property": "color"},
                },
                {
                    "id": "fp3-background",
                    "type": "css_property",
                    "description": "CSS sets background styles",
                    "points": 10,
                    "scope": "any_page",
                    "params": {"property": "background"},
                },
                {
                    "id": "fp3-layout",
                    "type": "css_property",
                    "description": "Uses a modern layout method (flex or grid)",
                    "points": 10,
                    "scope": "any_page",
                    "params": {"property": "display", "value": "(flex|grid)"},
                },
                {
                    "id": "fp3-responsive",
                    "type": "custom_regex",
                    "description": "Uses media queries for responsive behavior",
                    "points": 30,
                    "scope": "any_page",
                    "params": {"target": "css", "pattern": "@media\\s*[^\\{]+\\{"},
                },
            ],
        },
        {
            "id": "required_elements_media_integration",
            "title": "Required Elements and Media Integration",
            "description": "100 pts: Includes required images, text, table, list, and form elements that are meaningful and functional; any audio/video used has controls and no autoplay. 85 pts: Required elements are present with minor issues. 70 pts: Required elements are present but basic. 50 pts: Required elements are weak or incomplete. 0 pts: Required elements are largely omitted.",
            "checks": [
                {
                    "id": "fp4-images",
                    "type": "html_element",
                    "description": "Includes image content",
                    "points": 20,
                    "scope": "any_page",
                    "params": {"tag": "img", "minCount": 1},
                },
                {
                    "id": "fp4-text",
                    "type": "html_element",
                    "description": "Includes textual content",
                    "points": 20,
                    "scope": "any_page",
                    "params": {"tag": "p", "minCount": 1},
                },
                {
                    "id": "fp4-table",
                    "type": "html_element",
                    "description": "Includes a table",
                    "points": 20,
                    "scope": "any_page",
                    "params": {"tag": "table", "minCount": 1},
                },
                {
                    "id": "fp4-list",
                    "type": "html_element",
                    "description": "Includes a list",
                    "points": 20,
                    "scope": "any_page",
                    "params": {"tag": "li", "minCount": 1},
                },
                {
                    "id": "fp4-form",
                    "type": "html_element",
                    "description": "Includes a form",
                    "points": 20,
                    "scope": "any_page",
                    "params": {"tag": "form", "minCount": 1},
                },
            ],
        },
        {
            "id": "javascript_validation_security_originality_explainability",
            "title": "JavaScript, Input Validation, Security, Originality, and Explainability",
            "description": "100 pts: JavaScript is integrated and functional, inputs are validated before use, and secure coding awareness is evident. 85 pts: JavaScript and validation are strong with minor gaps. 70 pts: JavaScript is functional but basic. 50 pts: JavaScript is weak or partially broken and validation is incomplete. 0 pts: JavaScript/validation requirements were missed or work is not explainable.",
            "checks": [
                {
                    "id": "fp5-js-present",
                    "type": "js_file",
                    "description": "Includes JavaScript",
                    "points": 20,
                    "scope": "any_page",
                    "params": {},
                },
                {
                    "id": "fp5-dom-event",
                    "type": "js_dom_event",
                    "description": "Uses JavaScript DOM event handling",
                    "points": 15,
                    "scope": "any_page",
                    "params": {},
                },
                {
                    "id": "fp5-validation-core",
                    "type": "custom_regex",
                    "description": "Includes input validation logic",
                    "points": 30,
                    "scope": "any_page",
                    "params": {
                        "target": "js",
                        "pattern": "(checkValidity|reportValidity|setCustomValidity|trim\\s*\\(\\)|isNaN|parseInt|parseFloat|RegExp)",
                    },
                },
                {
                    "id": "fp5-validation-flow",
                    "type": "custom_regex",
                    "description": "Validation is connected to form/input flow",
                    "points": 20,
                    "scope": "any_page",
                    "params": {
                        "target": "js",
                        "pattern": "(addEventListener\\s*\\(\\s*['\"](?:submit|input|change)['\"]|preventDefault\\s*\\()",
                    },
                },
                {
                    "id": "fp5-safe-dom",
                    "type": "custom_regex",
                    "description": "Uses safe DOM update APIs",
                    "points": 15,
                    "scope": "any_page",
                    "params": {"target": "js", "pattern": "(textContent|createElement|appendChild)"},
                },
            ],
        },
    ],
}


def get_rubric_templates() -> list[dict[str, Any]]:
    return [
        {"name": "Basic HTML/CSS Website", "rubric": BASIC_HTML_CSS_RUBRIC},
        {"name": "Multi-Page Web Project", "rubric": MULTI_PAGE_WEB_PROJECT_RUBRIC},
        {"name": "ISCS 1800 Final Project", "rubric": ISCS_1800_FINAL_PROJECT_RUBRIC},
    ]


def bootstrap_default_assignments(db: Session) -> None:
    existing_names = {name for (name,) in db.query(Assignment.name).all()}
    created = 0
    for index, template in enumerate(get_rubric_templates()):
        rubric = template["rubric"]
        if rubric["title"] in existing_names:
            continue
        db.add(
            Assignment(
                name=rubric["title"],
                description=rubric.get("description"),
                rubric_json=rubric,
                is_active=(index == 0 and not existing_names and created == 0),
            )
        )
        created += 1

    if created:
        db.commit()
