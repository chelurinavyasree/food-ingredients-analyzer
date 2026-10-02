const sampleIngredients = "Whole grain wheat flour, sunflower oil, cane sugar, maltodextrin, sea salt, natural flavors, soy lecithin, tocopherols";
const form = document.querySelector("#analyzer-form");
const ingredientField = document.querySelector("#ingredients");
const productField = document.querySelector("#product-name");
const analyzeButton = document.querySelector("#analyze-button");
const searchButton = document.querySelector("#search-button");
const productSearchResults = document.querySelector("#product-search-results");
const results = document.querySelector("#results-content");
let selectedNutritionGrade = "";

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderAnalysis(data) {
  const resultsTop = makeElement("div", "results-top");
  const resultTitle = makeElement("div", "result-title");
  resultTitle.append(makeElement("h2", "", "Food overview"));
  const label = makeElement("span", "analyzed-label", data.product_name || "Your ingredient list");
  label.title = label.textContent;
  resultTitle.append(label);
  resultsTop.append(resultTitle);

  const verdict = makeElement("div", `safety-verdict ${data.allergen_count ? "has-flags" : "no-flags"}`);
  verdict.append(makeElement("span", "verdict-label", "Ingredient and allergen check"));
  verdict.append(makeElement("strong", "", data.safety_status));
  verdict.append(makeElement("span", "", data.safety_message));
  resultsTop.append(verdict);

  const nutrition = makeElement("div", "nutrition-verdict");
  const nutritionHeading = makeElement("div", "nutrition-heading");
  nutritionHeading.append(makeElement("strong", "", "Overall nutrition"));
  if (data.nutrition_grade) {
    nutritionHeading.append(makeElement("span", `nutrition-grade grade-${data.nutrition_grade}`, `Nutri-Score ${data.nutrition_grade.toUpperCase()}`));
  } else {
    nutritionHeading.append(makeElement("span", "nutrition-grade grade-unknown", "No score"));
  }
  nutrition.append(nutritionHeading, makeElement("span", "nutrition-summary", data.nutrition_summary));
  const nutritionLink = makeElement("a", "nutrition-link", "How Nutri-Score works");
  nutritionLink.href = "https://world.openfoodfacts.org/nutriscore";
  nutritionLink.target = "_blank";
  nutritionLink.rel = "noopener noreferrer";
  nutrition.append(nutritionLink);
  resultsTop.append(nutrition);

  const stats = makeElement("div", "stats");
  const statItems = [
    [data.ingredient_count, "ingredients", ""],
    [data.allergen_count, "allergen flags", data.allergen_count ? "alert" : ""],
    [data.caution_count, "things to review", data.caution_count ? "caution" : ""],
  ];
  for (const [value, labelText, className] of statItems) {
    const stat = makeElement("div", `stat ${className}`.trim());
    stat.append(makeElement("strong", "", String(value)));
    stat.append(makeElement("span", "", labelText));
    stats.append(stat);
  }
  resultsTop.append(stats);

  const findings = makeElement("div", "findings");
  const findingsHead = makeElement("div", "findings-head");
  findingsHead.append(makeElement("h3", "", "What stood out"));
  findingsHead.append(makeElement("span", "", `${data.findings.length} ${data.findings.length === 1 ? "finding" : "findings"}`));
  findings.append(findingsHead);

  const findingList = makeElement("div", "finding-list");
  if (data.findings.length) {
    for (const item of data.findings) {
      const finding = makeElement("article", `finding ${item.kind === "note" ? "" : item.kind}`.trim());
      finding.append(makeElement("span", "finding-dot"));
      const copy = makeElement("div");
      const title = makeElement("div", "finding-title");
      title.append(document.createTextNode(`${item.title} `));
      title.append(makeElement("span", "finding-match", `in ${item.match}`));
      copy.append(title, makeElement("div", "finding-detail", item.detail));
      finding.append(copy, makeElement("span", "finding-tag", item.tag));
      findingList.append(finding);
    }
  } else {
    const allClear = makeElement("div", "all-clear");
    allClear.append(makeElement("span", "all-clear-icon", "✓"));
    allClear.append(makeElement("span", "", "No common allergens or flagged additives matched our quick scan. This is not a guarantee that the product is allergen-free."));
    findingList.append(allClear);
  }
  findings.append(findingList);
  results.replaceChildren(resultsTop, findings);
}

