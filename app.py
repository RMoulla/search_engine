from __future__ import annotations

import os
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from search import ProductSearchEngine
from utils import parse_column_map

CSV_PATH = os.getenv("PRODUCTS_CSV", "products.csv")
COLUMN_MAP_JSON = os.getenv("COLUMN_MAP_JSON", "")
COLUMN_OVERRIDE = parse_column_map(COLUMN_MAP_JSON)

app = Flask(__name__)
engine: ProductSearchEngine | None = None
startup_error: str | None = None


@app.before_request
def lazy_load_engine() -> None:
    global engine, startup_error
    if engine is None and startup_error is None:
        try:
            engine = ProductSearchEngine(CSV_PATH, COLUMN_OVERRIDE)
        except Exception as exc:  # noqa: BLE001 - convert errors into UI message
            startup_error = str(exc)


@app.route("/", methods=["GET"])
def index() -> str:
    if startup_error:
        return render_template("index.html", error=startup_error, categories=[], examples=[])

    assert engine is not None
    examples = [
        "chaussures running pluie",
        "cadeau anniversaire",
        "ordinateur pour etudiant",
        "telephone 5g",
    ]
    return render_template("index.html", categories=engine.categories, examples=examples, error=None)


@app.route("/search", methods=["POST"])
def search() -> Any:
    if startup_error:
        return jsonify({"error": startup_error}), 500

    assert engine is not None
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    query = str(payload.get("query", "")).strip()
    min_price = payload.get("min_price")
    max_price = payload.get("max_price")
    min_rating = payload.get("min_rating")
    category = payload.get("category") or None
    debug = bool(payload.get("debug", False))

    def as_float(value: Any):
        try:
            return float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    results, diagnostics = engine.search(
        query,
        min_price=as_float(min_price),
        max_price=as_float(max_price),
        min_rating=as_float(min_rating),
        category=category,
        debug=debug,
    )

    serialized: List[Dict[str, Any]] = []
    for row in results:
        product = row.product
        serialized.append(
            {
                "title": product["title"],
                "description": product.get("description") or "Description non disponible.",
                "category": product.get("category") or "-",
                "brand": product.get("brand") or "-",
                "price": product.get("price"),
                "rating": product.get("rating"),
                "image_url": product.get("image_url") or "",
                "url": product.get("url") or "",
                "why": f"Tokens matchés: {', '.join(row.matched_tokens[:5]) or 'faible recouvrement lexical'} | score={row.score:.3f}",
                "debug_scores": {
                    "final": round(row.score, 4),
                    "tfidf": round(row.tfidf_score, 4),
                    "fuzzy": round(row.fuzzy_score, 4),
                    "bonus": round(row.category_bonus, 4),
                },
            }
        )

    return jsonify({"results": serialized, "diagnostics": diagnostics})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
