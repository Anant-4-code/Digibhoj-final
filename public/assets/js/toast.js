// DigiBhoj — Toast Notification System

window.toast = (function() {
  let container = null;

  function getContainer() {
    if (!container) {
      container = document.getElementById('toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
      }
    }
    return container;
  }

  const icons = {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    '🔔'
  };

  function show(message, type = 'success', duration = 3500) {
    const c = getContainer();
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.innerHTML = `<span class="toast-icon">${icons[type] || '💬'}</span><span class="toast-text">${message}</span>`;
    c.appendChild(t);

    // Auto-remove
    setTimeout(() => {
      t.style.animation = 'toast-in 0.3s ease reverse';
      setTimeout(() => t.remove(), 280);
    }, duration);
  }

  return { show,
    success: (msg) => show(msg, 'success'),
    error:   (msg) => show(msg, 'error'),
    warning: (msg) => show(msg, 'warning'),
    info:    (msg) => show(msg, 'info')
  };
})();

// Auto-show toasts from query params
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('added'))   toast.success('Item added to cart! 🛒');
  if (params.get('success')) toast.success('Order placed successfully! 🎉');
  if (params.get('updated')) toast.success('Profile updated successfully! ✨');
  if (params.get('error'))   toast.error(params.get('error'));
});
