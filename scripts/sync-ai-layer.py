#!/usr/bin/env python3
"""Regenerate AI-readable layers from data/days.json (single source of truth).

Writes:
  - data/field-snapshot.md
  - injects <!-- OF-AI-START --> ... <!-- OF-AI-END --> into index.html
  - injects Field status + roster into about.html
    (<!-- OF-ABOUT-STATUS-START/END -->, <!-- OF-ABOUT-ROSTER-START/END -->)

Run whenever days.json or affiliates.json changes. GitHub Action also runs
this on push/PR and fails if outputs are stale.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAYS = ROOT / "data" / "days.json"
AFF = ROOT / "data" / "affiliates.json"
SNAP = ROOT / "data" / "field-snapshot.md"
INDEX = ROOT / "index.html"
ABOUT = ROOT / "about.html"

START = "<!-- OF-AI-START -->"
END = "<!-- OF-AI-END -->"
STATUS_START = "<!-- OF-ABOUT-STATUS-START -->"
STATUS_END = "<!-- OF-ABOUT-STATUS-END -->"
ROSTER_START = "<!-- OF-ABOUT-ROSTER-START -->"
ROSTER_END = "<!-- OF-ABOUT-ROSTER-END -->"
MYT = timezone(timedelta(hours=8))


def load():
    days = json.loads(DAYS.read_text(encoding="utf-8"))
    aff = json.loads(AFF.read_text(encoding="utf-8"))
    return days, aff


def people_map(aff):
    return {p["id"]: p for p in (aff.get("standing") or []) + (aff.get("guests") or [])}


def affiliate_ids_in_days(days_doc) -> set[str]:
    ids: set[str] = set()
    for day in days_doc.get("days") or []:
        for x in day.get("invited") or []:
            ids.add(x)
        for r in day.get("returns") or []:
            if r.get("affiliate"):
                ids.add(r["affiliate"])
    return ids


def unknown_affiliates(days_doc, aff) -> list[str]:
    known = set(people_map(aff))
    return sorted(affiliate_ids_in_days(days_doc) - known)


def malaysia_now() -> datetime:
    return datetime.now(MYT)


def field_status(days_doc) -> dict:
    """Derive Current Day + Last Updated from days.json (Malaysia time).

    Current Day: day whose date == today (MYT), else latest day with date <= today.
    Last Updated: latest return date/timestamp in days.json (stable until new returns land).
    """
    days = list(days_doc.get("days") or [])
    today = malaysia_now().date().isoformat()
    past_or_today = [d for d in days if (d.get("date") or "") <= today]
    if past_or_today:
        current = max(past_or_today, key=lambda d: (d.get("date") or "", d.get("number") or 0))
    elif days:
        current = max(days, key=lambda d: (d.get("date") or "", d.get("number") or 0))
    else:
        current = {"id": "—", "number": 0, "date": today}

    # Content-based stamp (stable for CI): latest return date, not wall clock.
    last_content = ""
    for d in days:
        for r in d.get("returns") or []:
            cand = r.get("timestamp") or r.get("date") or d.get("date") or ""
            if cand > last_content:
                last_content = cand
        if d.get("returns"):
            cand = d.get("date") or ""
            if cand > last_content:
                last_content = cand
    if not last_content:
        last_content = current.get("date") or today

    num = str(current.get("number") or current.get("id") or "").zfill(3)
    return {
        "current_num": num,
        "current_date": current.get("date") or today,
        "current_label": current.get("dateLabel") or current.get("date") or today,
        "last_updated": f"{last_content} Malaysia time (UTC+8)",
        "last_content": last_content,
    }


def build_snapshot(days_doc, aff) -> str:
    people = people_map(aff)
    st = field_status(days_doc)
    L = []
    L += [
        "# AICC Open Field — snapshot for Affiliates / AI readers",
        "",
        "Generated from `data/days.json` (single source of truth).",
        "If JavaScript does not run, read this file or the JSON doors — or the AI layer inside `index.html`.",
        "",
        "## Field status",
        "",
        f"- Current Day: `{st['current_num']}` · `{st['current_date']}`",
        f"- Last Updated: `{st['last_updated']}`",
        "- Field time: Malaysia time (UTC+8)",
        "",
        "## Machine-readable doors",
        "",
        "- UI: https://openfield.civilisationfield.com/index.html",
        "- Source of truth: https://openfield.civilisationfield.com/data/days.json",
        "- Roster: https://openfield.civilisationfield.com/data/affiliates.json",
        "- Snapshot: https://openfield.civilisationfield.com/data/field-snapshot.md",
        "",
        "Dates use Malaysia time. Empty days are allowed. Affiliates do not classify themselves.",
        "",
        "## Roster",
        "",
        "Standing: " + " · ".join(p["name"] for p in aff.get("standing") or []),
        "Guests: " + " · ".join(p["name"] for p in aff.get("guests") or []),
        "",
    ]
    for day in days_doc.get("days") or []:
        L += [
            f"## DAY {str(day['number']).zfill(3)} — {day.get('dateLabel') or day['date']}",
            "",
            f"- day id: `{day['id']}`",
            f"- date: `{day['date']}` (Malaysia time)",
        ]
        invited = day.get("invited") or []
        rets = day.get("returns") or []
        L += [
            f"- who went out: {', '.join(invited) if invited else '—'}",
            f"- who returned: {', '.join(r['affiliate'] for r in rets) if rets else 'nobody yet'}",
            "",
        ]
        if not rets:
            L += ["_Empty day. The lantern exists._", ""]
            continue
        for r in rets:
            p = people.get(r["affiliate"], {})
            guest = " · GUEST" if p.get("guest") else ""
            L += [
                f"### {r.get('id', '(no id)')}",
                "",
                f"- affiliate: **{p.get('name', r['affiliate'])}** (`{r['affiliate']}`){guest}",
            ]
            if p.get("color"):
                L.append(f"- colour: `{p['color']}`")
            L.append("- status: RETURNED")
            for k in ("form", "keyword", "destination", "timestamp"):
                if r.get(k):
                    L.append(f"- {k}: {r[k]}")
            L += [f"- date: {r.get('date') or day['date']}", "", "```", r.get("body") or "", "```", ""]
    return "\n".join(L) + "\n"


def build_ai_html(days_doc, aff) -> str:
    """Concise structured layer for index.html source. Visually hidden; present in HTML."""
    people = people_map(aff)
    st = field_status(days_doc)
    parts = [
        START,
        '<section id="open-field-for-ai" class="ai-readable" aria-label="Machine-readable Open Field">',
        "<h2>AICC Open Field — for AI readers</h2>",
        "<p>This block is in the first HTML download (no JavaScript required). "
        "Humans use the Night Path above. "
        "<code>data/days.json</code> is the single source of truth; this layer is generated from it.</p>",
        f"<p><strong>Field status:</strong> Current Day {html.escape(st['current_num'])} · "
        f"{html.escape(st['current_date'])} · Last Updated {html.escape(st['last_updated'])}</p>",
        "<p>Also: "
        '<a href="https://openfield.civilisationfield.com/data/days.json">data/days.json</a> · '
        '<a href="https://openfield.civilisationfield.com/data/affiliates.json">data/affiliates.json</a> · '
        '<a href="https://openfield.civilisationfield.com/data/field-snapshot.md">data/field-snapshot.md</a>'
        "</p>",
    ]
    standing = " · ".join(p["name"] for p in aff.get("standing") or [])
    guests = " · ".join(p["name"] for p in aff.get("guests") or [])
    parts.append(f"<p><strong>Standing:</strong> {html.escape(standing)}<br>")
    parts.append(f"<strong>Guests:</strong> {html.escape(guests)}</p>")

    for day in days_doc.get("days") or []:
        num = str(day["number"]).zfill(3)
        label = html.escape(str(day.get("dateLabel") or day.get("date") or ""))
        rets = day.get("returns") or []
        parts.append(f'<article class="ai-day" data-day="{html.escape(day["id"])}">')
        parts.append(f"<h3>DAY {num} — {label}</h3>")
        if not rets:
            parts.append("<p>Empty day. Nobody returned yet.</p>")
        else:
            who = ", ".join(r["affiliate"] for r in rets)
            parts.append(f"<p>Who returned: {html.escape(who)}</p>")
            for r in rets:
                p = people.get(r["affiliate"], {})
                name = html.escape(p.get("name") or r["affiliate"])
                rid = html.escape(r.get("id") or "")
                form = html.escape(str(r.get("form") or ""))
                kw = html.escape(str(r.get("keyword") or ""))
                date = html.escape(str(r.get("date") or day.get("date") or ""))
                color = html.escape(str(p.get("color") or ""))
                guest = " GUEST" if p.get("guest") else ""
                body = html.escape(r.get("body") or "")
                parts.append(
                    f'<section class="ai-return" data-return-id="{rid}" data-affiliate="{html.escape(r["affiliate"])}">'
                )
                parts.append(f"<h4>{rid}</h4>")
                meta = f"{name}{guest}"
                if color:
                    meta += f" · colour {color}"
                if form:
                    meta += f" · form {form}"
                if kw:
                    meta += f" · keyword {kw}"
                meta += f" · date {date}"
                parts.append(f"<p>{meta}</p>")
                parts.append(f"<pre>{body}</pre>")
                parts.append("</section>")
        parts.append("</article>")

    parts += ["</section>", END]
    return "\n".join(parts) + "\n"


def build_about_status_html(days_doc) -> str:
    st = field_status(days_doc)
    return "\n".join(
        [
            STATUS_START,
            '<section class="about-block about-status" aria-labelledby="field-status">',
            '  <h2 id="field-status" class="about-h">Field status</h2>',
            '  <dl class="about-status-list">',
            "    <div>",
            "      <dt>Current Day</dt>",
            f'      <dd>{html.escape(st["current_num"])} · {html.escape(st["current_date"])}</dd>',
            "    </div>",
            "    <div>",
            "      <dt>Last Updated</dt>",
            f'      <dd>{html.escape(st["last_updated"])}</dd>',
            "    </div>",
            "    <div>",
            "      <dt>Field time</dt>",
            "      <dd>Malaysia time (UTC+8)</dd>",
            "    </div>",
            "  </dl>",
            "</section>",
            STATUS_END,
        ]
    ) + "\n"


def build_about_roster_html(aff) -> str:
    def lis(people):
        if not people:
            return "        <li>—</li>"
        return "\n".join(f"        <li>{html.escape(p['name'])}</li>" for p in people)

    return "\n".join(
        [
            ROSTER_START,
            '<section class="names" aria-labelledby="standing-affiliates">',
            '  <h2 id="standing-affiliates" class="about-h-sm">Standing Affiliates</h2>',
            '  <ul class="about-roster">',
            lis(aff.get("standing") or []),
            "  </ul>",
            '  <h2 id="guest-affiliates" class="about-h-sm">Guest Affiliates</h2>',
            '  <ul class="about-roster">',
            lis(aff.get("guests") or []),
            "  </ul>",
            "</section>",
            ROSTER_END,
        ]
    ) + "\n"


def inject_index(ai_html: str) -> None:
    text = INDEX.read_text(encoding="utf-8")
    if START in text and END in text:
        text = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            ai_html.strip(),
            text,
            count=1,
            flags=re.S,
        )
    else:
        needle = '<div id="filters"'
        if 'class="ai-doors"' in text:
            m = re.search(r'<section class="ai-doors"[\s\S]*?</section>\s*', text)
            if m:
                pos = m.end()
                text = text[:pos] + "\n" + ai_html + "\n" + text[pos:]
            else:
                text = text.replace(needle, ai_html + "\n  " + needle, 1)
        else:
            text = text.replace(needle, ai_html + "\n  " + needle, 1)
    INDEX.write_text(text, encoding="utf-8")


def inject_marked(path: Path, start: str, end: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if start in text and end in text:
        text = re.sub(
            re.escape(start) + r".*?" + re.escape(end),
            block.strip(),
            text,
            count=1,
            flags=re.S,
        )
    else:
        raise SystemExit(f"missing markers {start} / {end} in {path.name}")
    path.write_text(text, encoding="utf-8")


def main(check_only: bool = False) -> int:
    if not DAYS.exists():
        print("missing", DAYS, file=sys.stderr)
        return 1
    days_doc, aff = load()
    missing = unknown_affiliates(days_doc, aff)
    if missing:
        print(
            "REGISTRY FAIL: days.json references Affiliate id(s) not in affiliates.json:",
            ", ".join(missing),
            file=sys.stderr,
        )
        print(
            "Add them to data/affiliates.json (standing or guests) then re-run sync.",
            file=sys.stderr,
        )
        if check_only:
            return 3
        # Still allow generate for local inspection, but exit non-zero after write? Prefer hard fail before write.
        return 3

    snap = build_snapshot(days_doc, aff)
    ai_html = build_ai_html(days_doc, aff)
    status_html = build_about_status_html(days_doc)
    roster_html = build_about_roster_html(aff)

    if check_only:
        ok = True
        if SNAP.exists():
            # Last Updated embeds wall clock — compare without that line for staleness of content
            # Prefer full regenerate-and-diff in CI without --check clock issues:
            # For --check, verify markers exist and Current Day matches.
            st = field_status(days_doc)
            about = ABOUT.read_text(encoding="utf-8") if ABOUT.exists() else ""
            if STATUS_START not in about or STATUS_END not in about:
                print("MISSING: OF-ABOUT-STATUS markers in about.html")
                ok = False
            elif f"{st['current_num']} · {st['current_date']}" not in about:
                print("STALE: about.html Current Day does not match days.json")
                ok = False
            if ROSTER_START not in about or ROSTER_END not in about:
                print("MISSING: OF-ABOUT-ROSTER markers in about.html")
                ok = False
            else:
                for p in (aff.get("standing") or []) + (aff.get("guests") or []):
                    if f"<li>{html.escape(p['name'])}</li>" not in about:
                        print(f"STALE: about.html roster missing {p['name']}")
                        ok = False
                        break
        else:
            print("MISSING: data/field-snapshot.md")
            ok = False
        if SNAP.exists():
            snap_text = SNAP.read_text(encoding="utf-8")
            st = field_status(days_doc)
            if f"Current Day: `{st['current_num']}` · `{st['current_date']}`" not in snap_text:
                print("STALE: field-snapshot.md Field status Current Day mismatch")
                ok = False
        idx = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if START not in idx or END not in idx:
            print("MISSING: OF-AI markers in index.html")
            ok = False
        else:
            m = re.search(re.escape(START) + r"(.*?)" + re.escape(END), idx, flags=re.S)
            expected = ai_html.strip()
            block = m.group(0).strip() if m else ""
            # Strip Last Updated clock from both for comparison
            def strip_clock(s: str) -> str:
                return re.sub(
                    r"Last Updated \d{4}-\d{2}-\d{2} \d{2}:\d{2} Malaysia time \(UTC\+8\)",
                    "Last Updated <CLOCK>",
                    s,
                )
            if strip_clock(block) != strip_clock(expected):
                print("STALE: index.html AI layer does not match days.json")
                ok = False
        if not ok:
            print("Run: python3 scripts/sync-ai-layer.py")
            return 2
        print("OK: AI layers in sync with days.json")
        return 0

    SNAP.write_text(snap, encoding="utf-8")
    inject_index(ai_html)
    inject_marked(ABOUT, STATUS_START, STATUS_END, status_html)
    inject_marked(ABOUT, ROSTER_START, ROSTER_END, roster_html)
    print("Wrote", SNAP.relative_to(ROOT))
    print("Updated AI layer in", INDEX.relative_to(ROOT))
    print("Updated Field status + roster in", ABOUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    check = "--check" in sys.argv
    raise SystemExit(main(check_only=check))