function renderProductResults(products) {
  productSearchResults.replaceChildren();
  if (!products.length) {
    productSearchResults.append(makeElement("p", "search-message", "No products with ingredient data were found. Try adding the brand name, or paste the package ingredients below."));
    return;
  }

  productSearchResults.append(makeElement("p", "search-message", "Choose the exact product and check the country or brand when shown:"));
  for (const product of products) {
    const card = makeElement("article", "product-result");
    const details = makeElement("div", "product-result-copy");
    details.append(makeElement("strong", "", product.name));
    if (product.brands || product.countries) {
      details.append(makeElement("span", "product-result-meta", [product.brands, product.countries].filter(Boolean).join(" · ")));
    }
    details.append(makeElement("span", "product-result-ingredients", product.ingredients));
    if (product.nutrition_grade) {
      details.append(makeElement("span", `nutrition-grade grade-${product.nutrition_grade}`, `Nutri-Score ${product.nutrition_grade.toUpperCase()}`));
    }
    const choose = makeElement("button", "choose-product", "Use this product");
    choose.type = "button";
    choose.addEventListener("click", () => {
      productField.value = product.name;
      ingredientField.value = product.ingredients;
      selectedNutritionGrade = product.nutrition_grade || "";
      productSearchResults.replaceChildren(makeElement("p", "search-message selected-product", "Product selected. Analyzing its listed ingredients..."));
      form.requestSubmit();
    });
    card.append(details, choose);
    productSearchResults.append(card);
  }
  const attribution = makeElement("p", "data-attribution", "Product data from ");
  const sourceLink = makeElement("a", "", "Open Food Facts");
  sourceLink.href = "https://world.openfoodfacts.org/";
  sourceLink.target = "_blank";
  sourceLink.rel = "noopener noreferrer";
  attribution.append(sourceLink, document.createTextNode(". Community contributed; packaging may have changed."));
  productSearchResults.append(attribution);
}

function renderError(message) {
  const error = makeElement("div", "request-error", message);
  results.replaceChildren(error);
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  analyzeButton.disabled = true;
  analyzeButton.setAttribute("aria-busy", "true");
  analyzeButton.lastChild.textContent = "Analyzing...";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_name: productField.value,
        nutrition_grade: selectedNutritionGrade,
        ingredients: ingredientField.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis failed. Please try again.");
    renderAnalysis(data);
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Couldn't reach the analyzer. Check your connection and try again.");
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.removeAttribute("aria-busy");
    analyzeButton.lastChild.textContent = "Analyze ingredients";
  }
});

document.querySelector("#sample-button").addEventListener("click", () => {
  productField.value = "Garden veggie crackers";
  selectedNutritionGrade = "";
  ingredientField.value = sampleIngredients;
  form.requestSubmit();
});

productField.addEventListener("input", () => {
  selectedNutritionGrade = "";
});

searchButton.addEventListener("click", async () => {
  const query = productField.value.trim();
  if (!query) {
    productSearchResults.replaceChildren(makeElement("p", "search-message", "Enter a food product name first."));
    productField.focus();
    return;
  }

  searchButton.disabled = true;
  searchButton.textContent = "Searching...";
  productSearchResults.replaceChildren(makeElement("p", "search-message", "Searching Open Food Facts..."));
  try {
    const response = await fetch(`/api/search-products?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Product search failed. Try again.");
    renderProductResults(data.products || []);
  } catch (error) {
    productSearchResults.replaceChildren(makeElement("p", "search-message search-error", error instanceof Error ? error.message : "Product search failed. You can paste the package ingredients instead."));
  } finally {
    searchButton.disabled = false;
    searchButton.textContent = "Find product";
  }
});
