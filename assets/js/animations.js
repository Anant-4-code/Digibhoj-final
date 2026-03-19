// DigiBhoj — Scroll Animations (IntersectionObserver)

(function() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(el => {
      if (el.isIntersecting) {
        el.target.classList.add('revealed');
        observer.unobserve(el.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  function observe() {
    document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));
  }

  document.addEventListener('DOMContentLoaded', observe);

  // Counter animation for stat values
  function animateCounter(el) {
    const target = parseFloat(el.dataset.count || el.textContent.replace(/[^0-9.]/g, ''));
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const duration = 1200;
    const start = performance.now();
    function update(now) {
      const progress = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      el.textContent = prefix + (target % 1 === 0 ? Math.floor(target * ease).toLocaleString() : (target * ease).toFixed(1)) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  const counterObserver = new IntersectionObserver(entries => {
    entries.forEach(el => {
      if (el.isIntersecting) {
        animateCounter(el.target);
        counterObserver.unobserve(el.target);
      }
    });
  }, { threshold: 0.5 });

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.count-up').forEach(el => counterObserver.observe(el));
  });

  window.reinitAnimations = function() { observe(); };
})();
