import sqlite3

import pytest

from meal_planner import db
from meal_planner.scraper import dedupe_ingredients, insert_recipe_data


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.sqlite")
    db.init_db(path)
    return path


def test_insert_recipe_data_normalizes_ingredient_names(db_path):
    insert_recipe_data(
        {
            "title": "Garlic Bread",
            "url": "https://example.com/garlic-bread",
            "ingredients": ["2 x minced Garlic", "1 Garlic Clove"],
        },
        db_path,
    )
    # Both ingredient lines should normalize to the same "garlic" row.
    assert db.get_all_ingredients(db_path) == ["garlic"]


def test_insert_recipe_data_is_idempotent_on_url(db_path):
    recipe = {
        "title": "Garlic Bread",
        "url": "https://example.com/garlic-bread",
        "ingredients": ["Garlic"],
    }
    insert_recipe_data(recipe, db_path)
    insert_recipe_data(recipe, db_path)  # simulates re-scraping an overlapping page

    conn = sqlite3.connect(db_path)
    recipe_count = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    conn.close()
    assert recipe_count == 1


def test_dedupe_ingredients_merges_and_repoints_links(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO recipes (recipe_id, title, instructions_url) VALUES (1, 'Garlic Bread', 'https://example.com/1')"
    )
    conn.executemany(
        "INSERT INTO ingredients (ingredient_id, ingredient_name) VALUES (?, ?)",
        [(1, "garlic"), (2, "garlic clove"), (3, "garlic cloves")],
    )
    conn.executemany(
        "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
        [(1, 1, "1", None), (1, 2, "2", None), (1, 3, "3", None)],
    )
    conn.commit()
    conn.close()

    dedupe_ingredients(db_path)

    conn = sqlite3.connect(db_path)
    ingredient_names = [row[0] for row in conn.execute("SELECT ingredient_name FROM ingredients")]
    link_count = conn.execute("SELECT COUNT(*) FROM recipe_ingredients").fetchone()[0]
    orphaned = conn.execute(
        "SELECT COUNT(*) FROM recipe_ingredients ri "
        "LEFT JOIN ingredients i ON ri.ingredient_id = i.ingredient_id "
        "WHERE i.ingredient_id IS NULL"
    ).fetchone()[0]
    conn.close()

    assert ingredient_names == ["garlic"]
    # The recipe only ever needs one link to "garlic", however many
    # duplicate ingredient rows pointed at it before the merge.
    assert link_count == 1
    assert orphaned == 0


def test_dedupe_ingredients_is_idempotent(db_path):
    insert_recipe_data(
        {"title": "R", "url": "https://example.com/r", "ingredients": ["Garlic"]}, db_path
    )
    dedupe_ingredients(db_path)
    dedupe_ingredients(db_path)  # should merge nothing the second time, not error
    assert db.get_all_ingredients(db_path) == ["garlic"]
