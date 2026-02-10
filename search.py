"""Search engine based on TF-IDF + fuzzy scoring without embeddings."""

from __future__ import annotations

import csv
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from utils import detect_columns, parse_numeric, tokenize


@dataclass
class SearchResult:
    product: Dict[str, object]
    score: float
    tfidf_score: float
    fuzzy_score: float
    category_bonus: float
    matched_tokens: List[str]


class ProductSearchEngine:
    """Precomputed lexical engine for product search."""

    def __init__(self, csv_path: str, column_override: Optional[Dict[str, str]] = None) -> None:
        self.csv_path = csv_path
        self.column_override = column_override or {}
        self.products: List[Dict[str, object]] = []
        self.doc_vectors: List[Dict[str, float]] = []
        self.doc_norms: List[float] = []
        self.idf: Dict[str, float] = {}
        self.categories: List[str] = []
        self.last_index_build_ms: float = 0.0
        self.load_data()

    def load_data(self) -> None:
        start = time.perf_counter()
        with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("Le fichier CSV ne contient pas d'en-têtes de colonnes.")

            columns = detect_columns(reader.fieldnames, self.column_override)
            if not columns.get("title"):
                raise ValueError(
                    "Impossible de détecter une colonne titre. Configurez COLUMN_MAP_JSON, ex: {'title': 'product_name'}."
                )

            products: List[Dict[str, object]] = []
            category_set = set()
            tokenized_docs: List[List[str]] = []

            for idx, row in enumerate(reader):
                title = (row.get(columns["title"], "") if columns["title"] else "").strip()
                if not title:
                    continue
                description = (row.get(columns["description"], "") if columns["description"] else "").strip()
                category = (row.get(columns["category"], "") if columns["category"] else "").strip()
                brand = (row.get(columns["brand"], "") if columns["brand"] else "").strip()
                image_url = (row.get(columns["image_url"], "") if columns["image_url"] else "").strip()
                url = (row.get(columns["url"], "") if columns["url"] else "").strip()
                price = parse_numeric(row.get(columns["price"]) if columns["price"] else None)
                rating = parse_numeric(row.get(columns["rating"]) if columns["rating"] else None)

                text_parts = [title, description, category, brand]
                merged_tokens = tokenize(" ".join(part for part in text_parts if part))
                searchable_text = " ".join(merged_tokens)

                product = {
                    "id": idx,
                    "title": title,
                    "description": description,
                    "category": category,
                    "brand": brand,
                    "price": price,
                    "rating": rating,
                    "image_url": image_url,
                    "url": url,
                    "searchable_text": searchable_text,
                }
                products.append(product)
                tokenized_docs.append(merged_tokens)
                if category:
                    category_set.add(category)

        if not products:
            raise ValueError("Aucun produit valide trouvé dans le CSV.")

        self.products = products
        self._build_tfidf(tokenized_docs)
        self.categories = sorted(category_set)
        self.last_index_build_ms = (time.perf_counter() - start) * 1000

    def _build_tfidf(self, tokenized_docs: List[List[str]]) -> None:
        doc_count = len(tokenized_docs)
        doc_freq: Dict[str, int] = defaultdict(int)

        for tokens in tokenized_docs:
            for token in set(tokens):
                doc_freq[token] += 1

        self.idf = {
            token: math.log((1 + doc_count) / (1 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }

        self.doc_vectors = []
        self.doc_norms = []
        for tokens in tokenized_docs:
            counts = Counter(tokens)
            total = len(tokens) or 1
            vector: Dict[str, float] = {}
            for token, count in counts.items():
                tf = count / total
                vector[token] = tf * self.idf.get(token, 0.0)
            norm = math.sqrt(sum(value * value for value in vector.values()))
            self.doc_vectors.append(vector)
            self.doc_norms.append(norm)

    def _query_vector(self, query_tokens: List[str]) -> Tuple[Dict[str, float], float]:
        counts = Counter(query_tokens)
        total = len(query_tokens) or 1
        vector: Dict[str, float] = {}
        for token, count in counts.items():
            if token in self.idf:
                vector[token] = (count / total) * self.idf[token]
        norm = math.sqrt(sum(value * value for value in vector.values()))
        return vector, norm

    @staticmethod
    def _cosine_similarity(qvec: Dict[str, float], qnorm: float, dvec: Dict[str, float], dnorm: float) -> float:
        if qnorm == 0 or dnorm == 0:
            return 0.0
        dot = sum(weight * dvec.get(token, 0.0) for token, weight in qvec.items())
        return dot / (qnorm * dnorm)

    @staticmethod
    def _fuzzy_score(query_tokens: List[str], title: str) -> float:
        title_tokens = tokenize(title)
        if not title_tokens:
            return 0.0
        q = " ".join(sorted(set(query_tokens)))
        t = " ".join(sorted(set(title_tokens)))
        return SequenceMatcher(None, q, t).ratio()

    def search(
        self,
        query: str,
        *,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
        debug: bool = False,
        limit: int = 30,
    ) -> Tuple[List[SearchResult], Dict[str, object]]:
        query_tokens = tokenize(query)
        diagnostics: Dict[str, object] = {
            "query_tokens": query_tokens,
            "index_build_ms": round(self.last_index_build_ms, 2),
            "query_time_ms": 0.0,
            "total_products": len(self.products),
        }
        if not query_tokens:
            return [], diagnostics

        start = time.perf_counter()
        qvec, qnorm = self._query_vector(query_tokens)

        results: List[SearchResult] = []
        for idx, product in enumerate(self.products):
            price = product["price"]
            rating = product["rating"]
            if min_price is not None and (price is None or price < min_price):
                continue
            if max_price is not None and (price is None or price > max_price):
                continue
            if category and product.get("category") != category:
                continue
            if min_rating is not None and (rating is None or rating < min_rating):
                continue

            tfidf_score = self._cosine_similarity(qvec, qnorm, self.doc_vectors[idx], self.doc_norms[idx])
            fuzzy_score = self._fuzzy_score(query_tokens, str(product["title"]))
            token_set = set(query_tokens)
            matched_tokens = sorted(token_set.intersection(set(product["searchable_text"].split())))

            category_bonus = 0.0
            if product.get("category"):
                category_tokens = set(tokenize(str(product["category"])))
                if token_set.intersection(category_tokens):
                    category_bonus += 0.12
            if product.get("brand"):
                brand_tokens = set(tokenize(str(product["brand"])))
                if token_set.intersection(brand_tokens):
                    category_bonus += 0.08

            final_score = (0.72 * tfidf_score) + (0.22 * fuzzy_score) + category_bonus
            if final_score <= 0:
                continue

            results.append(
                SearchResult(
                    product=product,
                    score=final_score,
                    tfidf_score=tfidf_score,
                    fuzzy_score=fuzzy_score,
                    category_bonus=category_bonus,
                    matched_tokens=matched_tokens,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        trimmed = results[:limit]
        diagnostics["query_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
        if debug:
            diagnostics["top_scores"] = [
                {
                    "title": r.product["title"],
                    "final": round(r.score, 4),
                    "tfidf": round(r.tfidf_score, 4),
                    "fuzzy": round(r.fuzzy_score, 4),
                    "bonus": round(r.category_bonus, 4),
                }
                for r in trimmed[:5]
            ]

        return trimmed, diagnostics
