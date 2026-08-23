import sqlite3

import pytest

from meal_planner import db


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.sqlite")
    db.init_db(path)
    return path


def _seed(db_path, recipes, ingredients, links):
    """
    :param recipes: list of (recipe_id, title, instructions_url)
    :param ingredients: list of (ingredient_id, ingredient_name)
    :param links: list of (recipe_id, ingredient_id, quantity, unit)
    """
    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO recipes (recipe_id, title, instructions_url) VALUES (?, ?, ?)", recipes
    )
    conn.executemany(
        "INSERT INTO ingredients (ingredient_id, ingredient_name) VALUES (?, ?)", ingredients
    )
    conn.executemany(
        "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
        links,
    )
    conn.commit()
    conn.close()


def test_init_db_is_idempotent(db_path):
    db.init_db(db_path)  # should not raise on a second call
    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"recipes", "ingredients", "recipe_ingredients"} <= tables


def test_get_all_ingredients_alphabetical(db_path):
    _seed(
        db_path,
        recipes=[(1, "Onion Soup", "https://example.com/1")],
        ingredients=[(1, "onion"), (2, "garlic"), (3, "stock")],
        links=[(1, 1, "2", None), (1, 2, "1", None), (1, 3, "500", "ml")],
    )
    assert db.get_all_ingredients(db_path) == ["garlic", "onion", "stock"]


def test_get_recipe_by_ingredients_match_any(db_path):
    _seed(
        db_path,
        recipes=[
            (1, "Garlic Bread", "https://example.com/garlic-bread"),
            (2, "Tomato Soup", "https://example.com/tomato-soup"),
        ],
        ingredients=[(1, "garlic"), (2, "tomato"), (3, "bread")],
        links=[(1, 1, "2", None), (1, 3, "1", None), (2, 2, "4", None)],
    )
    results = db.get_recipe_by_ingredients(["garlic"], match_all=False, db_path=db_path)
    assert results == [
        {"recipe_id": 1, "title": "Garlic Bread", "instructions_url": "https://example.com/garlic-bread"}
    ]


def test_get_recipe_by_ingredients_match_all_requires_every_ingredient(db_path):
    _seed(
        db_path,
        recipes=[(1, "Garlic Bread", "https://example.com/garlic-bread")],
        ingredients=[(1, "garlic"), (2, "bread"), (3, "butter")],
        links=[(1, 1, "2", None), (1, 2, "1", None)],
    )
    # Recipe has garlic + bread but not butter.
    assert db.get_recipe_by_ingredients(
        ["garlic", "bread", "butter"], match_all=True, db_path=db_path
    ) == []
    assert db.get_recipe_by_ingredients(
        ["garlic", "bread"], match_all=True, db_path=db_path
    ) == [{"recipe_id": 1, "title": "Garlic Bread", "instructions_url": "https://example.com/garlic-bread"}]


def test_get_recipe_by_ingredients_empty_list_returns_empty(db_path):
    assert db.get_recipe_by_ingredients([], match_all=False, db_path=db_path) == []
    assert db.get_recipe_by_ingredients([], match_all=True, db_path=db_path) == []


def test_get_recipe_detail(db_path):
    _seed(
        db_path,
        recipes=[(1, "Garlic Bread", "https://example.com/garlic-bread")],
        ingredients=[(1, "garlic"), (2, "bread")],
        links=[(1, 1, "2", None), (1, 2, "1", "loaf")],
    )
    detail = db.get_recipe_detail(1, db_path)
    assert detail == {
        "recipe_id": 1,
        "title": "Garlic Bread",
        "instructions_url": "https://example.com/garlic-bread",
        "ingredients": [
            {"name": "bread", "quantity": "1", "unit": "loaf"},
            {"name": "garlic", "quantity": "2", "unit": None},
        ],
    }


def test_get_recipe_detail_missing_id_returns_none(db_path):
    assert db.get_recipe_detail(999, db_path) is None
