// Publications page: filter the list as you type.
(function () {
  function setup() {
    var box = document.getElementById("pubsearch");
    if (!box || box.dataset.ready) return;
    box.dataset.ready = "1";
    var items = Array.prototype.slice.call(document.querySelectorAll("li.pub[data-search]"));
    var years = Array.prototype.slice.call(document.querySelectorAll("section.year"));
    var shown = document.getElementById("pubshown");
    box.addEventListener("input", function () {
      var terms = box.value.toLowerCase().split(/\s+/).filter(Boolean);
      var n = 0;
      items.forEach(function (li) {
        var hay = li.getAttribute("data-search");
        var ok = terms.every(function (t) { return hay.indexOf(t) !== -1; });
        li.hidden = !ok;
        if (ok) n++;
      });
      years.forEach(function (s) { s.hidden = !s.querySelector("li.pub:not([hidden])"); });
      if (shown) shown.textContent = n;
    });
  }
  // Material's instant navigation swaps pages without a reload.
  if (window.document$ && window.document$.subscribe) window.document$.subscribe(setup);
  else document.addEventListener("DOMContentLoaded", setup);
})();

// Gallery: click an image to view it large; arrows/Escape on the keyboard.
(function () {
  var box, media, cap, list = [], at = 0;
  function build() {
    box = document.createElement("div");
    box.className = "lightbox";
    box.innerHTML = '<button class="lightbox__close" aria-label="Close">×</button>' +
      '<button class="lightbox__prev" aria-label="Previous">‹</button>' +
      '<div class="lightbox__media"></div>' +
      '<button class="lightbox__next" aria-label="Next">›</button><p class="lightbox__cap"></p>';
    document.body.appendChild(box);
    media = box.querySelector(".lightbox__media");
    cap = box.querySelector(".lightbox__cap");
    box.querySelector(".lightbox__close").onclick = close;
    box.querySelector(".lightbox__prev").onclick = function (ev) { ev.stopPropagation(); show(at - 1); };
    box.querySelector(".lightbox__next").onclick = function (ev) { ev.stopPropagation(); show(at + 1); };
    box.addEventListener("click", function (ev) { if (ev.target === box) close(); });
    document.addEventListener("keydown", function (ev) {
      if (!box.classList.contains("is-open")) return;
      if (ev.key === "Escape") close();
      if (ev.key === "ArrowLeft") show(at - 1);
      if (ev.key === "ArrowRight") show(at + 1);
    });
  }
  function show(i) {
    at = (i + list.length) % list.length;
    var f = list[at];
    media.innerHTML = f.dataset.kind === "video"
      ? '<video src="' + f.dataset.full + '" autoplay muted loop playsinline controls></video>'
      : '<img src="' + f.dataset.full + '" alt="">';
    cap.textContent = f.dataset.caption || "";
    box.classList.add("is-open");
  }
  function close() { box.classList.remove("is-open"); media.innerHTML = ""; }
  function setup() {
    list = Array.prototype.slice.call(document.querySelectorAll(".gallery__item"));
    if (!list.length) return;
    if (!box) build();
    list.forEach(function (f, i) {
      f.onclick = function () { show(i); };
      f.onkeydown = function (ev) { if (ev.key === "Enter") show(i); };
    });
  }
  if (window.document$ && window.document$.subscribe) window.document$.subscribe(setup);
  else document.addEventListener("DOMContentLoaded", setup);
})();

// Header: transparent over the home-page picture, solid once you scroll; close the
// mobile menu after choosing a link.
(function () {
  function setup() {
    var h = document.querySelector("[data-lc-header]");
    if (!h) return;
    var onScroll = function () { h.classList.toggle("is-scrolled", window.scrollY > 40); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    var t = document.getElementById("lc-menu");
    document.querySelectorAll(".lc-nav__link").forEach(function (a) { a.addEventListener("click", function () { if (t) t.checked = false; }); });
  }
  if (document.readyState !== "loading") setup(); else document.addEventListener("DOMContentLoaded", setup);
})();

// Highlight the current page in the top menu.
(function () {
  var here = location.pathname.replace(/index\.html$/, "");
  document.querySelectorAll(".lc-nav__link[data-path]").forEach(function (a) {
    if (here.endsWith("/" + a.getAttribute("data-path"))) a.classList.add("is-active");
  });
})();
