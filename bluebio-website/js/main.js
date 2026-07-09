// Nav: scrolled shadow state + mobile toggle
const nav = document.getElementById("nav");
const navToggle = document.getElementById("navToggle");
const navLinks = document.getElementById("navLinks");

window.addEventListener("scroll", () => {
  nav.classList.toggle("scrolled", window.scrollY > 12);
}, { passive: true });

navToggle.addEventListener("click", () => {
  navLinks.classList.toggle("open");
});
navLinks.querySelectorAll("a").forEach((a) => {
  a.addEventListener("click", () => navLinks.classList.remove("open"));
});

// Scroll reveal
const revealEls = document.querySelectorAll(".reveal");
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("visible");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });
revealEls.forEach((el) => revealObserver.observe(el));

// Stagger reveal within each grid/row for a nicer cascade
document.querySelectorAll(".services-grid, .values-grid, .pipeline-track, .app-grid").forEach((group) => {
  [...group.children].forEach((child, i) => {
    child.style.transitionDelay = `${i * 80}ms`;
  });
});

// Hero waveform bars
const waveBars = document.getElementById("waveBars");
if (waveBars) {
  const count = 26;
  for (let i = 0; i < count; i++) {
    const bar = document.createElement("span");
    const height = 30 + Math.round(Math.random() * 70);
    const delay = (Math.random() * 1.4).toFixed(2);
    bar.style.height = `${height}%`;
    bar.style.animationDelay = `${delay}s`;
    waveBars.appendChild(bar);
  }
}

// Footer year
const yearEl = document.getElementById("year");
if (yearEl) yearEl.textContent = new Date().getFullYear();
