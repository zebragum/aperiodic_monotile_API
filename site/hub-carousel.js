/** Lightweight auto-advancing gallery for the Untiling hub. */
(function () {
  const root = document.querySelector("[data-carousel]");
  if (!root) return;

  const slides = Array.from(root.querySelectorAll("[data-slide]"));
  const dotsBox = root.querySelector("[data-carousel-dots]");
  const prevBtn = root.querySelector("[data-carousel-prev]");
  const nextBtn = root.querySelector("[data-carousel-next]");
  if (!slides.length || !dotsBox) return;

  let index = Math.max(
    0,
    slides.findIndex((s) => s.classList.contains("is-active"))
  );
  let timer = null;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const INTERVAL_MS = 4500;

  const dots = slides.map((_, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "hub-carousel-dot";
    b.setAttribute("role", "tab");
    b.setAttribute("aria-label", `Show image ${i + 1}`);
    b.addEventListener("click", () => go(i, true));
    dotsBox.appendChild(b);
    return b;
  });

  function go(next, userDriven) {
    index = ((next % slides.length) + slides.length) % slides.length;
    slides.forEach((slide, i) => {
      const on = i === index;
      slide.classList.toggle("is-active", on);
      slide.hidden = !on;
      dots[i].classList.toggle("is-active", on);
      dots[i].setAttribute("aria-selected", on ? "true" : "false");
    });
    if (userDriven) restart();
  }

  function restart() {
    if (reduceMotion) return;
    clearInterval(timer);
    timer = setInterval(() => go(index + 1, false), INTERVAL_MS);
  }

  prevBtn?.addEventListener("click", () => go(index - 1, true));
  nextBtn?.addEventListener("click", () => go(index + 1, true));

  root.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      go(index - 1, true);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      go(index + 1, true);
    }
  });

  let touchX = null;
  root.addEventListener(
    "touchstart",
    (e) => {
      touchX = e.changedTouches[0]?.clientX ?? null;
    },
    { passive: true }
  );
  root.addEventListener(
    "touchend",
    (e) => {
      if (touchX == null) return;
      const dx = (e.changedTouches[0]?.clientX ?? touchX) - touchX;
      touchX = null;
      if (Math.abs(dx) < 40) return;
      go(index + (dx < 0 ? 1 : -1), true);
    },
    { passive: true }
  );

  root.addEventListener("mouseenter", () => clearInterval(timer));
  root.addEventListener("mouseleave", restart);
  root.addEventListener("focusin", () => clearInterval(timer));
  root.addEventListener("focusout", restart);

  root.tabIndex = 0;
  go(index, false);
  restart();
})();
