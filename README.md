# Moteur de recherche produits intelligent (sans embeddings)

Application Flask qui charge `products.csv`, construit un index TF-IDF au démarrage, puis combine :

- score TF-IDF (lexical)
- fuzzy matching sur le titre
- bonus de matching catégorie/marque

Le tout avec filtres UX (prix, catégorie, note), mode debug des scores et interface moderne en cartes.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
python app.py
```

Puis ouvrir `http://localhost:8000`.

## Configuration de mapping colonnes

Le chargeur détecte automatiquement les colonnes usuelles (`title`, `description`, `price`, `rating`, `image_url`, `category`, `brand`, `url`).

Si le schéma diffère, vous pouvez forcer le mapping via variable d'environnement :

```bash
export COLUMN_MAP_JSON='{"title":"product_name","price":"amount"}'
python app.py
```

Vous pouvez aussi pointer un CSV différent :

```bash
export PRODUCTS_CSV="/chemin/vers/products.csv"
python app.py
```

## Tests

```bash
pytest
```

## Notes performance

- L'index TF-IDF est pré-calculé au démarrage.
- Le temps de build index et de requête est affiché dans l'UI.
- Pour 10k produits, la recherche reste rapide sur laptop standard (objectif < 200ms selon machine/données).
