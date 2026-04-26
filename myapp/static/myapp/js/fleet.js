const brandFilter = document.getElementById("filter-brand");
const typeFilter = document.getElementById("filter-type");
const transFilter = document.getElementById("filter-trans");
const priceFilter = document.getElementById("filter-price");

const cars = document.querySelectorAll(".car-card");
const count = document.getElementById("count");
const noResults = document.getElementById("no-results");

function filterCars() {
  let visibleCount = 0;

  cars.forEach((car) => {
    const brand = car.dataset.brand;
    const type = car.dataset.type;
    const trans = car.dataset.trans;
    const price = parseFloat(car.dataset.price);

    let show = true;

    if (brandFilter.value && brand !== brandFilter.value) {
      show = false;
    }

    if (typeFilter.value && type !== typeFilter.value) {
      show = false;
    }

    if (transFilter.value && trans !== transFilter.value) {
      show = false;
    }

    if (priceFilter.value) {
      const [min, max] = priceFilter.value.split("-").map(Number);
      if (price < min || price > max) {
        show = false;
      }
    }

    car.style.display = show ? "block" : "none";

    if (show) visibleCount++;
  });

  count.textContent = visibleCount;

  noResults.style.display = visibleCount === 0 ? "block" : "none";
}

brandFilter.addEventListener("change", filterCars);
typeFilter.addEventListener("change", filterCars);
transFilter.addEventListener("change", filterCars);
priceFilter.addEventListener("change", filterCars);


