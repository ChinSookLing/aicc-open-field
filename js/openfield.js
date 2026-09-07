(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];

  async function loadJSON(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load " + path);
    return res.json();
  }

  function allPeople(aff) {
    return [...(aff.standing || []), ...(aff.guests || [])];
  }

  function personById(aff, id) {
    return allPeople(aff).find((p) => p.id === id) || null;
  }

  function fallbackColor(aff) {
    return (aff && aff.fallbackColor) || "#FFD700";
  }

  function colorOf(aff, personOrId) {
    if (personOrId && typeof personOrId === "object") {
      return personOrId.color || fallbackColor(aff);
    }
    const p = personById(aff, personOrId);
    return (p && p.color) || fallbackColor(aff);
  }

  function returnIds(day) {
    return (day.returns || []).map((r) => r.affiliate);
  }

  function renderFilters(aff, active, onPick) {
    const box = $("#filters");
    if (!box) return;
    box.innerHTML = "";
    const make = (id, name, color) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip" + (active === id ? " is-on" : "");
      b.style.setProperty("--c", color || fallbackColor(aff));
      b.dataset.id = id;
      if (id !== "all") {
        const d = document.createElement("span");
        d.className = "dot";
        b.appendChild(d);
      }
      b.appendChild(document.createTextNode(name.toUpperCase()));
      b.addEventListener("click", () => onPick(id));
      box.appendChild(b);
    };
    make("all", "All", fallbackColor(aff));
    allPeople(aff).forEach((p) => make(p.id, p.name, p.color));
  }

  function renderPath(days, aff, filter) {
    const path = $("#path");
    if (!path) return;
    path.innerHTML = "";
    days.forEach((day) => {
      const ids = returnIds(day);
      const match = filter === "all" || ids.includes(filter);
      const el = document.createElement("div");
      el.className = "lantern" + (ids.length ? "" : " is-empty") + (match ? " is-focus" : " is-dim");
      const href = "day.html?d=" + encodeURIComponent(day.id);
      const dots = ids
        .map((id) => {
          const p = personById(aff, id);
          if (!p) return `<span style="--c:${fallbackColor(aff)}" title="${id}"></span>`;
          const guestCls = p.guest ? " is-guest" : "";
          return `<span class="${guestCls.trim()}" style="--c:${colorOf(aff, p)}" title="${p.name}${p.guest ? " (guest)" : ""}"></span>`;
        })
        .join("");
      el.innerHTML = `
        <a href="${href}">
          <div class="dots">${dots || "&nbsp;"}</div>
          <div class="flame" aria-hidden="true"></div>
          <div class="pole" aria-hidden="true"></div>
          <div class="label">DAY ${String(day.number).padStart(2, "0")}</div>
          <div class="date">${day.dateLabel || day.date}</div>
        </a>`;
      path.appendChild(el);
    });
  }

  function renderDay(day, aff) {
    const title = $("#day-title");
    const meta = $("#day-meta");
    const who = $("#who");
    const box = $("#returns");
    if (!day || !box) return;
    if (title) title.textContent = "DAY " + String(day.number).padStart(3, "0");
    if (meta) meta.textContent = day.dateLabel || day.date;
    const invited = (day.invited || []).map((id) => personById(aff, id)?.name || id);
    const returned = returnIds(day).map((id) => personById(aff, id)?.name || id);
    if (who) {
      who.innerHTML = `<div><strong>Who went out?</strong> ${invited.length ? invited.join(" · ") : "—"}</div>
        <div><strong>Who returned?</strong> ${returned.length ? returned.join(" · ") : "Nobody returned."}</div>`;
    }
    box.innerHTML = "";
    if (!(day.returns || []).length) {
      box.innerHTML = `<div class="empty-day">The day exists.<br>Nobody returned yet.</div>`;
      return;
    }
    day.returns.forEach((r) => {
      const p = personById(aff, r.affiliate);
      const card = document.createElement("article");
      card.className = "card" + (p?.guest ? " is-guest" : "");
      card.style.setProperty("--c", colorOf(aff, p));
      card.innerHTML = `
        <div class="who-line">
          <span class="name">${(p?.name || r.affiliate).toUpperCase()}${p?.guest ? " · GUEST" : ""}</span>
          ${r.keyword ? `<span class="kw">${r.keyword}</span>` : ""}
          <span class="kw">${r.date || day.date}</span>
          ${r.form ? `<span class="kw">${r.form}</span>` : ""}
        </div>
        <div class="body"></div>`;
      card.querySelector(".body").textContent = r.body || "";
      box.appendChild(card);
    });
  }

  function renderFieldIndex(days, aff) {
    const byAff = $("#by-affiliate");
    const byMonth = $("#by-month");
    const byDay = $("#by-day");
    const byForm = $("#by-form");
    if (!byAff) return;

    const affMap = {};
    const monthMap = {};
    const formMap = {};
    days.forEach((day) => {
      (day.returns || []).forEach((r) => {
        (affMap[r.affiliate] ||= []).push({ day, r });
        const m = (r.date || day.date || "").slice(0, 7);
        if (m) (monthMap[m] ||= []).push({ day, r });
        const f = (r.form || "Words").toLowerCase();
        (formMap[f] ||= []).push({ day, r });
      });
    });

    const list = (el, items, labelFn, hrefFn) => {
      el.innerHTML = "";
      if (!items.length) {
        el.innerHTML = `<li style="color:var(--muted)">No returns yet.</li>`;
        return;
      }
      items.forEach((it) => {
        const li = document.createElement("li");
        li.innerHTML = `<a href="${hrefFn(it)}">${labelFn(it)}</a>`;
        el.appendChild(li);
      });
    };

    byAff.innerHTML = "";
    allPeople(aff).forEach((p) => {
      const n = (affMap[p.id] || []).length;
      const li = document.createElement("li");
      li.innerHTML = `<a href="index.html?filter=${p.id}"><span class="dot${p.guest ? " is-guest" : ""}" style="--c:${colorOf(aff, p)}"></span>${p.name}${p.guest ? " (guest)" : ""} — ${n} return${n === 1 ? "" : "s"}</a>`;
      byAff.appendChild(li);
    });

    const months = Object.keys(monthMap).sort();
    byMonth.innerHTML = months.length
      ? months.map((m) => `<li><a href="index.html">${m} — ${monthMap[m].length}</a></li>`).join("")
      : `<li style="color:var(--muted)">No returns yet.</li>`;

    byDay.innerHTML = days
      .map((d) => `<li><a href="day.html?d=${d.id}">Day ${String(d.number).padStart(3, "0")} · ${d.dateLabel || d.date} · ${(d.returns || []).length} returned</a></li>`)
      .join("");

    const forms = Object.keys(formMap).sort();
    byForm.innerHTML = forms.length
      ? forms.map((f) => `<li><a href="index.html">${f} — ${formMap[f].length}</a></li>`).join("")
      : `<li style="color:var(--muted)">No returns yet.</li>`;
  }

  async function boot() {
    const page = document.body.dataset.page;
    const [aff, data] = await Promise.all([
      loadJSON("data/affiliates.json"),
      loadJSON("data/days.json"),
    ]);
    const days = data.days || [];

    if (page === "home") {
      let filter = new URLSearchParams(location.search).get("filter") || "all";
      const paint = () => {
        renderFilters(aff, filter, (id) => {
          filter = id;
          const u = new URL(location.href);
          if (id === "all") u.searchParams.delete("filter");
          else u.searchParams.set("filter", id);
          history.replaceState(null, "", u);
          paint();
        });
        renderPath(days, aff, filter);
      };
      paint();
    }

    if (page === "day") {
      const id = new URLSearchParams(location.search).get("d") || "001";
      const day = days.find((d) => d.id === id) || days[0];
      renderDay(day, aff);
    }

    if (page === "index") {
      renderFieldIndex(days, aff);
    }
  }

  boot().catch((err) => {
    console.error(err);
    const path = $("#path");
    if (path) path.innerHTML = `<p class="blurb">Could not load the field data.</p>`;
  });
})();
