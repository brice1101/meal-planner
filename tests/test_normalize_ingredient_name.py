import pytest

from gousto_scraper import normalize_ingredient_name


@pytest.mark.parametrize("raw, expected", [
    ("garlic", "garlic"),
    ("garlic clove", "garlic"),
    ("garlic cloves", "garlic"),
    ("minced garlic", "garlic"),
    ("diced garlic", "garlic"),
    ("finely chopped tomatoes", "tomato"),
    ("tomatoes", "tomato"),
    ("tomato", "tomato"),
    ("grated italian hard cheese", "italian hard cheese"),
    ("italian hard cheese", "italian hard cheese"),
    ("1 pot of crème fraîche", "crème fraîche"),
    ("1 tomato paste sachet", "tomato paste"),
    ("1 red wine vinegar sachet", "red wine vinegar"),
    ("1 dijon mustard pot", "dijon mustard"),
    ("asparagus spears", "asparagus spear"),
    ("/2 beef stock cube", "beef stock cube"),
])
def test_known_duplicates_collapse(raw, expected):
    assert normalize_ingredient_name(raw) == expected


@pytest.mark.parametrize("raw", [
    "dried basil",
    "basil",
    "ground coriander",
    "coriander",
])
def test_genuinely_different_products_stay_distinct(raw):
    # "dried"/"ground" mark a different product from the fresh/whole version,
    # so normalizing must not merge these with their bare counterpart.
    assert normalize_ingredient_name(raw) == raw


def test_never_returns_empty_string():
    # Every word being stripped shouldn't lose the ingredient entirely.
    assert normalize_ingredient_name("1 pot") != ""
