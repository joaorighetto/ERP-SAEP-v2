/**
 * htmx-alpine.js
 *
 * Bridge: initialise Alpine.js components that HTMX injects into the DOM.
 *
 * Alpine v3 uses a MutationObserver and detects dynamically-inserted markup
 * automatically. The previous approach called Alpine.initTree(target) on the
 * entire swap target, which re-initialised ALL existing components inside it
 * (e.g. resetting deleted=true on hidden item rows, making them reappear).
 *
 * Fix: on htmx:afterSwap, walk only x-data elements that Alpine has NOT yet
 * initialised (no own _x_dataStack property). This is a safety net only —
 * in practice Alpine v3's MutationObserver handles new content on its own.
 *
 * Loaded after both htmx.js and alpinejs (see base.html).
 */
document.addEventListener("htmx:afterSwap", function (event) {
  if (!window.Alpine || !event.detail || !event.detail.target) return;
  event.detail.target.querySelectorAll("[x-data]").forEach(function (el) {
    if (!Object.prototype.hasOwnProperty.call(el, "_x_dataStack")) {
      window.Alpine.initTree(el);
    }
  });
});
