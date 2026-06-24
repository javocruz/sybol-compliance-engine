"""Tests for regulation source URL resolution."""

from src.rag.source_urls import resolve_source_url


def test_resolve_http_url_unchanged():
    url = "https://eur-lex.europa.eu/eli/reg/2024/1689"
    assert resolve_source_url(url) == url


def test_resolve_absolute_filesystem_path():
    assert (
        resolve_source_url("/Users/dev/project/research/regulations/gdpr.pdf")
        == "/api/regulations/gdpr.pdf"
    )


def test_resolve_relative_path():
    assert (
        resolve_source_url("research/regulations/eu_ai_act.pdf")
        == "/api/regulations/eu_ai_act.pdf"
    )


def test_resolve_empty_path_uses_regulation_type():
    assert resolve_source_url("", "gdpr") == "/api/regulations/gdpr.pdf"


def test_resolve_unknown_path_without_type_returns_empty():
    assert resolve_source_url("") == ""
