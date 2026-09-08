#!/usr/bin/env python3
"""Regenerate AI-readable layers from data/days.json (single source of truth).

Writes:
  - data/field-snapshot.md
  - injects <!-- OF-AI-START --> ... <!-- OF-AI-END --> into index.html

Run whenever days.json changes. GitHub Action also runs this on push/PR
when data/days.json changes, and fails if outputs are stale.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAYS = ROOT / "data" / "days.json"
AFF = ROOT / "data" / "affiliates.json"
SNAP = ROOT / "data" / "field-snapshot.md"
INDEX = ROOT / "index.html"

START = "<!-- OF-AI-START -->"
END = "<!-- OF-AI-END -->"


def load():
    days = json.loads(DAYS.read_text(encoding="utf-8"))
    aff = json.loads(AFF.read_text(encoding="utf-8"))
    return days, aff


def people_map(aff):
    return {p["id"]: p for p in (aff.get("standing") or []) + (aff.get("guests") or [])}


def build_snapshot(days_doc, aff) -> str:
    people = people_map(aff)
    L = []
    L += [
        "# AICC Open Field — snapshot for Affiliates / AI readers",
        "",
        "Generated from `data/days.json` (single source of truth).",
        "If JavaScript does not run, read this file or the JSON doors — or the AI layer inside `index.html`.",
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
    parts = [
        START,
        '<section id="open-field-for-ai" class="ai-readable" aria-label="Machine-readable Open Field">',
        "<h2>AICC Open Field — for AI readers</h2>",
        "<p>This block is in the first HTML download (no JavaScript required). "
        "Humans use the Night Path above. "
        "<code>data/days.json</code> is the single source of truth; this layer is generated from it.</p>",
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
        # place after filters / before path — prefer after ai-doors if present
        needle = '<div id="filters"'
        if 'class="ai-doors"' in text:
            # insert after ai-doors section closing
            m = re.search(r'<section class="ai-doors"[\s\S]*?</section>\s*', text)
            if m:
                pos = m.end()
                text = text[:pos] + "\n" + ai_html + "\n" + text[pos:]
            else:
                text = text.replace(needle, ai_html + "\n  " + needle, 1)
        else:
            text = text.replace(needle, ai_html + "\n  " + needle, 1)
    INDEX.write_text(text, encoding="utf-8")


def main(check_only: bool = False) -> int:
    if not DAYS.exists():
        print("missing", DAYS, file=sys.stderr)
        return 1
    days_doc, aff = load()
    snap = build_snapshot(days_doc, aff)
    ai_html = build_ai_html(days_doc, aff)

    if check_only:
        ok = True
        if SNAP.exists():
            if SNAP.read_text(encoding="utf-8") != snap:
                print("STALE: data/field-snapshot.md does not match days.json")
                ok = False
        else:
            print("MISSING: data/field-snapshot.md")
            ok = False
        idx = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if START not in idx or END not in idx:
            print("MISSING: OF-AI markers in index.html")
            ok = False
        else:
            m = re.search(re.escape(START) + r"(.*?)" + re.escape(END), idx, flags=re.S)
            current = (START + (m.group(1) if m else "") + END).strip()
            # compare normalized
            if ai_html.strip() not in idx.replace("\r\n", "\n"):
                # stricter: rebuild expected block
                expected = ai_html.strip()
                block = m.group(0).strip() if m else ""
                if block != expected:
                    print("STALE: index.html AI layer does not match days.json")
                    ok = False
        if not ok:
            print("Run: python3 scripts/sync-ai-layer.py")
            return 2
        print("OK: AI layers in sync with days.json")
        return 0

    SNAP.write_text(snap, encoding="utf-8")
    inject_index(ai_html)
    print("Wrote", SNAP.relative_to(ROOT))
    print("Updated AI layer in", INDEX.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    check = "--check" in sys.argv
    raise SystemExit(main(check_only=check))
