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
    response = client.post("/items", json={"name": "book", "price": 13})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "book", "price": 13}


def test_created_item_appears_in_list():
    client.post("/items", json={"name": "book", "price": 13})
    response = client.get("/items")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "book"


def test_ids_increment():
    first = client.post("/items", json={"name": "book", "price": 13})
    second = client.post("/items", json={"name": "pen", "price": 2.0})
    assert first.json()["id"] == 1
    assert second.json()["id"] == 2


def test_get_item_by_id():
    client.post("/items", json={"name": "book", "price": 13})
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