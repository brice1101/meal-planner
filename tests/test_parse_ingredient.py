from meal_planner.scraper import parse_fraction, parse_ingredient


def test_parse_fraction_valid():
    assert parse_fraction("1/2") == 0.5


def test_parse_fraction_invalid_returns_none():
    assert parse_fraction("not-a-fraction") is None
    assert parse_fraction("1") is None


def test_parentheses_with_unit():
    # E.g. "Soy Sauce (15ml)"
    assert parse_ingredient("Soy Sauce (15ml)") == ("Soy Sauce", "15.0", "ml")


def test_parentheses_with_multiplier():
    # E.g. "Onion (150g) x2"
    name, quantity, unit = parse_ingredient("Onion (150g) x2")
    assert name == "Onion"
    assert unit == "g"
    assert float(quantity) == 300.0


def test_quantity_x_name():
    # E.g. "2 x Onion"
    assert parse_ingredient("2 x Onion") == ("Onion", "2.0", None)


def test_name_x_quantity():
    # E.g. "Onion x2"
    assert parse_ingredient("Onion x2") == ("Onion", "2.0", None)


def test_quantity_unit_name():
    # E.g. "15ml Soy Sauce"
    assert parse_ingredient("15ml Soy Sauce") == ("Soy Sauce", "15.0", "ml")


def test_quantity_name():
    # E.g. "2 Onion"
    assert parse_ingredient("2 Onion") == ("Onion", "2.0", None)


def test_name_only():
    assert parse_ingredient("Garlic") == ("Garlic", None, None)


def test_allergen_marker_is_stripped():
    name, _, _ = parse_ingredient("Peanuts†")
    assert "†" not in name


def test_leading_fraction_quantity():
    # Regression: alternation order used to make "1/2" match only "1",
    # leaving "/2 Beef Stock Cube" as the name.
    name, quantity, unit = parse_ingredient("1/2 Beef Stock Cube")
    assert name == "Beef Stock Cube"
    assert float(quantity) == 0.5
    assert unit is None
