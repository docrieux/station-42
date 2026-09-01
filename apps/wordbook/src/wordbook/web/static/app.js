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
    } else if (form.matches(".manualform")) {
      e.preventDefault();
      saveManual(form);
    }
  });

  document.addEventListener("change", (e) => {
    if (!e.target.matches('.sortform select')) return;
    document.body.dataset.sort = e.target.value;
    refresh({ list: true });
  });

  document.addEventListener("click", (e) => {
    // "+ definition" clones the last row in that form.
    const addrow = e.target.closest(".addrow");
    if (addrow) {
      const rows = addrow.closest("form").querySelector(".senses");
      const row = rows.lastElementChild.cloneNode(true);
      row.querySelectorAll("textarea, input").forEach((el) => (el.value = ""));
      rows.appendChild(row);
      row.querySelector("textarea").focus();
      return;
    }
    // Close the language menu on an outside click.
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

  async function saveManual(form) {
    const senses = [...form.querySelectorAll(".senserow")]
      .map((r) => ({
        text: r.querySelector('[name="def"]').value.trim(),
        part_of_speech: r.querySelector('[name="pos"]').value.trim() || null,
        example: r.querySelector('[name="ex"]').value.trim() || null,
      }))
      .filter((s) => s.text);
    const word = form.elements.word.value.trim();
    if (!word || !senses.length) return;

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    try {
      const res = await fetch("/api/entries", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ language: form.elements.lang.value, word, senses }),
      });
      if (res.ok) {
        form.closest("details.addbox, details.editbox")?.removeAttribute("open");
        if (form.closest(".addbox")) form.reset();
        await refresh({ list: true });
      }
    } finally {
      btn.disabled = false;
    }
  }

  rateCountdown(); // in case the page loaded straight onto a rate-limit card
})();
