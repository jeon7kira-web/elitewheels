const cars = document.querySelectorAll(".car");
const carcontainer = document.querySelector(".car-container");

function setActive(car) {
  cars.forEach((c) => c.classList.remove("active"));
  car.classList.add("active");
}

cars.forEach((car) => {
  car.addEventListener("mouseenter", () => {
    setActive(car);
  });
});

container.addEventListener("mouseleave", () => {
  setActive(cars[0]); // first main car
});
