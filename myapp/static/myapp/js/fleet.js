const allCards  = document.querySelectorAll('.car-card');
const countEl   = document.getElementById('count');
const noResults = document.getElementById('no-results');

function applyFilters() {
  const brand = document.getElementById('filter-brand').value;
  const type  = document.getElementById('filter-type').value;
  const trans = document.getElementById('filter-trans').value;
  const price = document.getElementById('filter-price').value;

  let visible = 0;

  allCards.forEach(card => {
    const cb = card.dataset.brand;
    const ct = card.dataset.type;
    const cr = card.dataset.trans;
    const cp = parseInt(card.dataset.price);

    let show = true;
    if (brand && cb !== brand) show = false;
    if (type  && ct !== type)  show = false;
    if (trans && cr !== trans) show = false;
    if (price) {
      const [min, max] = price.split('-').map(Number);
      if (cp < min || cp > max) show = false;
    }

    card.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  countEl.textContent     = visible;
  noResults.style.display = visible === 0 ? 'block' : 'none';
}

['filter-brand', 'filter-type', 'filter-trans', 'filter-price'].forEach(id =>
  document.getElementById(id).addEventListener('change', applyFilters)
);