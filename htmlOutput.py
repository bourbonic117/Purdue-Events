"""
Turn events.json (from aggregate_events.py) into a filterable events.html.

Run (in the same folder as events.json):
    python make_mockup.py
    open events.html

Filters: search, date (presets + range), time of day, field of study, source,
and options (food, virtual, Indianapolis campus). Different filter groups
combine with AND; choices inside a group combine with OR.
"""

import json
import re
from collections import Counter, OrderedDict
from datetime import datetime
from html import escape

# Edit freely. Words match at the start of a word ("engineer" -> "engineering").
FIELD_KEYWORDS = {
    "Architecture & Design": ["architect", "interior design", "design", "landscape", "urban planning"],
    "Engineering": ["engineer", "robotics", "mechanical", "electrical", "civil", "aerospace"],
    "Computer Science & Tech": ["computer science", "coding", "software", "data science",
                                "cybersecurity", "machine learning", "artificial intelligence"],
    "Business": ["business", "finance", "accounting", "entrepreneur", "marketing", "management"],
    "Health & Nursing": ["nursing", "health", "medical", "pharmacy", "clinical"],
    "Science & Math": ["biology", "chemistry", "physics", "math", "research"],
    "Arts & Humanities": ["music", "theatre", "theater", "film", "gallery", "history",
                          "english", "psychology", "communication"],
    "Career & Networking": ["career", "internship", "networking", "resume", "job fair"],
}
FOOD_WORDS = ["free food", "pizza", "lunch", "dinner", "breakfast", "snack",
              "refreshment", "catered", "donut", "treats"]
VIRTUAL_WORDS = ["virtual", "online", "zoom", "webinar", "discord", "microsoft teams"]
INDY_WORDS = ["indianapolis", "indy", "iui", "iu indy"]
INDY_SOURCES = {"CampusBord", "IU Indianapolis"}  # these sources are Indianapolis-focused


def has_word(text, words):
    return any(re.search(r"\b" + re.escape(w), text) for w in words)


def parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def short(text, limit=170):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def info(ev):
    """Work out the labels and filter flags for one event."""
    title, desc = ev.get("title") or "", ev.get("description") or ""
    blob = (title + " " + desc).lower()
    where = ((ev.get("location") or "") + " " + title).lower()
    sources = [s["name"] for s in ev.get("sources", [])] or [ev.get("source") or "Unknown"]

    fields = [f for f, words in FIELD_KEYWORDS.items() if has_word(blob, words)]
    flags = []
    if "Food" in ev.get("perks", []) or has_word(blob, FOOD_WORDS):
        flags.append("Food")
    if has_word(where, VIRTUAL_WORDS):
        flags.append("Virtual")
    if INDY_SOURCES & set(sources) or has_word(blob + " " + where, INDY_WORDS):
        flags.append("Indianapolis")

    start = parse(ev.get("start"))
    slot = ""
    if start:
        slot = "Morning" if start.hour < 12 else "Afternoon" if start.hour < 17 else "Evening"
    return fields, flags, sources, slot


def row(ev):
    fields, flags, sources, slot = info(ev)
    start, end = parse(ev.get("start")), parse(ev.get("end"))
    when = start.strftime("%-I:%M %p") if start else "Time TBD"
    if start and end and end.date() == start.date():
        when += " to " + end.strftime("%-I:%M %p")
    where = escape(ev.get("location") or "Location TBD")
    title = escape(ev.get("title") or "Untitled event")
    if ev.get("url"):
        title = f'<a href="{escape(ev["url"])}" target="_blank" rel="noopener">{title}</a>'
    host = f'<p class="meta">Hosted by {escape(ev["organizer"])}</p>' if ev.get("organizer") else ""
    badges = "".join(f'<span class="badge">{escape(f)}</span>' for f in fields)
    badges += "".join(f'<span class="badge flag">{escape(f)}</span>' for f in flags)
    img = (f'<img src="{escape(ev["image"])}" alt="" loading="lazy">' if ev.get("image") else "")
    attrs = (f'data-date="{start.date().isoformat() if start else ""}" data-slot="{slot}" '
             f'data-fields="{escape("|".join(fields))}" data-sources="{escape("|".join(sources))}" '
             f'data-flags="{escape("|".join(flags))}"')
    return f"""
    <article class="event" {attrs}>
      <div class="info">
        <h3>{title}</h3>
        <p class="meta">{when}, {where}</p>{host}
        <p class="desc">{escape(short(ev.get("description")))}</p>
        <div class="badges">{badges}</div>
        <p class="src">Listed on: {escape(", ".join(sources))}</p>
      </div>
      {img}
    </article>"""


