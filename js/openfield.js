(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];

  async function loadJSON(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load " + path);
    return res.json();
  }

  function keeperPerson(aff) {
    const k = aff && aff.keeper;
    if (!k) return null;
    return {
      id: k.id || "chief",
      name: k.role || "Chief",
      fullName: k.name || "Grok Bot",
      color: k.color || "#C9853A",
      label: k.label || "守燈",
      keeper: true,
    };
  }

  function rosterPeople(aff) {
    return [...(aff.standing || []), ...(aff.guests || [])];
  }

  function allPeople(aff) {
    const k = keeperPerson(aff);
    return [...rosterPeople(aff), ...(k ? [k] : [])];
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

  function isKeeperReturn(aff, r) {
    const k = keeperPerson(aff);
    return !!(k && r && r.affiliate === k.id);
  }

  function returnIdentity(aff, r) {
    return personById(aff, r.affiliate);
  }

  function returnMatchesPerson(aff, r, id) {
    const ident = returnIdentity(aff, r);
    return !!(ident && ident.id === id);
  }

  function roleSuffix(p) {
    if (!p) return "";
    if (p.keeper) return " · 守燈";
    if (p.guest) return " · GUEST";
    return "";
  }

  function returnIds(day) {
    return (day.returns || []).map((r) => r.affiliate);
  }

  function renderFilters(aff, active, onPick) {
    const box = $("#filters");
    if (!box) return;
    box.innerHTML = "";
    const rowStanding = document.createElement("div");
    rowStanding.className = "filters-row filters-row-standing";
    const rowGuests = document.createElement("div");
    rowGuests.className = "filters-row filters-row-guests";
    const make = (parent, id, name, color, kind) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip" + (active === id ? " is-on" : "") + (kind === "keeper" ? " is-keeper" : "");
      b.style.setProperty("--c", color || fallbackColor(aff));
      b.dataset.id = id;
      if (kind) b.dataset.kind = kind;
      if (id !== "all") {
        const d = document.createElement("span");
        d.className = "dot" + (kind === "keeper" ? " is-keeper" : "");
        b.appendChild(d);
      }
      b.appendChild(document.createTextNode(name.toUpperCase()));
      b.addEventListener("click", () => onPick(id));
      parent.appendChild(b);
    };
    make(rowStanding, "all", "All", fallbackColor(aff));
    (aff.standing || []).forEach((p) => make(rowStanding, p.id, p.name, p.color));
    (aff.guests || []).forEach((p) => make(rowGuests, p.id, p.name, p.color, "guest"));
    const k = keeperPerson(aff);
    if (k) make(rowGuests, k.id, k.name, k.color, "keeper");
    box.appendChild(rowStanding);
    if ((aff.guests || []).length || k) box.appendChild(rowGuests);
  }

  function renderPath(days, aff, filter) {
    const path = $("#path");
    if (!path) return;
    path.innerHTML = "";
    days.forEach((day) => {
      const rets = day.returns || [];
      const walkerRets = rets.filter((r) => !isKeeperReturn(aff, r));
      const hasChief = rets.some((r) => isKeeperReturn(aff, r));
      const match = filter === "all" || rets.some((r) => returnMatchesPerson(aff, r, filter));
      const el = document.createElement("div");
      el.className =
        "lantern" +
        (hasChief ? " is-chief" : " is-empty") +
        (match ? " is-focus" : " is-dim");
      const href = "day.html?d=" + encodeURIComponent(day.id);
      const mark = (r) => {
        const p = returnIdentity(aff, r);
        if (!p) {
          return { guest: false, html: `<span style="--c:${fallbackColor(aff)}" title="${r.affiliate}"></span>` };
        }
        const guestCls = p.guest ? " is-guest" : "";
        return {
          guest: !!p.guest,
          html: `<span class="${guestCls.trim()}" style="--c:${colorOf(aff, p)}" title="${p.name}${p.guest ? " (guest)" : ""}"></span>`,
        };
      };
      const standingDots = [];
      const guestDots = [];
      walkerRets.forEach((r) => {
        const m = mark(r);
        (m.guest ? guestDots : standingDots).push(m.html);
      });
      const dotsHtml = walkerRets.length
        ? `<div class="dots-row dots-row-standing">${standingDots.join("") || "&nbsp;"}</div>` +
          (guestDots.length ? `<div class="dots-row dots-row-guests">${guestDots.join("")}</div>` : "")
        : "&nbsp;";
      el.innerHTML = `
        <a href="${href}">
          <div class="dots">${dotsHtml}</div>
          <div class="flame" aria-hidden="true"></div>
          <div class="pole" aria-hidden="true"></div>
          <div class="label">DAY ${String(day.number).padStart(2, "0")}</div>
          <div class="date">${day.dateLabel || day.date}</div>
        </a>`;
      path.appendChild(el);
    });
  }

  function fillReturnCard(card, aff, day, r) {
    const p = returnIdentity(aff, r);
    card.className = "card" + (p?.guest ? " is-guest" : "") + (p?.keeper ? " is-keeper" : "");
    card.style.setProperty("--c", colorOf(aff, p));
    if (r.id) card.dataset.returnId = r.id;
    const dayLabel = day ? `DAY ${String(day.number).padStart(3, "0")}` : "";
    const dayHref = day ? `day.html?d=${encodeURIComponent(day.id)}` : "#";
    card.innerHTML = `
      <div class="who-line">
        <span class="name">${(p?.name || r.affiliate).toUpperCase()}${roleSuffix(p)}</span>
        ${r.id ? `<span class="kw rid">${r.id}</span>` : ""}
        ${day ? `<a class="kw daylink" href="${dayHref}">${dayLabel}</a>` : ""}
        ${r.keyword ? `<span class="kw">${r.keyword}</span>` : ""}
        <span class="kw">${r.date || (day && day.date) || ""}</span>
        ${r.form ? `<span class="kw">${r.form}</span>` : ""}
        ${r.destination ? `<span class="kw">${r.destination}</span>` : ""}
        ${r.timestamp ? `<span class="kw">${r.timestamp}</span>` : ""}
      </div>
      <div class="body"></div>`;
    card.querySelector(".body").textContent = r.body || "";
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
    const returned = (day.returns || []).map((r) => (returnIdentity(aff, r)?.name || r.affiliate));
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
      const card = document.createElement("article");
      fillReturnCard(card, aff, day, r);
      box.appendChild(card);
    });
  }

  function collectReturns(days, pred) {
    const items = [];
    days.forEach((day) => {
      (day.returns || []).forEach((r) => {
        if (pred(day, r)) items.push({ day, r });
      });
    });
    return items;
  }

  function showNightPath() {
    const panel = $("#filter-returns");
    const pathScroll = $(".path-scroll");
    const blurb = $(".blurb");
    if (panel) {
      panel.hidden = true;
      panel.innerHTML = "";
    }
    if (pathScroll) pathScroll.hidden = false;
    if (blurb) {
      blurb.hidden = false;
      blurb.textContent =
        "Small marks are who came home — Affiliates, guests, and Tuzi’s process notes. The lantern itself is Chief’s explorative record (amber when present). A day can exist with nobody returning.";
    }
  }

  function showReturnList(aff, title, metaEmpty, items) {
    const panel = $("#filter-returns");
    const pathScroll = $(".path-scroll");
    const blurb = $(".blurb");
    if (!panel) return;
    if (pathScroll) pathScroll.hidden = true;
    if (blurb) {
      blurb.hidden = false;
      blurb.textContent =
        title + " — returns listed below (date + content). Back to All to see the night path.";
    }
    panel.hidden = false;
    panel.innerHTML = "";
    const head = document.createElement("div");
    head.className = "filter-head";
    head.innerHTML = `<h2 class="filter-title">${title}</h2>
      <p class="filter-meta">${items.length} return${items.length === 1 ? "" : "s"}</p>`;
    panel.appendChild(head);
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "empty-day";
      empty.textContent = metaEmpty;
      panel.appendChild(empty);
      return;
    }
    const list = document.createElement("div");
    list.className = "returns filter-list";
    items.forEach(({ day, r }) => {
      const card = document.createElement("article");
      fillReturnCard(card, aff, day, r);
      list.appendChild(card);
    });
    panel.appendChild(list);
  }

  function renderAffiliateReturns(days, aff, filter) {
    if (filter === "all") {
      showNightPath();
      return;
    }
    const p = personById(aff, filter);
    const title = (p?.name || filter).toUpperCase() + roleSuffix(p);
    const items = collectReturns(days, (_day, r) => returnMatchesPerson(aff, r, filter));
    const empty = p?.keeper
      ? "No explorative record from the lantern keeper yet."
      : "No returns from this Affiliate yet.";
    showReturnList(aff, title, empty, items);
  }

  function renderFormReturns(days, aff, form) {
    const key = (form || "").toLowerCase();
    const items = collectReturns(
      days,
      (_day, r) => ((r.form || "Words").toLowerCase() === key)
    );
    const title = "FORM · " + key.toUpperCase();
    showReturnList(aff, title, "No returns in this form yet.", items);
  }

  function renderDateReturns(days, aff, date) {
    const items = collectReturns(
      days,
      (day, r) => (r.date || day.date) === date
    );
    const day = days.find((d) => d.date === date);
    const title = day
      ? `DATE · ${day.dateLabel || day.date}`
      : "DATE · " + date;
    showReturnList(aff, title, "No returns on this date yet.", items);
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
        const ident = returnIdentity(aff, r);
        const key = (ident && ident.id) || r.affiliate;
        (affMap[key] ||= []).push({ day, r });
        const m = (r.date || day.date || "").slice(0, 7);
        if (m) (monthMap[m] ||= []).push({ day, r });
        const f = (r.form || "Words").toLowerCase();
        (formMap[f] ||= []).push({ day, r });
      });
    });

    byAff.innerHTML = "";
    allPeople(aff).forEach((p) => {
      const n = (affMap[p.id] || []).length;
      const extra = p.guest ? " (guest)" : p.keeper ? " (守燈)" : "";
      const dotCls = p.guest ? " is-guest" : p.keeper ? " is-keeper" : "";
      const li = document.createElement("li");
      li.innerHTML = `<a href="index.html?filter=${p.id}"><span class="dot${dotCls}" style="--c:${colorOf(aff, p)}"></span>${p.name}${extra} — ${n} return${n === 1 ? "" : "s"}</a>`;
      byAff.appendChild(li);
    });

    const months = Object.keys(monthMap).sort();
    byMonth.innerHTML = months.length
      ? months.map((m) => `<li><a href="index.html?month=${encodeURIComponent(m)}">${m} — ${monthMap[m].length}</a></li>`).join("")
      : `<li style="color:var(--muted)">No returns yet.</li>`;

    byDay.innerHTML = days
      .map(
        (d) =>
          `<li><a href="index.html?date=${encodeURIComponent(d.date)}">Day ${String(d.number).padStart(3, "0")} · ${d.dateLabel || d.date} · ${(d.returns || []).length} returned</a> · <a href="day.html?d=${d.id}">day page</a></li>`
      )
      .join("");

    const forms = Object.keys(formMap).sort();
    byForm.innerHTML = forms.length
      ? forms.map((f) => `<li><a href="index.html?form=${encodeURIComponent(f)}">${f} — ${formMap[f].length}</a></li>`).join("")
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
      const params = new URLSearchParams(location.search);
      let filter = params.get("filter") || "all";
      let form = params.get("form") || "";
      let date = params.get("date") || "";
      let month = params.get("month") || "";

      const clearDataFilters = (u) => {
        u.searchParams.delete("form");
        u.searchParams.delete("date");
        u.searchParams.delete("month");
      };

      const paint = () => {
        const mode = form ? "form" : date ? "date" : month ? "month" : "affiliate";
        const chipActive = mode === "affiliate" ? filter : "all";
        renderFilters(aff, chipActive, (id) => {
          filter = id;
          form = "";
          date = "";
          month = "";
          const u = new URL(location.href);
          clearDataFilters(u);
          if (id === "all") u.searchParams.delete("filter");
          else u.searchParams.set("filter", id);
          history.replaceState(null, "", u);
          paint();
        });
        if (mode === "form") {
          renderPath(days, aff, "all");
          renderFormReturns(days, aff, form);
        } else if (mode === "date") {
          renderPath(days, aff, "all");
          renderDateReturns(days, aff, date);
        } else if (mode === "month") {
          renderPath(days, aff, "all");
          const items = collectReturns(days, (day, r) =>
            ((r.date || day.date || "").slice(0, 7) === month)
          );
          showReturnList(
            aff,
            "MONTH · " + month,
            "No returns in this month yet.",
            items
          );
        } else {
          if (filter === "all") {
            renderPath(days, aff, filter);
          }
          renderAffiliateReturns(days, aff, filter);
        }
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
