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
})();
