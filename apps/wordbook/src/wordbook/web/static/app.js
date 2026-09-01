// wordbook — progressive enhancement. The page works without this file;
// here we just swap fragments instead of doing full-page reloads.
(() => {
  "use strict";

  const prefix = document.body.classList.contains("mobile") ? "/m" : "/d";
  const lang = () => document.body.dataset.lang;
  const sort = () => document.body.dataset.sort;
  const q = () => (document.querySelector('.search input[name="q"]')?.value || "").trim();

  async function fragment(kind) {
    const p = new URLSearchParams({ lang: lang(), sort: sort(), q: q(), partial: kind });
    const res = await fetch(`${prefix}/?${p.toString()}`, {
      headers: { "x-requested-with": "fetch" },
    });
    return res.text();
  }

  async function refresh({ result = false, list = false } = {}) {
    if (result) document.getElementById("result").innerHTML = await fragment("result");
    if (list) document.getElementById("dictlist").innerHTML = await fragment("list");
    if (result) rateCountdown();
  }

  // Live "resets in 12h 58m 04s (around 14:32)" ticker on the rate-limit card.
  let rateTimer = null;
  function rateCountdown() {
    clearInterval(rateTimer);
    const el = document.querySelector(".rate-reset");
    if (!el) return;
    const at = el.dataset.resetAt
      ? Date.parse(el.dataset.resetAt)
      : Date.now() + parseInt(el.dataset.resetIn || "0", 10) * 1000;
    const clock = new Date(at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const pad = (n) => String(n).padStart(2, "0");
    const render = () => {
      const left = Math.round((at - Date.now()) / 1000);
      if (left <= 0) {
        el.textContent = "You can try again now — search above.";
        clearInterval(rateTimer);
        return;
      }
      const h = Math.floor(left / 3600);
      const m = Math.floor((left % 3600) / 60);
      el.textContent =
        "resets in " +
        (h ? h + "h " : "") +
        (h || m ? pad(m) + "m " : "") +
        pad(left % 60) +
        "s (around " +
        clock +
        ")";
    };
    render();
    rateTimer = setInterval(render, 1000);
  }

  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (form.matches(".search")) {
      e.preventDefault();
      refresh({ result: true });
    } else if (form.matches(".bookmark")) {
      e.preventDefault();
      bookmark(form);
    } else if (form.matches(".remove")) {
      e.preventDefault();
      remove(form);
    }
  });

  document.addEventListener("change", (e) => {
    if (!e.target.matches('.sortform select')) return;
    document.body.dataset.sort = e.target.value;
    refresh({ list: true });
  });

  // Close the language menu on an outside click.
  document.addEventListener("click", (e) => {
    const open = document.querySelector(".langmenu[open]");
    if (open && !e.target.closest(".langmenu")) open.open = false;
  });

  async function bookmark(form) {
    const btn = form.querySelector("button");
    btn.disabled = true;
    try {
      const res = await fetch("/api/dictionary", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          language: form.elements.lang.value,
          word: form.elements.word.value,
        }),
      });
      if (res.ok) await refresh({ result: true, list: true });
    } finally {
      btn.disabled = false;
    }
  }

  async function remove(form) {
    const l = form.elements.lang.value;
    const w = form.elements.word.value;
    const res = await fetch(`/api/dictionary/${l}/${encodeURIComponent(w)}`, {
      method: "DELETE",
    });
    if (res.ok || res.status === 404) await refresh({ result: true, list: true });
  }

  rateCountdown(); // in case the page loaded straight onto a rate-limit card
})();
