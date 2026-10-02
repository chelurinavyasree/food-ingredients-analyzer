import re
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

MAX_INGREDIENT_LENGTH = 12_000
MAX_PRODUCT_NAME_LENGTH = 120
OPEN_FOOD_FACTS_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

INGREDIENT_RULES: list[dict[str, Any]] = [
    {"terms": ("milk", "whey", "casein", "butter", "cream", "cheese", "lactose"), "kind": "alert", "tag": "ALLERGEN", "title": "Milk-derived ingredient", "detail": "Milk and its derivatives are common allergens. Check the package's allergen statement."},
    {"terms": ("peanut", "groundnut"), "kind": "alert", "tag": "ALLERGEN", "title": "Peanut", "detail": "Peanuts are a major food allergen and can cause serious reactions."},
    {"terms": ("almond", "cashew", "walnut", "pistachio", "pecan", "hazelnut", "macadamia", "tree nut"), "kind": "alert", "tag": "ALLERGEN", "title": "Tree nut", "detail": "Tree nuts are a major food allergen. The specific nut may matter for your needs."},
    {"terms": ("wheat", "barley", "rye", "malt", "spelt"), "kind": "alert", "tag": "ALLERGEN", "title": "Gluten-containing grain", "detail": "This ingredient may contain gluten. Check suitability for your dietary needs."},
    {"terms": ("soy", "soya", "soybean"), "kind": "alert", "tag": "ALLERGEN", "title": "Soy", "detail": "Soy is a major food allergen. Look for a matching allergen declaration."},
    {"terms": ("sesame", "tahini"), "kind": "alert", "tag": "ALLERGEN", "title": "Sesame", "detail": "Sesame is a major food allergen and may appear under several ingredient names."},
    {"terms": ("egg", "eggs", "albumin", "mayonnaise"), "kind": "alert", "tag": "ALLERGEN", "title": "Egg-derived ingredient", "detail": "Egg and its derivatives are common allergens. Check the package's allergen statement."},
    {"terms": ("fish", "anchovy", "salmon", "tuna", "cod"), "kind": "alert", "tag": "ALLERGEN", "title": "Fish", "detail": "A fish ingredient is listed. The species may be specified elsewhere on the package."},
    {"terms": ("shellfish", "shrimp", "crab", "lobster", "prawn", "oyster"), "kind": "alert", "tag": "ALLERGEN", "title": "Shellfish", "detail": "A shellfish ingredient may be present. Check the package for its allergen declaration."},
    {"terms": ("aspartame", "sucralose", "acesulfame potassium", "acesulfame-k"), "kind": "caution", "tag": "SWEETENER", "title": "High-intensity sweetener", "detail": "A non-sugar sweetener is listed. Check the label if you prefer to avoid these."},
    {"terms": ("high fructose corn syrup", "corn syrup", "glucose syrup", "invert sugar"), "kind": "caution", "tag": "SWEETENER", "title": "Added syrup or sugar", "detail": "A concentrated sweetener is listed. The nutrition panel shows total sugars per serving."},
    {"terms": ("sodium nitrite", "sodium nitrate", "potassium nitrite"), "kind": "caution", "tag": "PRESERVATIVE", "title": "Curing preservative", "detail": "Nitrite or nitrate preservatives are commonly used in cured meats."},
    {"terms": ("bha", "bht", "tbhq"), "kind": "caution", "tag": "PRESERVATIVE", "title": "Synthetic antioxidant", "detail": "This antioxidant helps preserve freshness. Regulations and permitted uses vary by region."},
    {"terms": ("monosodium glutamate", "msg", "disodium inosinate", "disodium guanylate"), "kind": "caution", "tag": "FLAVOR", "title": "Flavor enhancer", "detail": "A flavor-enhancing ingredient is listed. Sensitivity varies from person to person."},
    {"terms": ("red 40", "yellow 5", "yellow 6", "blue 1", "color 40", "tartrazine"), "kind": "caution", "tag": "COLOR", "title": "Certified food color", "detail": "An added color is listed. Names and labeling requirements vary by country."},
    {"terms": ("maltodextrin",), "kind": "caution", "tag": "ADDITIVE", "title": "Maltodextrin", "detail": "A processed carbohydrate often used for texture or as a carrier. It can affect blood sugar."},
    {"terms": ("palm oil", "palm kernel oil"), "kind": "caution", "tag": "OIL", "title": "Palm-derived oil", "detail": "Palm oil is used for texture and stability. Consider your dietary and sourcing preferences."},
    {"terms": ("natural flavors", "artificial flavors"), "kind": "note", "tag": "LABEL NOTE", "title": "Flavoring listed", "detail": "The flavor source isn't detailed here. Contact the manufacturer if you need specifics."},
    {"terms": ("tocopherols", "citric acid", "rosemary extract", "ascorbic acid"), "kind": "note", "tag": "PRESERVATIVE", "title": "Freshness aid", "detail": "This ingredient is commonly used to help maintain freshness."},
]


def split_ingredients(value: str) -> list[str]:
    return [part.strip().strip("()").strip() for part in re.split(r"[,;\n]+", value) if part.strip().strip("() ")]


