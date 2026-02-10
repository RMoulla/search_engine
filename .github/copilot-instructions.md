# Copilot Instructions for Search Engine

## Project Overview

A Flask-based **product search engine without embeddings**, combining three lexical scoring methods:
- **TF-IDF** (72% weight): Cosine similarity on tokenized product fields
- **Fuzzy matching** (22% weight): SequenceMatcher on product titles  
- **Category/brand bonus** (6% weight): +0.12 if category tokens match, +0.08 for brand

**Non-goal**: This is NOT a semantic search engine—focus on lexical/heuristic approaches.

## Architecture

### Core Components

| File | Role |
|------|------|
| `search.py` | `ProductSearchEngine`: Loads CSV, builds TF-IDF index, scores results via `search(query, filters)` |
| `app.py` | Flask routes. `/` renders UI; `/search` POST handler deserializes JSON payload, calls engine, returns scored results |
| `utils.py` | Tokenization (stopword/synonym filtering), text normalization (accent stripping), numeric parsing, column detection |
| `static/app.js` | Vanilla JS: sends `/search` POST; renders card grid; modal details view; passes `debug` flag to show score breakdown |
| `templates/index.html` | Jinja2: category dropdown + price/rating filters; chip buttons for example queries |

### Data Flow

```
CSV (products.csv) 
  → detect_columns() [heuristic + COLUMN_MAP_JSON override] 
  → tokenize(title + description + category + brand) 
  → build TF-IDF + collect categories
  
Query (Frontend POST)
  → tokenize + _query_vector() 
  → filter by price/rating/category 
  → score each product (TF-IDF + fuzzy + bonus)
  → sort, limit 30, return with diagnostics
```

## Key Patterns & Decisions

### 1. **Column Auto-Detection with Overrides**
- `detect_columns()` in `utils.py` heuristically matches CSV headers against `COLUMN_CANDIDATES`.
- Override via env var: `export COLUMN_MAP_JSON='{"title":"product_name","price":"amount"}'`
- If no `title` column found → error with helpful message.
- When adding/changing data sources: **always test column detection** (see `COLUMN_CANDIDATES` dict).

### 2. **Lazy Engine Initialization**
- Engine built on first request via `@app.before_request` hook.
- Startup errors captured and displayed in UI (no 500 crash).
- Query CSV path via: `export PRODUCTS_CSV="/path/to/custom.csv"`

### 3. **Scoring is Deterministic, Not ML**
- Three independent scores combined linearly: `0.72*tfidf + 0.22*fuzzy + bonus`
- Adjust weights *only* if you understand TF-IDF/fuzzy ratio trade-offs (lexical recall vs. fuzzy noise).
- Debug mode (`?debug=true` via frontend) returns score breakdown per result—use this to validate scoring changes.

### 4. **Tokenization: Stopwords + Synonyms**
- `tokenize()` removes 40+ FR/EN stopwords (`de`, `le`, `the`, etc.) and applies synonym mapping (`"basket"→"chaussure"`, `"tel"→"telephone"`).
- Text normalized: lowercase, accents stripped, punctuation removed.
- When adding synonyms: maintain bidirectional coverage in `SYNONYMS` dict in `utils.py`.

### 5. **No Async/Background Jobs**
- Everything synchronous: CSV load, TF-IDF build, search within single request cycle.
- Index pre-built at startup (not per-query). For 10k products, query ~100ms on standard laptop.

## Critical Workflows

### Running Locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # Runs on http://localhost:8000
```

### Environment Configuration
```bash
export PRODUCTS_CSV="./data/my_products.csv"      # Path to CSV
export COLUMN_MAP_JSON='{"title":"name","price":"cost"}'  # Map non-standard columns
python app.py
```

### Testing
```bash
pytest  # Runs tests (if present in tests/ folder)
```

### Performance Debugging
- **Index build time**: Shown in UI diagnostics (`index_build_ms`).
- **Query time**: Shown in UI diagnostics (`query_time_ms`).
- **Enable debug mode**: Frontend checkbox "Debug scores" shows TF-IDF/fuzzy/bonus breakdown per result.
- **Profiling**: Add `time.perf_counter()` markers in `search.search()` method.

## Frontend Integration (app.js)

- **POST `/search`**: `{query, min_price, max_price, min_rating, category, debug}`
- **Response**: `{results: [...], diagnostics: {query_tokens, index_build_ms, query_time_ms, total_products, top_scores (if debug)}}`
- **No frameworks**: Vanilla JS + HTML `<dialog>` modal for product details.
- **Localization**: French UI text. If expanding to other languages, update `formatPrice()` locale and stopwords.

## Common Modifications

| Task | Files | Notes |
|------|-------|-------|
| Add new scoring dimension | `search.py` `_build_tfidf()` / `search()` | Update weights to stay ≤1.0. Test with debug mode. |
| Change stopwords | `utils.py` `STOPWORDS_FR_EN` | Add terms and re-test with realistic queries. |
| Add synonyms | `utils.py` `SYNONYMS` | Bidirectional: `"basket"→"chaussure"` and reverse if needed. |
| Filter results | `search.py` `search()` method price/rating checks | Add before score calculation; update query params in `app.js` payload. |
| Customize result cards | `static/app.js` `renderResults()` | Modify card HTML structure; maintain `item.why` explanation. |
| Add CSV source | `app.py` main | Update `CSV_PATH`; ensure column names match `COLUMN_CANDIDATES` or use `COLUMN_MAP_JSON`. |

## What NOT to Do

- ❌ Don't add heavy ML models (embeddings, classifiers)—contradicts "no embeddings" design.
- ❌ Don't remove matched token explanation (`item.why`)—transparency is a design principle.
- ❌ Don't skip debug score breakdown—essential for validating scoring changes.
- ❌ Don't cache results across requests—each query re-scores live index.
