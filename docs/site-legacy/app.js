// === Scroll reveal ===
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); } });
}, { threshold: 0.15 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// === Nav scroll ===
const nav = document.getElementById('nav');
const scrollTop = document.getElementById('scrollTop');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 40);
  // Show/hide scroll-to-top button
  if (scrollTop) scrollTop.classList.toggle('visible', window.scrollY > 600);
});

// === Scroll to top ===
if (scrollTop) {
  scrollTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// === Hamburger ===
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');
hamburger.addEventListener('click', () => {
  const open = navLinks.style.display === 'flex';
  navLinks.style.display = open ? 'none' : 'flex';
  navLinks.style.flexDirection = open ? '' : 'column';
  navLinks.style.position = open ? '' : 'absolute';
  navLinks.style.top = open ? '' : '60px';
  navLinks.style.left = open ? '' : '0';
  navLinks.style.right = open ? '' : '0';
  navLinks.style.background = open ? '' : 'rgba(6,8,13,0.97)';
  navLinks.style.padding = open ? '' : '20px';
  navLinks.style.borderBottom = open ? '' : '1px solid rgba(255,255,255,0.06)';
});

// === Terminal typing effect ===
const termLines = document.querySelectorAll('#terminal > div');
termLines.forEach((line, i) => {
  line.style.opacity = '0';
  line.style.transition = 'opacity 0.4s';
});
const termObs = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      termLines.forEach((line, i) => {
        setTimeout(() => { line.style.opacity = '1'; }, i * 300);
      });
      termObs.unobserve(e.target);
    }
  });
}, { threshold: 0.3 });
const termEl = document.getElementById('terminal');
if (termEl) termObs.observe(termEl);

// === Metric bars animation ===
document.querySelectorAll('.metric-bar-fill').forEach(bar => {
  const w = bar.style.width;
  bar.style.width = '0';
  const mObs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) { bar.style.width = w; mObs.unobserve(e.target); }
    });
  }, { threshold: 0.5 });
  mObs.observe(bar);
});

// === Smooth scroll for nav links ===
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', (e) => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
    if (window.innerWidth < 900) navLinks.style.display = 'none';
  });
});

// === Animated counter for hero stats ===
function animateCounter(el, target, suffix = '') {
  let current = 0;
  const step = Math.ceil(target / 40);
  const timer = setInterval(() => {
    current += step;
    if (current >= target) { current = target; clearInterval(timer); }
    el.textContent = current.toLocaleString() + suffix;
  }, 30);
}

const statObserver = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      const el = e.target;
      const text = el.textContent.trim();
      // Animate "1,000+"
      if (text.includes('1,000')) {
        animateCounter(el, 1000, '+');
      }
      statObserver.unobserve(el);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('.hero-stat-value').forEach(el => statObserver.observe(el));
