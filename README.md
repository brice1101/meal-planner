# Smart Meal Planner
A Python-based meal planning assistant that helps reduce food waste and simplify weekly meal prep. It scrapes recipes from the ![Gousto](https://www.gousto.co.uk/) website, stores them in a database, and provides recipe suggestions based on your leftover ingredients via a simple Tkinter GUI.

## Features

- **Web Scraper** - Automatically collects recipes and ingredients from Gousto's recipe pages.
- **Ingredient Database** - Recipes and their required ingredients are stored locally for quick lookups.

**Tech used:** Python, SQLite

## TO DO
- **Clean up duplicates from database**: the web scraper collates all unique text as a new ingredient. Recipes often use slightly different names for the same ingredient (e.g., garlic/minced garlic/diced garlic/garlic clove). Duplicates are being removed manually when encountered during personal use. 
