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

document.querySelectorAll(".faq__question").forEach((btn) => {
  btn.addEventListener("click", () => {
    const item = btn.closest(".faq__item");
    const isOpen = item.classList.contains("open");
    document
      .querySelectorAll(".faq__item")
      .forEach((i) => i.classList.remove("open"));
    if (!isOpen) item.classList.add("open");
  });
});

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", function (e) {
    const targetId = this.getAttribute("href");

    if (targetId.length > 1) {
      const target = document.querySelector(targetId);

      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }
  });
});

window.addEventListener("load", () => {
  const hash = window.location.hash;

  if (hash) {
    const el = document.querySelector(hash);

    if (el) {
      setTimeout(() => {
        el.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    }
  }
});
