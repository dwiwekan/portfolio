/* Click a filled image-slot -> open it in a lightbox instead of the file picker.
   Empty slots keep their normal behaviour so images can still be dropped in. */
(function () {
  if (window.__slotLightbox) return;
  window.__slotLightbox = true;

  function slotImage(slot) {
    try {
      const img = slot.shadowRoot && slot.shadowRoot.querySelector('.frame img');
      if (img && img.currentSrc) return img.currentSrc;
      if (img && img.src) return img.src;
    } catch (e) {}
    return null;
  }

  let overlay = null;
  function close() {
    if (!overlay) return;
    overlay.remove();
    overlay = null;
    document.removeEventListener('keydown', onKey);
  }
  function onKey(e) { if (e.key === 'Escape') close(); }

  function open(src) {
    close();
    overlay = document.createElement('div');
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.style.cssText =
      'position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;' +
      'padding:5vmin;background:color-mix(in srgb, var(--color-text, #201e1d) 78%, transparent);' +
      'cursor:zoom-out';
    const img = document.createElement('img');
    img.src = src;
    img.alt = '';
    img.style.cssText = 'max-width:100%;max-height:100%;object-fit:contain;box-shadow:0 24px 60px rgba(0,0,0,.35)';
    overlay.appendChild(img);
    overlay.addEventListener('click', close);
    document.body.appendChild(overlay);
    document.addEventListener('keydown', onKey);
  }

  document.addEventListener('click', function (e) {
    const slot = e.target && e.target.closest && e.target.closest('image-slot');
    if (!slot) return;
    // Leave authoring affordances alone while the host is in edit mode.
    if (slot.hasAttribute('data-editable') && e.altKey) return;
    const src = slotImage(slot);
    if (!src) return;
    e.preventDefault();
    e.stopPropagation();
    open(src);
  }, true);
})();
