# Imports
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import sqlite3
import time

service = Service(executable_path='chromedriver-win64/chromedriver.exe')  # Replace with your chromedriver path.
driver = webdriver.Chrome(service=service)


def scrape_gousto_recipe(url):
    """
    Scrapes recipe information from a Gousto recipe webpage.

    :param url: str
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
        ingredients_elements = driver.find_elements(By.CSS_SELECTOR, "ul.IngredientList_ingredientList__14UI0 li")
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


def insert_recipe_data(recipe_data, db_path):
    """
    Inserts the recipe information into the database.

    :param recipe_data: Dictionary of recipe data
    :param db_path: Path to .sqlite database file in string format
    :returns: None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    # Insert into the recipes table
    cursor.execute("INSERT INTO recipes (title, instructions_url) VALUES (?, ?)",
                   (recipe_data['title'], recipe_data['url']))
    # cursor.execute("INSERT INTO recipes (title, instructions_url) VALUES (?, ?)",
    # (recipe_data['title'], recipe_data['url'],))
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


def get_recipe_urls_from_category(category_url):
    """
    Returns a list of urls found on a target Gousto category page

    :param category_url: str
    :return: list of urls
    """

    driver.get(category_url)
    time.sleep(2)  # allow page to load.

    try:
        target_division = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".PageSection_verticalPaddingSmallMediumLarge__2sHrM"))
        )
        # Find recipe links within the division
        recipe_links = target_division.find_elements(By.CSS_SELECTOR, "a[href*='/cookbook/']")
        urls = []
        for link in recipe_links:
            urls.append(link.get_attribute("href"))
        return urls

    except Exception as e:
        print(f"Error scraping {category_url}: {e}")
        return []


def scrape_all_gousto_recipes(category_url):
    """
    Scrapes a supplied list of Gousto recipe page urls for recipe data

    :param category_url: str
    :return: list of recipe datas
    """
    visited_urls = set()
    all_recipe_data = []

    recipe_urls = get_recipe_urls_from_category(category_url)
    for recipe_url in recipe_urls:
        if recipe_url not in visited_urls:
            visited_urls.add(recipe_url)
            recipe_data = scrape_gousto_recipe(recipe_url)  # Your existing scrape function.
            if recipe_data:
                all_recipe_data.append(recipe_data)
            time.sleep(1)  # Rate limiting.
    return all_recipe_data


def get_url():
    """Gets url corresponding to number of pages wanted."""

    category_url = 'https://www.gousto.co.uk/cookbook/recipes'

    print("Enter number of pages to scrape. Each page contains 16 recipes."
          "Enter '0' to scrape only the first 16 recipes."
          "Maximum page number is 353")
    num_pages = int(input())
    while num_pages < 0 or num_pages > 353:
        print("Invalid number. Must be in range 0 <= n <= 353")
        num_pages = int(input())
    if num_pages == 0:
        return category_url
    else:
        return f'{category_url}?page={num_pages}'


def main():
    category_url = get_url()
    try:
        all_recipe_data = scrape_all_gousto_recipes(category_url)
        # store all_recipe_data into the database.
    finally:
        driver.quit()
    for i in all_recipe_data:
        if i['ingredients']:
            insert_recipe_data(i, 'recipes.sqlite')


if __name__ == "__main__":
    main()
