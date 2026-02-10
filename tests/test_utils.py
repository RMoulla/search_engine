from pathlib import Path

from search import ProductSearchEngine


def test_search_ranking_with_typos_and_synonyms(tmp_path: Path) -> None:
    data = """title,description,selling_price,average_rating,category,brand\nChaussure Running Homme,Imperméable pour pluie,89.9,4.5,Sport,Nike\nOrdinateur Portable Étudiant,léger et rapide,799,4.7,Informatique,Lenovo\nTéléphone 5G,grand écran et batterie,499,4.2,Mobile,Samsung\nMug Cadeau Anniversaire,idée cadeau personnalisée,19.9,4.0,Maison,GiftCo\nChaise de bureau ergonomique,confort dos,159,4.1,Mobilier,FlexSeat\n"""
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(data, encoding="utf-8")

    engine = ProductSearchEngine(str(csv_path))

    results_typos, debug_typos = engine.search("chaussur runing pluie", debug=True)
    assert results_typos
    assert results_typos[0].product["title"] == "Chaussure Running Homme"
    assert "top_scores" in debug_typos

    results_synonyms, _ = engine.search("cadeaux anniv")
    assert results_synonyms
    assert results_synonyms[0].product["title"] == "Mug Cadeau Anniversaire"
tests/test_utils.py
tests/test_utils.py
Nouveau
+13
-0

from utils import normalize_text, tokenize


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("Téléphone, ÉTUDIANT !") == "telephone etudiant"


def test_tokenize_applies_synonyms_and_stopwords() -> None:
    tokens = tokenize("basket pour tel et runing")
    assert "chaussure" in tokens
    assert "telephone" in tokens
    assert "running" in tokens
    assert "pour" not in tokens
