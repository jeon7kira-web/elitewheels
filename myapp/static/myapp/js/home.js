const cars = document.querySelectorAll(".car");
const carcontainer = document.querySelector(".cars-container");

function setActive(car) {
  cars.forEach((c) => c.classList.remove("active"));
  car.classList.add("active");
}

if (carcontainer) {
  cars.forEach((car) => {
    car.addEventListener("mouseenter", () => {
      setActive(car);
    });
  });

  carcontainer.addEventListener("mouseleave", () => {
    setActive(cars[0]);
  });
}

// Reviews slider
const reviewCards = document.querySelectorAll(".reviews__card");
let reviewCurrent = 0;

function changeSlide(dir) {
  if (!reviewCards.length) return;
  reviewCards[reviewCurrent].classList.remove("active");
  reviewCurrent =
    (reviewCurrent + dir + reviewCards.length) % reviewCards.length;
  reviewCards[reviewCurrent].classList.add("active");
}

if (reviewCards.length) {
  setInterval(() => changeSlide(1), 3500);
}

document
  .querySelector(".reviews__arrow--left")
  ?.addEventListener("click", () => changeSlide(-1));
document
  .querySelector(".reviews__arrow--right")
  ?.addEventListener("click", () => changeSlide(1));
