# Goodlist Food Ingredient Analyzer

A small Flask application with an HTML, CSS, and JavaScript frontend. Search for packaged foods by name using the Open Food Facts community database, choose a matching product, and review its listed ingredients, common allergen flags, and Nutri-Score when available. You can also paste an ingredient list from a package. Product search requires an internet connection; manual ingredient analysis works locally. The Nutri-Score summarizes nutritional quality, but it is not a complete judgment of whether a food is healthy for a specific person. Results are informational, are not medical advice, and cannot determine that a food is safe for a particular person.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## API

`POST /api/analyze` accepts JSON with an `ingredients` string, an optional `product_name` string, and an optional `nutrition_grade` (`a` through `e`). It returns an ingredient scan, an allergen summary, and nutrition quality information when a grade is provided. Ingredient lists are processed per request and are not saved.

`GET /api/search-products?q=...` searches Open Food Facts for products that have a listed ingredients field. The database is community contributed, so check the package for current and exact ingredient information.