def contains_term(ingredient: str, term: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    return re.search(pattern, ingredient, flags=re.IGNORECASE) is not None


def analyze_ingredients(ingredients: list[str]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for rule in INGREDIENT_RULES:
        match = next(
            (ingredient for ingredient in ingredients if any(contains_term(ingredient, term) for term in rule["terms"])),
            None,
        )
        if match is not None:
            findings.append({
                "kind": rule["kind"],
                "tag": rule["tag"],
                "title": rule["title"],
                "detail": rule["detail"],
                "match": match,
            })

    allergen_count = sum(item["kind"] == "alert" for item in findings)
    caution_count = sum(item["kind"] == "caution" for item in findings)
    note_count = sum(item["kind"] == "note" for item in findings)
    score = max(38, min(98, 94 - allergen_count * 12 - caution_count * 6 - note_count * 2))
    if score >= 85:
        headline, summary = "A simpler list", "No major flags found in our quick scan."
    elif score >= 65:
        headline, summary = "A few callouts", "A couple of ingredients may be worth a closer look."
    else:
        headline, summary = "Take a closer look", "Several items here may need your attention."

    return {
        "ingredient_count": len(ingredients),
        "allergen_count": allergen_count,
        "caution_count": caution_count,
        "nutrition_grade": "",
        "nutrition_summary": "Search for a packaged product to see its Nutri-Score, if available.",
        "safety_status": "Check before eating" if allergen_count else "No common allergen flags found",
        "safety_message": (
            "This list matched common allergen flags. Whether the food is dangerous depends on your allergies; check the full package label."
            if allergen_count else
            "This quick scan found no common allergen flags. It cannot guarantee the food is safe for you; check the package and your dietary needs."
        ),
        "score": score,
        "headline": headline,
        "summary": summary,
        "findings": findings,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Send a JSON object with an ingredients field."), 400

    raw_ingredients = data.get("ingredients", "")
    if not isinstance(raw_ingredients, str):
        return jsonify(error="Ingredients must be text."), 400
    if len(raw_ingredients) > MAX_INGREDIENT_LENGTH:
        return jsonify(error=f"Ingredients must be {MAX_INGREDIENT_LENGTH} characters or fewer."), 413

    ingredients = split_ingredients(raw_ingredients)
    if not ingredients:
        return jsonify(error="Add an ingredients list to continue."), 400

    product_name = data.get("product_name", "")
    if not isinstance(product_name, str):
        return jsonify(error="Product name must be text."), 400
    product_name = product_name.strip()
    if len(product_name) > MAX_PRODUCT_NAME_LENGTH:
        return jsonify(error=f"Product name must be {MAX_PRODUCT_NAME_LENGTH} characters or fewer."), 400

    nutrition_grade = data.get("nutrition_grade", "")
    if not isinstance(nutrition_grade, str) or nutrition_grade.lower() not in {"a", "b", "c", "d", "e"}:
        nutrition_grade = ""
    nutrition_grade = nutrition_grade.lower()
    nutrition_summaries = {
        "a": "Higher nutritional quality according to Nutri-Score.",
        "b": "Good nutritional quality according to Nutri-Score.",
        "c": "Mid-range nutritional quality according to Nutri-Score.",
        "d": "Lower nutritional quality according to Nutri-Score.",
        "e": "Lower nutritional quality according to Nutri-Score.",
    }
    analysis = analyze_ingredients(ingredients)
    analysis["nutrition_grade"] = nutrition_grade
    analysis["nutrition_summary"] = nutrition_summaries.get(
        nutrition_grade,
        "No Nutri-Score was available for this product. The ingredient scan alone cannot tell whether it is healthy overall.",
    )
    return jsonify(product_name=product_name, **analysis)


@app.get("/api/search-products")
def search_products():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify(error="Enter at least 2 characters to search."), 400
    if len(query) > MAX_PRODUCT_NAME_LENGTH:
        return jsonify(error=f"Search must be {MAX_PRODUCT_NAME_LENGTH} characters or fewer."), 400

    params = urlencode({
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 8,
        "fields": "code,product_name,brands,ingredients_text,countries,nutrition_grades,nutrition_grade_fr,nutriscore_grade",
    })
    api_request = Request(
        f"{OPEN_FOOD_FACTS_SEARCH_URL}?{params}",
        headers={"User-Agent": "GoodlistFoodIngredientAnalyzer/1.0 (local app)"},
    )
    try:
        with urlopen(api_request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return jsonify(error="Product search is temporarily unavailable. You can still paste the package ingredients below."), 502

    products = []
    for product in payload.get("products", []):
        name = product.get("product_name", "").strip()
        ingredients = product.get("ingredients_text", "").strip()
        if not name or not ingredients:
            continue
        nutrition_grade = str(
            product.get("nutrition_grades")
            or product.get("nutrition_grade_fr")
            or product.get("nutriscore_grade")
            or ""
        ).split(",")[0].strip().lower()
        code = str(product.get("code", ""))
        products.append({
            "name": name,
            "brands": product.get("brands", "").strip(),
            "ingredients": ingredients,
            "countries": product.get("countries", "").strip(),
            "nutrition_grade": nutrition_grade if nutrition_grade in {"a", "b", "c", "d", "e"} else "",
            "url": f"https://world.openfoodfacts.org/product/{code}" if code.isdigit() else "",
        })

    return jsonify(products=products, source="Open Food Facts")


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="The request is too large."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
