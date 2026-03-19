// DigiBhoj — Mouse Effects & Interactions
// Cursor Glow, Card Tilt, Magnetic Buttons, Parallax

(function() {
  // ── Cursor Glow ──────────────────────────────────────────────
  const glow = document.createElement('div');
  glow.className = 'cursor-glow';
  document.body.appendChild(glow);
  let mouseX = 0, mouseY = 0;
  document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    glow.style.left = mouseX + 'px';
    glow.style.top  = mouseY + 'px';
  });

  // ── Card Tilt Effect ──────────────────────────────────────────
  function initCardTilt() {
    document.querySelectorAll('.card-tilt').forEach(card => {
      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const cx   = rect.left + rect.width / 2;
        const cy   = rect.top  + rect.height / 2;
        const dx   = (e.clientX - cx) / (rect.width / 2);
        const dy   = (e.clientY - cy) / (rect.height / 2);
        card.style.transform = `perspective(600px) rotateX(${-dy*6}deg) rotateY(${dx*6}deg) scale(1.02)`;
        card.style.boxShadow = `${-dx*10}px ${-dy*10}px 30px rgba(168,184,91,0.2)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
        card.style.boxShadow = '';
      });
    });
  }

  // ── Magnetic Button Effect ───────────────────────────────────
  function initMagneticButtons() {
    document.querySelectorAll('.btn-primary, .btn-xl').forEach(btn => {
      btn.addEventListener('mousemove', e => {
        const rect = btn.getBoundingClientRect();
        const cx   = rect.left + rect.width / 2;
        const cy   = rect.top  + rect.height / 2;
        const dx   = (e.clientX - cx) * 0.25;
        const dy   = (e.clientY - cy) * 0.25;
        btn.style.transform = `translate(${dx}px, ${dy}px)`;
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
      });
    });
  }

  // ── Parallax Effect (hero section) ──────────────────────────
  function initParallax() {
    const layers = document.querySelectorAll('[data-parallax]');
    if (!layers.length) return;
    document.addEventListener('mousemove', e => {
      const xPct = (e.clientX / window.innerWidth  - 0.5) * 2;
      const yPct = (e.clientY / window.innerHeight - 0.5) * 2;
      layers.forEach(layer => {
        const speed = parseFloat(layer.dataset.parallax) || 5;
        layer.style.transform = `translate(${xPct * speed}px, ${yPct * speed}px)`;
      });
    });
  }

  // ── Page Enter Animation ─────────────────────────────────────
  document.body.classList.add('page-enter');

  // ── Dropdown Toggle ──────────────────────────────────────────
  document.querySelectorAll('[data-dropdown]').forEach(trigger => {
    const dropdown = trigger.closest('.dropdown');
    trigger.addEventListener('click', e => {
      e.stopPropagation();
      const isOpen = dropdown.classList.contains('open');
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
      if (!isOpen) dropdown.classList.add('open');
    });
  });
  document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
  });

  // ── Modal ─────────────────────────────────────────────────────
  document.querySelectorAll('[data-modal-open]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.modalOpen);
      if (target) target.classList.add('open');
    });
  });
  document.querySelectorAll('[data-modal-close], .modal-overlay').forEach(el => {
    el.addEventListener('click', e => {
      if (e.target === el) {
        document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
      }
    });
  });

  // ── Mobile Menu Toggle ───────────────────────────────────────
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const mobileOverlay = document.getElementById('mobileOverlay');

  if (menuToggle && sidebar && mobileOverlay) {
    function toggleMenu(e) {
      if (e) e.stopPropagation();
      sidebar.classList.toggle('open');
      mobileOverlay.classList.toggle('active');
    }
    menuToggle.addEventListener('click', toggleMenu);
    mobileOverlay.addEventListener('click', toggleMenu);
  }

  // ── Navbar scroll effect ─────────────────────────────────────
  const publicNav = document.querySelector('.public-nav, .navbar');
  if (publicNav) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 40) publicNav.classList.add('scrolled');
      else publicNav.classList.remove('scrolled');
    });
  }

  // ── Init all ─────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initCardTilt();
    initMagneticButtons();
    initParallax();
  });

  // ── Re-init after content update ─────────────────────────────
  window.reinitEffects = function() {
    initCardTilt();
    initMagneticButtons();
  };  // ── Theme Toggle ───────────────────────────────────────────────
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  window.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      const icon = themeToggle.querySelector('i');
      if (savedTheme === 'dark') icon.className = 'fa fa-sun';
      
      themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        icon.className = newTheme === 'dark' ? 'fa fa-sun' : 'fa fa-moon';
        
        // Add a satisfying pop effect
        themeToggle.style.transform = 'scale(0.8)';
        setTimeout(() => themeToggle.style.transform = 'scale(1)', 150);
      });
      
      // Hover effect
      themeToggle.addEventListener('mouseover', () => themeToggle.style.transform = 'scale(1.1)');
      themeToggle.addEventListener('mouseout', () => themeToggle.style.transform = 'scale(1)');
    }
  });

})();
