import re
import sqlite3
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DB_PATH = "recipes.sqlite"
CATEGORY_URL = "https://www.gousto.co.uk/cookbook/recipes"

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


def build_driver():
    """Creates a Chrome WebDriver. Selenium Manager auto-resolves the correct
    chromedriver binary for the host OS/browser, so no driver path is needed."""
    return webdriver.Chrome()


def scrape_gousto_recipe(url, driver):
    """
    Scrapes recipe information from a Gousto recipe webpage.

    :param url: str
    :param driver: an active Selenium WebDriver
    :return: Dictionary of recipe information
    """

    try:
        driver.get(url)

        # Wait for the main recipe title to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )

        # Get heading of page, corresponding to recipe title
        title = driver.find_element(By.TAG_NAME, "h1").text.strip() if driver.find_elements(By.TAG_NAME,
                                                                                            "h1") else "Title not found"

        # Get the list of ingredients
        ingredients_list = []
        # CSS-module class names carry a build hash suffix (e.g. "__14UI0")
        # that changes whenever Gousto rebuilds their frontend; matching on a
        # substring of the stable prefix instead means this selector doesn't
        # need updating every time that hash changes.
        ingredients_elements = driver.find_elements(By.CSS_SELECTOR, "ul[class*='IngredientList_ingredientList__'] li")
        for ingredient in ingredients_elements:
            ingredients_list.append(ingredient.text.strip())

        # Remove duplicates found in some erroneous ingredient lists
        unique_ingredients = list(set(ingredients_list))

        # Return a dictionary with necessary information
        return {
            'title': title,
            'ingredients': unique_ingredients,
            'url': url
        }

    # Handle exceptions during scraping by returning None instead
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def parse_fraction(fraction_str):
    """Parses a fraction string (e.g., "1/2") into a float."""
    parts = fraction_str.split("/")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return float(parts[0]) / float(parts[1])
    return None


def parse_ingredient(ingredient_line):
    """
    Parses an ingredient line to extract the ingredient name, quantity, and unit.

    :param ingredient_line: str
    :returns: tuple of ingredient information
    """
    ingredient_str = ingredient_line.replace('†','').strip() # Remove allergen marker from ingredients where needed
    ingredient_str = ingredient_str.strip()

    quantity_regex = r"(\d+(?:\.\d+)?|\d+/\d+)"

    # Case 1: Parentheses with optional x quantity
    # E.g. Soy Sauce (15ml)
    parentheses_match = re.search(rf"^(.*?)\s*\((?P<quantity_parentheses>{quantity_regex})\s*(?P<unit_parentheses>(?:g|kg|ml|l|tsp|tbsp|cup|oz|lb|pinch|dash|pcs|pot of|pots of)\b)?\)\s*(?:x\s*(?P<multiplier>\d+(?:\.\d+)?))?$", ingredient_str)
    if parentheses_match:
        name = parentheses_match.group(1).strip()
        quantity_str = parentheses_match.group("quantity_parentheses")
        unit = parentheses_match.group("unit_parentheses")
        multiplier = parentheses_match.group("multiplier")

        quantity = float(quantity_str) if "." in quantity_str or quantity_str.isdigit() else parse_fraction(quantity_str)

        if multiplier:
            quantity *= float(multiplier)
        return name, str(quantity), unit

    # Case 2: Quantity x Name
    # E.g. 2 x Onion
    quantity_x_start_match = re.search(rf"^(?P<quantity_x_start>{quantity_regex})\s*x\s*(?P<name_x_start>.*)$", ingredient_str)
    if quantity_x_start_match:
        quantity_str = quantity_x_start_match.group("quantity_x_start")
        quantity = float(quantity_str) if "." in quantity_str or quantity_str.isdigit() else parse_fraction(quantity_str)
        return quantity_x_start_match.group("name_x_start").strip(), str(quantity), None

    # Case 3: Name x Quantity
    # E.g. Onion x2
    name_x_end_match = re.search(rf"^(?P<name_x_end>.*)\s*x\s*(?P<quantity_x_end>{quantity_regex})$", ingredient_str)
    if name_x_end_match:
        quantity_str = name_x_end_match.group("quantity_x_end")
        quantity = float(quantity_str) if "." in quantity_str or quantity_str.isdigit() else parse_fraction(quantity_str)
        return name_x_end_match.group("name_x_end").strip(), str(quantity), None

    # Case 4: Quantity Unit Name
    # E.g. 15ml Soy Sauce
    quantity_unit_name_match = re.search(rf"^(?P<quantity_unit_name>{quantity_regex})\s*(?P<unit_unit_name>(?:g|kg|ml|l|tsp|tbsp|cup|oz|lb|pinch|dash|pcs|pot of|pots of)\b)\s*(?P<name_unit_name>.*)$", ingredient_str)
    if quantity_unit_name_match:
        quantity_str = quantity_unit_name_match.group("quantity_unit_name")
        quantity = float(quantity_str) if "." in quantity_str or quantity_str.isdigit() else parse_fraction(quantity_str)
        return quantity_unit_name_match.group("name_unit_name").strip(), str(quantity), quantity_unit_name_match.group("unit_unit_name")

    # Case 5: Quantity Name
    # E.g. 2 Onion
    quantity_name_match = re.search(rf"^(?P<quantity_name>{quantity_regex})\s*(?P<name_name>.*)$", ingredient_str)
    if quantity_name_match:
        quantity_str = quantity_name_match.group("quantity_name")
        quantity = float(quantity_str) if "." in quantity_str or quantity_str.isdigit() else parse_fraction(quantity_str)
        return quantity_name_match.group("name_name").strip(), str(quantity), None

    # Case 6: Name Only
    # E.g. Onion
    return ingredient_str, None, None


