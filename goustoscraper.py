# Imports
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import sqlite3
import time


def scrape_gousto_recipe(url, driver):
    """
    Scrapes recipe information from a Gousto recipe webpage.

    This function uses Selenium to navigate to the provided URL, waits for the page to load,
    and extracts the recipe title, ingredients, and instructions. It handles potential errors
    during the scraping process and returns a dictionary containing the extracted data.

    Args:
        url (str): The URL of the Gousto recipe webpage.
        driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.

    Returns:
        dict: A dictionary containing the scraped recipe data, including:
            - 'title' (str): The recipe title.
            - 'ingredients' (str): A newline-separated string of ingredients.
            - 'url' (str): The URL of the scraped recipe.
        None: If an error occurs during scraping.
    """

    try:
        driver.get(url)

        # Wait for the main recipe title to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )

        # Get heading of page, corresponding to recipe title
        title = driver.find_element(By.TAG_NAME, "h1").text.strip() if driver.find_elements(By.TAG_NAME, "h1") else "Title not found"

        # Get the list of ingredients
        ingredients_list = []
        ingredients_elements = driver.find_elements(By.CSS_SELECTOR, "ul.IngredientList_ingredientList__14UI0 li")
        for ingredient in ingredients_elements:
            ingredients_list.append(ingredient.text.strip())
        ingredients = "\n".join(ingredients_list)

        # Return a dictionary with necessary information
        return {
            'title': title,
            'ingredients': ingredients,
            'url': url
        }

    # Handle exceptions during scraping by returning None instead
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def parse_ingredient(ingredient_line):
    """
    Parses an ingredient line to extract the ingredient name, quantity, and unit.

    This function uses a regular expression to parse ingredient lines that may contain
    quantity, unit, and multiple values within parentheses or preceded by "x".
    It handles various formats and returns a tuple containing the parsed information.

    Args:
        ingredient_line (str): The ingredient line to parse.

    Returns:
        tuple: A tuple containing (name, quantity, unit), where:
            - name (str): The name of the ingredient.
            - quantity (float or int or None): The quantity of the ingredient (if specified), or None.
            - unit (str or None): The unit of the ingredient (if specified), or None.

    Examples:
        >>> parse_ingredient("Chicken breast (200g)")
        ('Chicken breast', 200.0, 'g')
        >>> parse_ingredient("Onion x2")
        ('Onion', 2.0, None)
        >>> parse_ingredient("Salt")
        ('Salt', None, None)
        >>> parse_ingredient("Chopped tomatoes (400) x 2")
        ('Chopped tomatoes', 800.0, None)
    """
    ingredient_line.replace('†','') # Remove allergen marker from ingredients where needed
    pattern = r"^(.*?)(?:\s*\(([\d\.]+)\s*([a-zA-Z]*)\))?(?:\s*x(\d+))?\.?$"
    match = re.match(pattern, ingredient_line.strip())

    if match:
        name = match.group(1).strip()
        quantity = match.group(2)
        unit = match.group(3)
        multiple = match.group(4)

        if multiple:
            if quantity:
                quantity = float(quantity) * int(multiple)
            else:
                quantity = int(multiple)

        if quantity:
            return (name, float(quantity), unit) if unit else (name, float(quantity), None)
        else:
            return (name, None, None)
    else:
        return (ingredient_line.strip(), None, None)


def insert_recipe_data(recipe_data, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(tables)
    # Insert into the recipes table
    cursor.execute("INSERT INTO recipes (title) VALUES (?)",
                   (recipe_data['title'],))
    # cursor.execute("INSERT INTO recipes (title, instructions_url) VALUES (?, ?)",
    # (recipe_data['title'], recipe_data['url'],))
    recipe_id = cursor.lastrowid  # Get the newly inserted recipe ID

    for line in recipe_data['ingredients'].split('\n'):
        ingredient_name, quantity, unit = parse_ingredient(line)
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

    # Insert ingredients and link them to the recipe
    #    for ingredient_name, quantity, unit in recipe_data['ingredients']:
    # Check if the ingredient already exists
    #        cursor.execute("SELECT ingredient_id FROM ingredients WHERE ingredient_name = ?", (ingredient_name,))
    #        existing_ingredient = cursor.fetchone()

    #        if existing_ingredient:
    #            ingredient_id = existing_ingredient[0]
    #        else:
    #            # Insert the new ingredient
    #            cursor.execute("INSERT INTO ingredients (ingredient_name) VALUES (?)", (ingredient_name,))
    #            ingredient_id = cursor.lastrowid

    # Insert into the recipe_ingredients table
    #        cursor.execute("INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
    #                       (recipe_id, ingredient_id, quantity, unit))

    conn.commit()
    conn.close()


def get_recipe_urls_from_category(category_url, driver):
    driver.get(category_url)
    time.sleep(2) #allow page to load.

    recipe_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/cookbook/']") #find all links containing cookbook
    urls = []
    for link in recipe_links:
        urls.append(link.get_attribute("href"))
    return urls


def scrape_all_gousto_recipes(category_urls, driver):
    visited_urls = set()
    all_recipe_data = []

    for category_url in category_urls:
        recipe_urls = get_recipe_urls_from_category(category_url, driver)
        for recipe_url in recipe_urls:
            if recipe_url not in visited_urls:
                visited_urls.add(recipe_url)
                recipe_data = scrape_gousto_recipe(recipe_url, driver) #your existing scrape function.
                if recipe_data:
                    all_recipe_data.append(recipe_data)
                time.sleep(1) #rate limiting.
    return all_recipe_data


def main():
    service = Service(executable_path='chromedriver-win64/chromedriver.exe')  # Replace with your chromedriver path.
    driver = webdriver.Chrome(service=service)
    category_url = ['https://www.gousto.co.uk/cookbook/recipes?page=352']
    driver.quit()

    service = Service(executable_path='chromedriver-win64/chromedriver.exe')  # Replace with your chromedriver path.
    driver = webdriver.Chrome(service=service)
    try:
        all_recipe_data = scrape_all_gousto_recipes(category_url, driver)
        # store all_recipe_data into the database.
    finally:
        driver.quit()
    for i in all_recipe_data:
        if i['ingredients']:
            insert_recipe_data(i, 'C:/Users/brxce/Documents/Python Projects/mealplanner/recipes.sqlite')

main()