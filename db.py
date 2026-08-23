"""Shared SQLite access layer: schema creation and the read queries used by
both the scraper and the recipe-search frontend."""

import sqlite3

DB_PATH = "recipes.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    instructions_url TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id INTEGER PRIMARY KEY,
    ingredient_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity TEXT,
    unit TEXT,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);
"""


def init_db(db_path=DB_PATH):
    """Creates the database schema if it doesn't already exist."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_all_ingredients(db_path=DB_PATH):
    """Returns every distinct ingredient name in the database, alphabetically."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_name FROM ingredients ORDER BY ingredient_name")
    ingredients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ingredients


def get_recipe_by_ingredients(ingredients, match_all, db_path=DB_PATH):
    """
    Finds recipes matching the given ingredient names.

    :param ingredients: list of ingredient name strings
    :param match_all: if True, a matching recipe must contain every given
        ingredient; if False, a recipe matching any one of them is included
    :param db_path: Path to .sqlite database file in string format
    :return: list of (title, instructions_url) tuples
    """
    if not ingredients:
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    placeholders = ', '.join(['?'] * len(ingredients))

    if match_all:
        query = f"""
        SELECT r.title, r.instructions_url
        FROM recipes r
        JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
        JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
        WHERE i.ingredient_name IN ({placeholders})
        GROUP BY r.recipe_id
        HAVING COUNT(DISTINCT i.ingredient_id) = ?"""
        cursor.execute(query, ingredients + [len(ingredients)])
    else:
        query = f"""
        SELECT DISTINCT r.title, r.instructions_url
        FROM recipes r
        JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
        JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
        WHERE i.ingredient_name IN ({placeholders})"""
        cursor.execute(query, ingredients)

    results = cursor.fetchall()
    conn.close()
    return results
