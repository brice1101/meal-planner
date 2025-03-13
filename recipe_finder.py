import sqlite3
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext


def get_all_ingredients():
    """Retrieves all ingredient names from the database."""
    conn = sqlite3.connect('recipes.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_name FROM ingredients")
    ingredients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ingredients

def update_ingredient_list(event):
    """Updates the dropdown list based on the user's input."""
    typed_text = ingredient_combobox.get().lower()
    filtered_ingredients = [ing for ing in all_ingredients if typed_text in ing.lower()]
    ingredient_combobox['values'] = filtered_ingredients

def add_ingredient():
    """Adds the selected ingredient to the ingredients list."""
    selected_ingredient = ingredient_combobox.get()
    if selected_ingredient and selected_ingredient not in ingredients_list_text.get("1.0", tk.END):
        ingredients_list_text.insert(tk.END, selected_ingredient + ", ")
        ingredient_combobox.set("") #clear combobox after selection
        ingredient_combobox.focus_set() #put cursor back in combobox.


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
    ingredients_input = ingredients_list_text.get("1.0", tk.END)
    ingredients = [ing.strip() for ing in ingredients_input.split(',') if ing.strip()]
    all_ingredients = all_ingredients_var.get()

    results = get_recipe_by_ingredients(ingredients, all_ingredients)

    results_text.delete(1.0, tk.END)
    if results:
        for title, url in results:
            results_text.insert(tk.END, f"Recipe: {title}\nURL: {url}\n\n")
    else:
        results_text.insert(tk.END, "No recipes found.")

# Create the main window
window = tk.Tk()
window.title("Recipe Finder")

# Ingredient input
ingredient_label = tk.Label(window, text="Enter ingredients:")
ingredient_label.pack()

# Combobox for auto-complete
all_ingredients = get_all_ingredients()
ingredient_combobox = ttk.Combobox(window, values=all_ingredients)
ingredient_combobox.pack()

# Entry field for typing
ingredient_combobox.bind("<KeyRelease>", update_ingredient_list)

#add button
add_button = tk.Button(window, text="Add", command=add_ingredient)
add_button.pack()

# Ingredient list display
ingredients_list_text = scrolledtext.ScrolledText(window, height=3, width=50)
ingredients_list_text.pack()

# All ingredients checkbox
all_ingredients_var = tk.BooleanVar()
all_ingredients_checkbox = tk.Checkbutton(window, text="Must have all ingredients", variable=all_ingredients_var)
all_ingredients_checkbox.pack()

# Search button
search_button = tk.Button(window, text="Search", command=search_recipes)
search_button.pack()

# Results display
results_text = scrolledtext.ScrolledText(window, width=60, height=20)
results_text.pack()

window.mainloop()
