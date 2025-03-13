import sqlite3
import tkinter as tk
from tkinter import scrolledtext


def get_recipe_by_ingredients(ingredients_list, all_ingredients):
    """Retrieves recipes from the database based on a list of ingredients."""
    conn = sqlite3.connect('recipes.sqlite')
    cursor = conn.cursor()

    placeholders = ', '.join(['?'] * len(ingredients_list))

    if all_ingredients:
        query = f"""
        SELECT r.title, r.instructions_url
        FROM recipes r
        JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
        JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
        WHERE i.ingredient_name IN ({placeholders})
        GROUP BY r.recipe_id
        HAVING COUNT(DISTINCT i.ingredient_id) = ?"""
        cursor.execute(query, ingredients_list + [len(ingredients_list)])

    else:
        query = f"""
            SELECT DISTINCT r.title, r.instructions_url
            FROM recipes r
            JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
            JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
            WHERE i.ingredient_name IN ({placeholders})"""
        cursor.execute(query, ingredients_list)

    results = cursor.fetchall()
    conn.close()
    return results


def search_recipes():
    ingredients_input = ingredients_entry.get()
    ingredients = [ing.strip() for ing in ingredients_input.split(',')]
    all_ingredients = all_ingredients_var.get()

    print(f"Checkbox state: {all_ingredients}")

    results = get_recipe_by_ingredients(ingredients, all_ingredients)

    results_text.delete(1.0, tk.END)
    if results:
        for title, url in results:
            results_text.insert(tk.END, f"Recipe: {title}\nURL: {url}\n\n")
    else:
        results_text.insert(tk.END, "No recipes found")


window = tk.Tk()
window.title("Recipe Finder")

ingredients_label = tk.Label(window, text="Enter ingredients (comma-separated):")
ingredients_label.pack()
ingredients_entry = tk.Entry(window, width=50)
ingredients_entry.pack()

all_ingredients_var = tk.BooleanVar()
all_ingredients_checkbox = tk.Checkbutton(window, text="Must have all ingredients", variable=all_ingredients_var)
all_ingredients_checkbox.pack()

search_button = tk.Button(window, text="Search", command=search_recipes)
search_button.pack()

results_text = scrolledtext.ScrolledText(window, width=60, height=20)
results_text.pack()

window.mainloop()
