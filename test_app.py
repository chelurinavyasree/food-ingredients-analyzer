import unittest

from app import app


class IngredientAnalyzerTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_home_page_uses_flask_template(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Read a food label", response.data)
        self.assertIn(b"/static/app.js", response.data)

    def test_analyze_reports_common_allergens_and_additives(self):
        response = self.client.post(
            "/api/analyze",
            json={
                "product_name": "Test crackers",
                "ingredients": "Wheat flour, peanut butter, maltodextrin",
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["product_name"], "Test crackers")
        self.assertEqual(result["ingredient_count"], 3)
        self.assertEqual(result["allergen_count"], 2)
        self.assertEqual(result["caution_count"], 1)
        self.assertEqual(len(result["findings"]), 3)

    def test_analyze_rejects_empty_ingredients(self):
        response = self.client.post("/api/analyze", json={"ingredients": " , ; "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_analyze_rejects_non_text_ingredients(self):
        response = self.client.post("/api/analyze", json={"ingredients": ["milk"]})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
