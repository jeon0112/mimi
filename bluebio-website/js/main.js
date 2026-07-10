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

// Theme toggle (dark = 문제, light = 해결)
const themeToggle = document.getElementById("themeToggle");
const htmlEl = document.documentElement;
const moonIcon = document.getElementById("themeIconMoon");
const sunIcon = document.getElementById("themeIconSun");
themeToggle.addEventListener("click", () => {
  const isDark = htmlEl.getAttribute("data-theme") === "dark";
  const next = isDark ? "light" : "dark";
  htmlEl.setAttribute("data-theme", next);
  moonIcon.style.display = next === "dark" ? "" : "none";
  sunIcon.style.display = next === "dark" ? "none" : "";
  themeToggle.setAttribute("aria-pressed", String(next === "dark"));
  themeToggle.setAttribute(
    "aria-label",
    next === "dark" ? "라이트 모드로 전환 (문제에서 해결로)" : "다크 모드로 전환"
  );
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
document.querySelectorAll(".values-grid, .pipeline-track, .app-grid, .impact-grid").forEach((group) => {
  [...group.children].forEach((child, i) => {
    child.style.transitionDelay = `${i * 80}ms`;
  });
});

// Hero terminal: mood chips
document.querySelectorAll(".mood-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".mood-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
  });
});

// Hero terminal: photo drop simulation
const photoDrop = document.getElementById("photoDrop");
if (photoDrop) {
  photoDrop.addEventListener("click", () => {
    const chosen = photoDrop.classList.toggle("chosen");
    photoDrop.textContent = chosen ? "✅ 사진이 등록되었습니다" : "📷 사진을 올려보세요 (시뮬레이션)";
  });
}

// Hero terminal: AI 발행 burst animation
const publishBtn = document.getElementById("publishBtn");
const burstStage = document.getElementById("burstStage");
if (publishBtn && burstStage) {
  publishBtn.addEventListener("click", () => {
    burstStage.classList.remove("active");
    void burstStage.offsetWidth;
    requestAnimationFrame(() => burstStage.classList.add("active"));
  });
}

// 나라장터 매칭 시뮬레이션
const matchBtn = document.getElementById("matchBtn");
const bizType = document.getElementById("bizType");
const matchResult = document.getElementById("matchResult");
const matchResultText = document.getElementById("matchResultText");
if (matchBtn) {
  matchBtn.addEventListener("click", () => {
    const type = bizType.value;
    matchResultText.textContent = `${type} 유형에 맞는 공고 3건을 찾았습니다 · 사업계획서 초안이 완성되었습니다.`;
    matchResult.classList.remove("shown");
    void matchResult.offsetWidth;
    requestAnimationFrame(() => matchResult.classList.add("shown"));
  });
}

// 이동권 & 돌봄: 대기시간 카운트다운 (스크롤 진입 시 1회 실행)
const mobilityDemo = document.getElementById("mobilityDemo");
const mobilityTo = document.getElementById("mobilityTo");
if (mobilityDemo && mobilityTo) {
  const mobilityObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      mobilityDemo.classList.add("solved");
      const from = 90, to = 20, duration = 1200;
      const start = performance.now();
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        mobilityTo.textContent = Math.round(from - (from - to) * eased);
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      mobilityObserver.unobserve(mobilityDemo);
    });
  }, { threshold: 0.4 });
  mobilityObserver.observe(mobilityDemo);
}

// 임팩트 대시보드: 카운트업 + 이후 완만한 라이브 트리클
function startTrickle(el, base) {
  let current = base;
  setInterval(() => {
    current += Math.floor(Math.random() * 3) + 1;
    el.textContent = current.toLocaleString("ko-KR");
  }, 6000 + Math.random() * 4000);
}
document.querySelectorAll(".impact-num").forEach((el) => {
  const target = parseInt(el.dataset.target, 10);
  const impactObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const duration = 1400;
      const start = performance.now();
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased).toLocaleString("ko-KR");
        if (progress < 1) {
          requestAnimationFrame(tick);
        } else {
          startTrickle(el, target);
        }
      }
      requestAnimationFrame(tick);
      impactObserver.unobserve(el);
    });
  }, { threshold: 0.4 });
  impactObserver.observe(el);
});

// 문화예술 갤러리: 스크롤에 따른 3D 틸트
const galleryTrack = document.getElementById("galleryTrack");
if (galleryTrack) {
  let tilting = false;
  function updateGalleryTilt() {
    const rect = galleryTrack.getBoundingClientRect();
    const center = rect.left + rect.width / 2;
    [...galleryTrack.children].forEach((card) => {
      const cardRect = card.getBoundingClientRect();
      const cardCenter = cardRect.left + cardRect.width / 2;
      const dist = (cardCenter - center) / rect.width;
      const rotate = Math.max(-22, Math.min(22, dist * 44));
      const scale = 1 - Math.min(Math.abs(dist), 0.5) * 0.12;
      card.style.transform = `rotateY(${-rotate}deg) scale(${scale})`;
    });
    tilting = false;
  }
  galleryTrack.addEventListener("scroll", () => {
    if (!tilting) {
      tilting = true;
      requestAnimationFrame(updateGalleryTilt);
    }
  }, { passive: true });
  window.addEventListener("resize", updateGalleryTilt);
  updateGalleryTilt();
}

// 히어로 음성으로 듣기 (Web Speech API)
const ttsBtn = document.getElementById("ttsBtn");
if (ttsBtn && "speechSynthesis" in window) {
  const ttsLabel = document.getElementById("ttsLabel");
  let speaking = false;
  ttsBtn.addEventListener("click", () => {
    if (speaking) {
      window.speechSynthesis.cancel();
      speaking = false;
      ttsLabel.textContent = "음성으로 듣기";
      ttsBtn.setAttribute("aria-pressed", "false");
      return;
    }
    const heroTitle = document.getElementById("heroTitle");
    const heroSub = document.getElementById("heroSub");
    const text = `${heroTitle.textContent}. ${heroSub.textContent}`;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "ko-KR";
    utter.onend = () => {
      speaking = false;
      ttsLabel.textContent = "음성으로 듣기";
      ttsBtn.setAttribute("aria-pressed", "false");
    };
    window.speechSynthesis.speak(utter);
    speaking = true;
    ttsLabel.textContent = "정지";
    ttsBtn.setAttribute("aria-pressed", "true");
  });
} else if (ttsBtn) {
  ttsBtn.style.display = "none";
}

// Footer year
const yearEl = document.getElementById("year");
if (yearEl) yearEl.textContent = new Date().getFullYear();
