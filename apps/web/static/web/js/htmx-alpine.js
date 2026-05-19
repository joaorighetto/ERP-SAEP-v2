/**
 * htmx-alpine.js
 *
 * Bridge: reinitialise Alpine.js components that HTMX injects into the DOM
 * after the initial page load (e.g. material search results, new item rows).
 *
 * Alpine registers itself on DOMContentLoaded and never sees dynamically-
 * inserted markup. Calling Alpine.initTree(target) manually after each swap
 * fills that gap.
 *
 * Loaded after both htmx.js and alpinejs (see base.html).
 */
document.addEventListener("htmx:afterSwap", function (event) {
  if (window.Alpine && event.detail && event.detail.target) {
    window.Alpine.initTree(event.detail.target);
  }
});
