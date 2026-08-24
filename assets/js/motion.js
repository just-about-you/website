/* Scroll reveals, the hero screenshot rotator, and the sticky-header state.
 *
 * No dependencies and no network calls — the site's whole argument is that
 * nothing third-party watches you read it, so a CDN script would undercut the
 * page it is decorating. scripts/check.py fails the build on any external
 * host but Google Fonts.
 *
 * Two properties this file has to hold at once, which pull against each other:
 *
 *   FAIL VISIBLE.  motion.css scopes every hidden state under `.js`, and only
 *                  this script adds `.js`. So if the file 404s, is blocked, or
 *                  throws before it gets there, nothing is ever hidden and the
 *                  page reads perfectly — just unanimated. Hiding first and
 *                  revealing later would make a thrown error a blank page.
 *
 *   NO FLASH.      Anything already on screen is marked `is-in` synchronously,
 *                  in the same block that adds `.js`, so it is never painted
 *                  visible-then-hidden-then-visible. Doing that mark inside the
 *                  IntersectionObserver callback instead is a frame too late and
 *                  the hero visibly blinks.
 */
(function () {
  "use strict";

  var root = document.documentElement;

  var reduced = false;
  try {
    reduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) {
    /* matchMedia absent or throwing: treat motion as fine. The CSS media
     * query still applies on its own, so the reduced-motion path does not
     * depend on this flag being right. */
  }

  function inView(el) {
    var r = el.getBoundingClientRect();
    return r.top < (window.innerHeight || 0) && r.bottom > 0;
  }

  /* ── scroll reveal ──────────────────────────────────────────────────── */

  function initReveal() {
    var nodes = document.querySelectorAll(".reveal, .reveal-group");
    if (!nodes.length) return;

    // Stagger index for grouped children, read by motion.css as --i.
    var groups = document.querySelectorAll(".reveal-group");
    for (var g = 0; g < groups.length; g++) {
      var kids = groups[g].children;
      for (var k = 0; k < kids.length; k++) {
        kids[k].style.setProperty("--i", String(k));
      }
    }

    // Motion unwelcome, or no observer to drive it: show everything now and
    // do not wire anything up. The CSS covers reduced-motion independently.
    if (reduced || !("IntersectionObserver" in window)) {
      for (var a = 0; a < nodes.length; a++) nodes[a].classList.add("is-in");
      return;
    }

    // Everything already on screen is revealed before `.js` lands, so it is
    // never hidden for even one frame. This is the no-flash half.
    var pending = [];
    for (var i = 0; i < nodes.length; i++) {
      if (inView(nodes[i])) nodes[i].classList.add("is-in");
      else pending.push(nodes[i]);
    }
    if (!pending.length) return;

    var io = new IntersectionObserver(
      function (entries) {
        for (var e = 0; e < entries.length; e++) {
          if (!entries[e].isIntersecting) continue;
          entries[e].target.classList.add("is-in");
          // One-shot. Re-animating on every scroll past is nauseating.
          io.unobserve(entries[e].target);
        }
      },
      // Fire slightly before the top edge arrives, so the motion finishes
      // about when the reader gets there.
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
    );

    for (var p = 0; p < pending.length; p++) io.observe(pending[p]);

    // Backstop. If layout settles late — a webfont landing, an image finally
    // sizing — something can end up on screen without the observer having
    // fired for it. Cheap, runs once, then stops.
    window.setTimeout(function () {
      for (var q = pending.length - 1; q >= 0; q--) {
        if (!inView(pending[q])) continue;
        pending[q].classList.add("is-in");
        io.unobserve(pending[q]);
      }
    }, 600);
  }

  /* ── hero screenshot rotator ────────────────────────────────────────── */

  function initDevice() {
    var screen = document.querySelector("[data-rotate]");
    if (!screen) return;

    var shots = screen.querySelectorAll("img");
    if (shots.length < 2) return;
    // First frame stays put. It is a real screenshot, not a placeholder.
    if (reduced) return;

    var at = 0;
    window.setInterval(function () {
      // The interval still fires in a background tab; repainting a page
      // nobody is looking at is pure battery.
      if (document.hidden) return;
      shots[at].classList.remove("is-current");
      at = (at + 1) % shots.length;
      shots[at].classList.add("is-current");
    }, 3200);
  }

  /* ── sticky header ──────────────────────────────────────────────────── */

  function initHeader() {
    // The chrome lives on the shell, not the row inside it — the shell is the
    // full-bleed sticky element, so it is the one that gets the hairline.
    var header =
      document.querySelector(".header-shell") ||
      document.querySelector(".site-header");
    if (!header) return;

    var ticking = false;
    function update() {
      header.classList.toggle("is-stuck", window.scrollY > 8);
      ticking = false;
    }
    window.addEventListener(
      "scroll",
      function () {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(update);
      },
      { passive: true }
    );
    update();
  }

  /* ── go ─────────────────────────────────────────────────────────────── */

  function start() {
    initReveal(); // marks on-screen items before anything can hide
    root.classList.add("js"); // from here, off-screen reveals are hidden
    initDevice();
    initHeader();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
