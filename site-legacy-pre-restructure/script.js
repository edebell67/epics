/* ============================================================
   The Tech Principle — interaction layer
   Progressive enhancement only: every section is readable
   and navigable with this file absent.
   ============================================================ */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- nav: solid background once scrolled ---------- */

  var nav = document.getElementById('nav');
  var ticking = false;

  function syncNav() {
    nav.classList.toggle('is-stuck', window.scrollY > 24);
    ticking = false;
  }

  window.addEventListener('scroll', function () {
    if (!ticking) {
      window.requestAnimationFrame(syncNav);
      ticking = true;
    }
  }, { passive: true });

  syncNav();

  /* ---------- mobile drawer ---------- */

  var toggle = document.getElementById('navToggle');
  var drawer = document.getElementById('navDrawer');

  function setDrawer(open) {
    toggle.setAttribute('aria-expanded', String(open));
    drawer.dataset.open = String(open);
    drawer.hidden = !open;
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }

  toggle.addEventListener('click', function () {
    setDrawer(toggle.getAttribute('aria-expanded') !== 'true');
  });

  drawer.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') setDrawer(false);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setDrawer(false);
      toggle.focus();
    }
  });

  /* ---------- scroll reveal ----------
     Guarded three ways: reduced-motion and missing-IO fall straight through to
     visible, and a watchdog reveals everything if the observer hasn't reported
     at all (throttled/background renderers never deliver callbacks — without
     this the page would sit permanently blank). */

  var revealables = document.querySelectorAll('.reveal');

  function revealAll() {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
  }

  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealAll();
  } else {
    var observerReported = false;

    var revealObserver = new IntersectionObserver(function (entries) {
      observerReported = true;
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.14, rootMargin: '0px 0px -8% 0px' });

    revealables.forEach(function (el) { revealObserver.observe(el); });

    window.setTimeout(function () {
      if (!observerReported) revealAll();
    }, 1200);
  }

  /* The stat band deliberately carries qualitative phrases rather than counts,
     so there is no counter animation here. If numeric figures are ever
     reintroduced, note that the previous implementation put the real value in
     the markup and only zeroed it when it was actually going to animate —
     otherwise a JS failure leaves the band reading "0". */
})();
