const resultsEl = document.getElementById('results');
const diagnosticsEl = document.getElementById('diagnostics');
const searchBtn = document.getElementById('search-btn');
const queryInput = document.getElementById('query');
const modal = document.getElementById('details-modal');
const modalTitle = document.getElementById('modal-title');
const modalDescription = document.getElementById('modal-description');
const closeModalBtn = document.getElementById('close-modal');

const PLACEHOLDER_IMAGE =
  'https://placehold.co/640x420/f1f5f9/334155?text=Image+indisponible';

function formatPrice(value) {
  if (value === null || value === undefined) return 'Prix non disponible';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatRating(value) {
  return value === null || value === undefined ? 'N/A' : `${value.toFixed(1)} / 5`;
}

function openDetails(title, description) {
  modalTitle.textContent = title;
  modalDescription.textContent = description;
  modal.showModal();
}

function renderEmpty() {
  resultsEl.innerHTML = `
    <article class="empty-state">
      <h3>Aucun résultat trouvé</h3>
      <p>Essaie d'ajouter une marque, une catégorie, ou un prix.</p>
    </article>
  `;
}

function renderResults(items, debugEnabled) {
  if (!items.length) {
    renderEmpty();
    return;
  }

  resultsEl.innerHTML = '';
  items.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'card';

    const image = document.createElement('img');
    image.src = item.image_url || PLACEHOLDER_IMAGE;
    image.alt = item.title;
    image.onerror = () => {
      image.src = PLACEHOLDER_IMAGE;
    };

    const content = document.createElement('div');
    content.className = 'card-content';
    const debugRow = debugEnabled
      ? `<div class="muted">Debug → TF-IDF: ${item.debug_scores.tfidf}, Fuzzy: ${item.debug_scores.fuzzy}, Bonus: ${item.debug_scores.bonus}, Final: ${item.debug_scores.final}</div>`
      : '';

    content.innerHTML = `
      <strong>${item.title}</strong>
      <div class="muted">${item.category} · ${item.brand}</div>
      <div>${formatPrice(item.price)}</div>
      <div class="muted">⭐ ${formatRating(item.rating)}</div>
      <button type="button" class="details-btn">Voir détails</button>
      <div class="why">Pourquoi ce résultat ? ${item.why}</div>
      ${debugRow}
    `;

    content.querySelector('.details-btn').addEventListener('click', () => {
      openDetails(item.title, item.description);
    });

    card.appendChild(image);
    card.appendChild(content);
    resultsEl.appendChild(card);
  });
}

async function runSearch() {
  const query = queryInput.value.trim();
  if (!query) {
    renderEmpty();
    return;
  }

  const payload = {
    query,
    min_price: document.getElementById('min-price').value,
    max_price: document.getElementById('max-price').value,
    min_rating: document.getElementById('min-rating').value,
    category: document.getElementById('category').value,
    debug: document.getElementById('debug').checked,
  };

  diagnosticsEl.textContent = 'Recherche en cours...';

  const resp = await fetch('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const errorPayload = await resp.json();
    diagnosticsEl.textContent = `Erreur: ${errorPayload.error || 'inconnue'}`;
    renderEmpty();
    return;
  }

  const data = await resp.json();
  const d = data.diagnostics;
  diagnosticsEl.textContent = `Produits indexés: ${d.total_products} · build index: ${d.index_build_ms} ms · recherche: ${d.query_time_ms} ms`;
  renderResults(data.results, payload.debug);
}

searchBtn?.addEventListener('click', runSearch);
queryInput?.addEventListener('keydown', (evt) => {
  if (evt.key === 'Enter') runSearch();
});

closeModalBtn?.addEventListener('click', () => modal.close());

document.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    queryInput.value = chip.dataset.q;
    runSearch();
  });
});
