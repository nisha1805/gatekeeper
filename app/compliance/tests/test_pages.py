import re

from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_the_start_page_is_served_under_app():
    response = client.get("/app/")
    assert response.status_code == 200
    assert "Compliance copilot" in response.text


def test_the_root_redirects_to_the_page():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/app/"


def test_the_page_has_a_strict_content_security_policy():
    headers = client.get("/app/").headers
    policy = headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "unsafe-inline" not in policy and "unsafe-eval" not in policy
    assert "frame-ancestors 'none'" in policy
    assert headers["x-content-type-options"] == "nosniff"


def test_the_policy_is_also_sent_with_scripts_and_styles():
    for path in ("/app/app.js", "/app/logic.js", "/app/style.css"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "content-security-policy" in response.headers


def test_the_page_has_no_inline_script_or_style():
    html = client.get("/app/").text
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert "<style" not in html
    assert " style=" not in html
    assert " onclick=" not in html


def test_the_scripts_never_write_server_text_as_html():
    for path in ("/app/app.js", "/app/logic.js"):
        source = client.get(path).text
        assert "innerHTML" not in source and "outerHTML" not in source
        assert "insertAdjacentHTML" not in source and "document.write" not in source


def test_the_api_routes_still_win_over_the_pages():
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/questions").status_code == 200


def test_the_api_has_no_security_headers_it_does_not_need():
    assert "content-security-policy" not in client.get("/health").headers


def test_the_page_does_not_serve_files_outside_its_folder():
    assert client.get("/app/../api.py").status_code in (400, 404)
    assert client.get("/app/%2e%2e/api.py").status_code in (400, 404)