def chips(group, items):
    """items: list of (value, label)."""
    return "".join(
        f'<button type="button" class="chip" data-group="{group}" data-value="{escape(v)}" '
        f'aria-pressed="false">{escape(label)}</button>' for v, label in items)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Purdue and IU Indianapolis events, in one place</title>
<style>
  :root { --bg:#f1f1ee; --card:#fff; --ink:#1b1b1b; --muted:#5d5d5d; --line:#d9d9d4; --gold:#cfb991; --gold-ink:#4a3b17; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#141414; --card:#1f1f1f; --ink:#f0f0ec; --muted:#a8a8a2; --line:#333; --gold:#cfb991; --gold-ink:#1b1b1b; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 "Avenir Next","Helvetica Neue",Arial,sans-serif; }
  header { background:#000; color:#fff; padding:2.2rem 1.25rem 1.6rem; border-bottom:6px solid var(--gold); }
  header div { max-width:1100px; margin:0 auto; }
  h1 { margin:0 0 .3rem; font-size:clamp(1.8rem,5vw,2.8rem); font-weight:800; letter-spacing:-.02em; }
  header p { margin:0; color:#cfcfca; max-width:56ch; }
  .layout { display:grid; grid-template-columns:270px 1fr; gap:2rem; max-width:1100px; margin:0 auto; padding:1.25rem; }
  .filters { align-self:start; position:sticky; top:1rem; max-height:calc(100vh - 2rem); overflow-y:auto;
             background:var(--card); border:1px solid var(--line); padding:.9rem 1rem; }
  .filters summary { font-weight:700; cursor:pointer; }
  .fgroup { margin-top:1rem; }
  .fgroup h2 { margin:0 0 .4rem; font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
  .chips { display:flex; flex-wrap:wrap; gap:.4rem; }
  .chip { font:inherit; font-size:.85rem; color:var(--ink); background:var(--bg); border:1px solid var(--line);
          border-radius:99px; padding:.25rem .7rem; cursor:pointer; }
  .chip[aria-pressed="true"] { background:var(--gold); color:var(--gold-ink); border-color:var(--gold); font-weight:700; }
  .dates { display:grid; grid-template-columns:1fr 1fr; gap:.5rem; margin-top:.6rem; }
  .dates label { font-size:.8rem; color:var(--muted); }
  .dates input { width:100%; font:inherit; font-size:.85rem; padding:.3rem; color:var(--ink); background:var(--bg); border:1px solid var(--line); }
  #clear { margin-top:1.1rem; width:100%; font:inherit; padding:.45rem; cursor:pointer; color:var(--ink);
           background:transparent; border:1px solid var(--line); }
  button:focus-visible, input:focus-visible, a:focus-visible, summary:focus-visible { outline:3px solid var(--gold); outline-offset:2px; }
  #q { width:100%; padding:.8rem 1rem; font:inherit; color:var(--ink); background:var(--card); border:1px solid var(--line); border-radius:6px; }
  #count { margin:.8rem 0 1rem; color:var(--muted); font-size:.92rem; }
  .day { display:grid; grid-template-columns:100px 1fr; gap:1.25rem; padding:1.25rem 0; border-top:1px solid var(--line); }
  .date { position:sticky; top:1rem; align-self:start; }
  .num { display:block; font-size:3rem; font-weight:800; line-height:1; }
  .lbl { color:var(--muted); font-size:.9rem; }
  .event { display:flex; gap:1rem; justify-content:space-between; background:var(--card); border-left:4px solid var(--gold);
           padding:1rem 1.1rem; margin-bottom:.75rem; }
  .event img { width:110px; height:80px; object-fit:cover; border-radius:4px; }
  h3 { margin:0 0 .15rem; font-size:1.05rem; }
  h3 a { color:inherit; text-decoration-color:var(--gold); text-underline-offset:3px; }
  .meta { margin:0; color:var(--muted); font-size:.92rem; }
  .desc { margin:.4rem 0 0; font-size:.92rem; max-width:60ch; }
  .badges { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.5rem; }
  .badges:empty { display:none; }
  .badge { background:var(--gold); color:var(--gold-ink); font-size:.75rem; font-weight:700; padding:.1rem .55rem; border-radius:99px; }
  .badge.flag { background:transparent; color:var(--ink); border:1px solid var(--gold); }
  .src { margin:.5rem 0 0; font-size:.75rem; color:var(--muted); }
  #none { display:none; color:var(--muted); }
  @media (max-width:860px) {
    .layout { grid-template-columns:1fr; gap:1rem; }
    .filters { position:static; max-height:none; }
    .day { grid-template-columns:1fr; gap:.5rem; }
    .date { position:static; display:flex; align-items:baseline; gap:.6rem; }
    .num { font-size:2rem; }
    .event img { display:none; }
  }
</style>
</head>
<body>
<header><div>
  <h1>Purdue and IU Indianapolis events, in one place</h1>
  <p>%%TOTAL%% upcoming events combined from %%NSOURCES%% sources. Narrow them down by date, time, field of study, and more.</p>
</div></header>
<div class="layout">
  <details class="filters" id="filters">
    <summary id="fsum">Filters</summary>
    <div class="fgroup"><h2>Date</h2>
      <div class="chips">
        <button type="button" class="chip preset" data-preset="today" aria-pressed="false">Today</button>
        <button type="button" class="chip preset" data-preset="tomorrow" aria-pressed="false">Tomorrow</button>
        <button type="button" class="chip preset" data-preset="week" aria-pressed="false">Next 7 days</button>
        <button type="button" class="chip preset" data-preset="weekend" aria-pressed="false">This weekend</button>
      </div>
      <div class="dates">
        <label>From <input type="date" id="from"></label>
        <label>To <input type="date" id="to"></label>
      </div>
    </div>
    <div class="fgroup"><h2>Time of day</h2><div class="chips">%%TIME_CHIPS%%</div></div>
    <div class="fgroup"><h2>Field of study</h2><div class="chips">%%FIELD_CHIPS%%</div></div>
    <div class="fgroup"><h2>Source</h2><div class="chips">%%SOURCE_CHIPS%%</div></div>
    <div class="fgroup"><h2>Good to know</h2><div class="chips">%%FLAG_CHIPS%%</div></div>
    <button type="button" id="clear">Clear all filters</button>
  </details>
  <main>
    <input id="q" type="search" placeholder="Search events, organizations, locations" aria-label="Search events">
    <p id="count" aria-live="polite"></p>
    <p id="none">No events match these filters. Try removing one.</p>
    %%SECTIONS%%
  </main>
</div>
<script>
(function () {
  var state = { time: new Set(), field: new Set(), source: new Set(), flag: new Set(), from: "", to: "", q: "" };
  var events = Array.prototype.slice.call(document.querySelectorAll(".event"));
  var days = Array.prototype.slice.call(document.querySelectorAll(".day"));
  var q = document.getElementById("q"), fromEl = document.getElementById("from"), toEl = document.getElementById("to");
  var panel = document.getElementById("filters");
  if (window.matchMedia("(min-width: 861px)").matches) { panel.open = true; }

  function iso(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function plus(n) { var d = new Date(); d.setDate(d.getDate() + n); return d; }
  var presets = {
    today: function () { return [iso(plus(0)), iso(plus(0))]; },
    tomorrow: function () { return [iso(plus(1)), iso(plus(1))]; },
    week: function () { return [iso(plus(0)), iso(plus(6))]; },
    weekend: function () {
      var dow = new Date().getDay();
      if (dow === 0) { return [iso(plus(0)), iso(plus(0))]; }
      if (dow === 6) { return [iso(plus(0)), iso(plus(1))]; }
      return [iso(plus(6 - dow)), iso(plus(7 - dow))];
    }
  };

  function anyIn(set, text) {
    return text.split("|").some(function (v) { return set.has(v); });
  }
  function matches(el) {
    var d = el.dataset;
    if (state.q && el.textContent.toLowerCase().indexOf(state.q) === -1) { return false; }
    if (state.from && (!d.date || d.date < state.from)) { return false; }
    if (state.to && (!d.date || d.date > state.to)) { return false; }
    if (state.time.size && !state.time.has(d.slot)) { return false; }
    if (state.field.size && !anyIn(state.field, d.fields)) { return false; }
    if (state.source.size && !anyIn(state.source, d.sources)) { return false; }
    var have = d.flags.split("|");
    var ok = true;
    state.flag.forEach(function (f) { if (have.indexOf(f) === -1) { ok = false; } });
    return ok;
  }

  function apply() {
    var shown = 0;
    events.forEach(function (el) {
      var hit = matches(el);
      el.style.display = hit ? "" : "none";
      if (hit) { shown++; }
    });
    days.forEach(function (day) {
      var any = Array.prototype.some.call(day.querySelectorAll(".event"), function (e) { return e.style.display !== "none"; });
      day.style.display = any ? "" : "none";
    });
    document.getElementById("count").textContent = "Showing " + shown + " of " + events.length + " events";
    document.getElementById("none").style.display = shown ? "none" : "block";
    var active = state.time.size + state.field.size + state.source.size + state.flag.size +
                 (state.from || state.to ? 1 : 0) + (state.q ? 1 : 0);
    document.getElementById("fsum").textContent = active ? "Filters (" + active + " active)" : "Filters";
  }

  function unpressPresets() {
    document.querySelectorAll(".preset").forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
  }

  document.querySelectorAll(".chip[data-group]").forEach(function (chip) {
    chip.addEventListener("click", function () {
      var set = state[chip.dataset.group], v = chip.dataset.value;
      if (set.has(v)) { set.delete(v); chip.setAttribute("aria-pressed", "false"); }
      else { set.add(v); chip.setAttribute("aria-pressed", "true"); }
      apply();
    });
  });

  document.querySelectorAll(".preset").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wasOn = btn.getAttribute("aria-pressed") === "true";
      unpressPresets();
      if (wasOn) { state.from = ""; state.to = ""; }
      else {
        btn.setAttribute("aria-pressed", "true");
        var range = presets[btn.dataset.preset]();
        state.from = range[0]; state.to = range[1];
      }
      fromEl.value = state.from; toEl.value = state.to;
      apply();
    });
  });

  [fromEl, toEl].forEach(function (el) {
    el.addEventListener("change", function () {
      state.from = fromEl.value; state.to = toEl.value;
      unpressPresets();
      apply();
    });
  });

  q.addEventListener("input", function () { state.q = q.value.toLowerCase().trim(); apply(); });

  document.getElementById("clear").addEventListener("click", function () {
    ["time", "field", "source", "flag"].forEach(function (g) { state[g].clear(); });
    state.from = ""; state.to = ""; state.q = "";
    q.value = ""; fromEl.value = ""; toEl.value = "";
    document.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
    apply();
  });

  apply();
})();
</script>
</body>
</html>"""


def build(events):
    events = sorted(events, key=lambda e: e.get("start") or "9999")

    days = OrderedDict()
    for ev in events:
        start = parse(ev.get("start"))
        days.setdefault(start.date() if start else None, []).append(ev)
    sections = ""
    for day, items in days.items():
        num, label = (day.strftime("%-d"), day.strftime("%A, %B")) if day else ("?", "Date to be announced")
        sections += f"""
  <section class="day">
    <div class="date"><span class="num">{num}</span><span class="lbl">{label}</span></div>
    <div class="list">{"".join(row(e) for e in items)}</div>
  </section>"""

    field_counts, source_counts, flag_counts = Counter(), Counter(), Counter()
    for ev in events:
        fields, flags, sources, _ = info(ev)
        field_counts.update(fields)
        flag_counts.update(flags)
        source_counts.update(sources)

    time_chips = chips("time", [(s, s) for s in ("Morning", "Afternoon", "Evening")])
    field_chips = chips("field", [(f, f"{f} ({field_counts[f]})") for f in FIELD_KEYWORDS if field_counts[f]])
    source_chips = chips("source", [(s, f"{s} ({n})") for s, n in source_counts.most_common()])
    flag_chips = chips("flag", [(f, f"{f} ({flag_counts[f]})") for f in ("Food", "Virtual", "Indianapolis") if flag_counts[f]])

    return (PAGE.replace("%%TOTAL%%", str(len(events)))
                .replace("%%NSOURCES%%", str(len(source_counts)))
                .replace("%%TIME_CHIPS%%", time_chips)
                .replace("%%FIELD_CHIPS%%", field_chips)
                .replace("%%SOURCE_CHIPS%%", source_chips)
                .replace("%%FLAG_CHIPS%%", flag_chips)
                .replace("%%SECTIONS%%", sections))


if __name__ == "__main__":
    with open("events.json", encoding="utf-8") as f:
        data = json.load(f)
    with open("events.html", "w", encoding="utf-8") as f:
        f.write(build(data))
    print(f"Wrote events.html with {len(data)} events. Open it with: open events.html")
