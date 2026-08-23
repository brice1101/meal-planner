import sqlite3

import pytest

from meal_planner import db
from meal_planner.webapp import app as flask_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.sqlite")
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO recipes (recipe_id, title, instructions_url) VALUES (1, 'Garlic Bread', 'https://example.com/garlic-bread')"
    )
    conn.executemany(
        "INSERT INTO ingredients (ingredient_id, ingredient_name) VALUES (?, ?)",
        [(1, "garlic"), (2, "bread")],
    )
    conn.executemany(
        "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
        [(1, 1, "2", None), (1, 2, "1", "loaf")],
    )
    conn.commit()
    conn.close()

    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as test_client:
        yield test_client


def test_index_lists_ingredients_for_autocomplete(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"garlic" in response.data


def test_search_finds_matching_recipe(client):
    response = client.get("/api/search?ingredient=garlic&match_all=false")
    assert response.status_code == 200
    data = response.get_json()
    assert data["results"] == [
        {"recipe_id": 1, "title": "Garlic Bread", "instructions_url": "https://example.com/garlic-bread"}
    ]


def test_search_with_no_ingredients_returns_empty(client):
    response = client.get("/api/search")
    assert response.get_json() == {"results": []}


def test_recipe_detail_page_renders(client):
    response = client.get("/recipe/1")
    assert response.status_code == 200
    assert b"Garlic Bread" in response.data
    assert b"https://example.com/garlic-bread" in response.data


def test_recipe_detail_missing_id_returns_404(client):
    response = client.get("/recipe/999")
    assert response.status_code == 404
