# Smart Meal Planner

[![Tests](https://github.com/brice1101/meal-planner/actions/workflows/tests.yml/badge.svg)](https://github.com/brice1101/meal-planner/actions/workflows/tests.yml)

A meal-planning assistant that helps reduce food waste: it scrapes recipes from [Gousto](https://www.gousto.co.uk/) into a local database, then lets you search for recipes you can make from ingredients you already have.

<!-- Add a screenshot or GIF of the search page here, e.g.: -->
<!-- ![Meal Planner search page](docs/screenshot.png) -->

## How it works

```
gousto.co.uk  →  scraper (Selenium)  →  SQLite  →  Flask web app
```

- **`meal_planner/scraper.py`** crawls Gousto's recipe pages with Selenium, parses each recipe's title, URL, and ingredient list, and stores them in a local SQLite database. Ingredient names are normalized as they're inserted (e.g. "garlic", "minced garlic", and "garlic clove" all become "garlic") so near-duplicates don't pile up.
- **`meal_planner/db.py`** is the shared data layer: schema creation and the read queries used by the web app.
- **`meal_planner/webapp.py`** is a small Flask app: pick the ingredients you have, choose whether a recipe must contain all of them or just any one, and get a list of matching recipes with a link back to the original Gousto page.

## Setup

Requires Python 3.11+. Scraping additionally requires a local install of Chrome or Chromium (Selenium's built-in Selenium Manager downloads the matching driver automatically — no manual driver setup needed).

```bash
git clone https://github.com/brice1101/meal-planner.git
cd meal-planner
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

The database (`recipes.sqlite`) isn't included in the repo, since it's scraped third-party content — you generate your own by running the scraper.

### Quick start (get a working demo in under a minute)

```bash
meal-planner-scrape
# When prompted for a page number, enter 0 to scrape just the first 16 recipes.

meal-planner-serve
# Visit http://127.0.0.1:5000
```

### Scraping more recipes

Run `meal-planner-scrape` again and enter a higher page number — Gousto's `?page=N` listing is cumulative (page N includes all recipes from page 1 through N), and re-scraping is safe: recipes and ingredients you already have are skipped rather than duplicated.

If you're topping up a database that was scraped before ingredient normalization existed, `meal-planner-scrape --dedupe` re-normalizes and merges any existing near-duplicate ingredients.

## Development

```bash
pytest
```

Tests cover the ingredient-line parser, ingredient normalization, the database layer, and the web app's routes, all against temporary throwaway databases — nothing here touches `recipes.sqlite`. CI runs the same suite on every push via GitHub Actions.

## A note on scraping

This project scrapes a commercial site's recipe pages for personal, non-commercial use. If you fork or extend this, be mindful of Gousto's terms of service and rate limits (the scraper already waits between requests) — this isn't intended for redistributing Gousto's content or for large-scale/commercial scraping.

## License

MIT — see [LICENSE](LICENSE).