def insert_recipe_data(recipe_data, db_path=DB_PATH):
    """
    Inserts the recipe information into the database. A no-op if this recipe's
    URL has already been scraped, so re-running the scraper (e.g. with a
    higher page count, which includes all earlier recipes too) is safe.

    :param recipe_data: Dictionary of recipe data
    :param db_path: Path to .sqlite database file in string format
    :returns: None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT recipe_id FROM recipes WHERE instructions_url = ?", (recipe_data['url'],))
    if cursor.fetchone():
        conn.close()
        return

    # Insert into the recipes table
    cursor.execute("INSERT INTO recipes (title, instructions_url) VALUES (?, ?)",
                   (recipe_data['title'], recipe_data['url']))
    recipe_id = cursor.lastrowid  # Get the newly inserted recipe ID

    for line in recipe_data['ingredients']:
        ingredient_name, quantity, unit = parse_ingredient(line)
        ingredient_name = ingredient_name.lower()
        # Check if the ingredient already exists
        cursor.execute("SELECT ingredient_id FROM ingredients WHERE ingredient_name = ?", (ingredient_name,))
        existing_ingredient = cursor.fetchone()

        if existing_ingredient:
            ingredient_id = existing_ingredient[0]
        else:
            # Insert the new ingredient
            cursor.execute("INSERT INTO ingredients (ingredient_name) VALUES (?)", (ingredient_name,))
            ingredient_id = cursor.lastrowid

        # Insert into the recipe_ingredients table
        cursor.execute("INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
                       (recipe_id, ingredient_id, quantity, unit))

    conn.commit()
    conn.close()


def get_recipe_urls_from_category(category_url, driver):
    """
    Returns a list of urls found on a target Gousto category page

    :param category_url: str
    :param driver: an active Selenium WebDriver
    :return: list of urls
    """

    driver.get(category_url)
    time.sleep(2)  # allow page to load.

    try:
        # See the note in scrape_gousto_recipe: match on the stable prefix of
        # the CSS-module class, not its build hash suffix, so this selector
        # survives Gousto frontend rebuilds.
        target_division = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='PageSection_verticalPaddingSmallMediumLarge__']"))
        )
        # Find recipe links within the division
        recipe_links = target_division.find_elements(By.CSS_SELECTOR, "a[href*='/cookbook/']")
        return [link.get_attribute("href") for link in recipe_links]

    except Exception as e:
        # Requesting a page beyond Gousto's current maximum returns a "page
        # not found" page rather than clamping to the last valid page, which
        # looks like this same timeout since the section we wait for is
        # absent there too.
        print(f"No recipes found at {category_url} ({e}). "
              f"This page may not exist, or the site's markup may have changed.")
        return []


def scrape_all_gousto_recipes(category_url, driver):
    """
    Scrapes a supplied list of Gousto recipe page urls for recipe data

    :param category_url: str
    :param driver: an active Selenium WebDriver
    :return: list of recipe datas
    """
    visited_urls = set()
    all_recipe_data = []

    recipe_urls = get_recipe_urls_from_category(category_url, driver)
    for recipe_url in recipe_urls:
        if recipe_url not in visited_urls:
            visited_urls.add(recipe_url)
            recipe_data = scrape_gousto_recipe(recipe_url, driver)
            if recipe_data:
                all_recipe_data.append(recipe_data)
            time.sleep(1)  # Rate limiting.
    return all_recipe_data


def get_url():
    """
    Builds the Gousto cookbook URL for the requested page.

    Gousto's `?page=N` parameter is cumulative: page N returns all recipes
    from page 1 through N (not just page N's own 16), and the site exposes no
    "last page" indicator to validate against. So rather than hardcoding a
    maximum that will inevitably go stale as Gousto adds recipes, any
    non-negative page number is accepted; requesting one beyond the site's
    current maximum returns a "page not found" page, which the scraper
    detects and reports rather than crashing on (see
    get_recipe_urls_from_category).

    :return: str
    """
    print("Enter number of pages to scrape. Each page contains 16 recipes, "
          "and includes all recipes from earlier pages too. "
          "Enter '0' to scrape only the first 16 recipes.")

    while True:
        raw_input_value = input("> ").strip()
        if raw_input_value.isdigit():
            num_pages = int(raw_input_value)
            break
        print("Please enter a whole number (0 or greater).")

    if num_pages == 0:
        return CATEGORY_URL
    return f'{CATEGORY_URL}?page={num_pages}'


def main():
    init_db()
    category_url = get_url()
    driver = build_driver()
    try:
        all_recipe_data = scrape_all_gousto_recipes(category_url, driver)
    finally:
        driver.quit()

    for recipe in all_recipe_data:
        if recipe['ingredients']:
            insert_recipe_data(recipe)


if __name__ == "__main__":
    main()