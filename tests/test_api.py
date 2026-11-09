import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app, items

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_items():
    """Empty the in-memory list before and after every test."""
    items.clear()
    yield
    items.clear()


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_items_is_empty_at_start():
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == []


def test_create_item():
    response = client.post("/items", json={"name": "book", "price": 12.5})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "book", "price": 12.5}


def test_created_item_appears_in_list():
    client.post("/items", json={"name": "book", "price": 12.5})
    response = client.get("/items")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "book"


def test_ids_increment():
    first = client.post("/items", json={"name": "book", "price": 12.5})
    second = client.post("/items", json={"name": "pen", "price": 2.0})
    assert first.json()["id"] == 1
    assert second.json()["id"] == 2


def test_get_item_by_id():
    client.post("/items", json={"name": "book", "price": 12.5})
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "book"


def test_get_unknown_item_returns_404():
    response = client.get("/items/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}


def test_create_item_with_invalid_body_returns_422():
    response = client.post("/items", json={"name": "book", "price": "not-a-number"})
    assert response.status_code == 422


def test_create_item_with_missing_field_returns_422():
    response = client.post("/items", json={"name": "book"})
    assert response.status_code == 422


def test_request_is_logged_with_structured_fields(caplog):
    with caplog.at_level(logging.INFO, logger="api"):
        client.get("/health")
    fields = caplog.records[-1].extra_fields
    assert fields["method"] == "GET"
    assert fields["path"] == "/health"
    assert fields["status"] == 200
    assert "request_id" in fields
    assert "duration_ms" in fields


def test_response_contains_request_id_header():
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_unhandled_error_returns_500_and_is_logged(caplog):
    with caplog.at_level(logging.ERROR, logger="api"):
        response = client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_metrics_endpoint_exposes_request_counter():
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert 'path="/health"' in response.text


def test_metrics_endpoint_exposes_latency_histogram():
    client.get("/health")
    response = client.get("/metrics")
    assert "http_request_duration_seconds_bucket" in response.text


def test_metrics_use_route_template_not_raw_path():
    client.get("/items/99")
    response = client.get("/metrics")
    assert 'path="/items/{item_id}"' in response.text
    assert 'path="/items/99"' not in response.text