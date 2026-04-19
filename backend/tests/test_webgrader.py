from __future__ import annotations

import http.server
import threading
from pathlib import Path

from app.models import Assignment, Submission
from app.schemas import RubricDefinition
from app.services import webgrader_engine
from app.services.rubric_templates import get_rubric_templates


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def serve_directory(path: Path):
    class Handler(QuietHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(path), **kwargs)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_builtin_templates_validate() -> None:
    templates = get_rubric_templates()
    assert templates
    for template in templates:
        rubric = RubricDefinition.model_validate(template["rubric"])
        assert rubric.version == "1.0"
        assert rubric.totalPoints == sum(check.points for section in rubric.sections for check in section.checks)


def test_ticket_alphabet_has_no_ambiguous_characters() -> None:
    assert not {"0", "O", "1", "I", "L"} & set(webgrader_engine.TICKET_ALPHABET)


def test_grade_submission_with_static_rubric(tmp_path, monkeypatch) -> None:
    (tmp_path / "index.html").write_text(
        """<!doctype html>
        <html>
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="style.css">
            <script src="app.js"></script>
          </head>
          <body>
            <h1>Project</h1>
            <img src="logo.png" alt="Logo">
            <a href="about.html">About</a>
          </body>
        </html>""",
        encoding="utf-8",
    )
    (tmp_path / "about.html").write_text("<!doctype html><html><body><h1>About</h1></body></html>", encoding="utf-8")
    (tmp_path / "style.css").write_text("body { display: flex; } @media (max-width: 700px) { body { display: block; } }", encoding="utf-8")
    (tmp_path / "app.js").write_text("function greet() { return true; } document.addEventListener('click', greet);", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"not-really-a-png")

    monkeypatch.setattr(webgrader_engine, "_validate_fetchable_url", lambda url: None)
    server = serve_directory(tmp_path)
    try:
        root = f"http://127.0.0.1:{server.server_port}/index.html"
        rubric_json = {
            "version": "1.0",
            "title": "Static Checks",
            "totalPoints": 60,
            "passingScore": 70,
            "maxPages": 5,
            "sections": [
                {
                    "id": "checks",
                    "title": "Checks",
                    "checks": [
                        {"id": "pages", "type": "page_count", "description": "Two pages", "points": 5, "scope": "all_pages", "params": {"min": 2}},
                        {"id": "h1", "type": "html_element", "description": "Has h1", "points": 5, "scope": "index", "params": {"tag": "h1"}},
                        {"id": "alt", "type": "html_attribute", "description": "Image alt", "points": 5, "scope": "index", "params": {"tag": "img", "attribute": "alt"}},
                        {"id": "css-prop", "type": "css_property", "description": "Uses flex", "points": 5, "scope": "index", "params": {"property": "display", "value": "flex"}},
                        {"id": "css-selector", "type": "css_selector", "description": "Styles body", "points": 5, "scope": "index", "params": {"selector": "body"}},
                        {"id": "js-file", "type": "js_file", "description": "Has JS", "points": 5, "scope": "index", "params": {}},
                        {"id": "js-function", "type": "js_function", "description": "Has greet", "points": 5, "scope": "index", "params": {"functionName": "greet"}},
                        {"id": "js-event", "type": "js_dom_event", "description": "Has click", "points": 5, "scope": "index", "params": {"eventType": "click"}},
                        {"id": "meta", "type": "meta_tag", "description": "Viewport", "points": 5, "scope": "index", "params": {"name": "viewport"}},
                        {"id": "file", "type": "file_exists", "description": "CSS file exists", "points": 5, "scope": "index", "params": {"path": "style.css"}},
                        {"id": "regex", "type": "custom_regex", "description": "Media query", "points": 5, "scope": "index", "params": {"pattern": "@media", "target": "css"}},
                        {"id": "links", "type": "link_crawl", "description": "Links work", "points": 5, "scope": "all_pages", "params": {}},
                    ],
                }
            ],
        }
        assignment = Assignment(name="Static Checks", rubric_json=rubric_json, is_active=True)
        submission = Submission(
            assignment_id="assignment",
            student_name="Jane Smith",
            student_email="jane@example.edu",
            project_url=root,
            ticket_code="A234",
        )

        result = webgrader_engine.grade_submission_with_rubric(submission, assignment)

        assert result["totalPointsEarned"] == 60
        assert result["percentScore"] == 100
        assert result["passed"] is True
        assert len(result["pagesFound"]) == 2
    finally:
        server.shutdown()
