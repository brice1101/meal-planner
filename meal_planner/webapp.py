"""Flask web app for searching recipes by ingredients you already have."""

from flask import Flask, abort, jsonify, render_template, request

from meal_planner import db


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", all_ingredients=db.get_all_ingredients())

    @app.get("/api/search")
    def search():
        ingredients = request.args.getlist("ingredient")
        match_all = request.args.get("match_all") == "true"
        results = db.get_recipe_by_ingredients(ingredients, match_all)
        return jsonify(results=results)

    @app.get("/recipe/<int:recipe_id>")
    def recipe_detail(recipe_id):
        recipe = db.get_recipe_detail(recipe_id)
        if recipe is None:
            abort(404)
        return render_template("recipe_detail.html", recipe=recipe)

    return app


app = create_app()


def main():
    db.init_db()
    app.run(debug=True)


if __name__ == "__main__":
    main()
