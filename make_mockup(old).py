"""
Turn events.json (from fetch_purdue_events.py) into a presentable events.html.

Run (in the same folder as events.json):
    python make_mockup.py
    open events.html
"""

import json
import re
from collections import OrderedDict
from datetime import datetime
from html import escape

# Edit these freely. Each field maps to words that suggest an event is
# relevant to students in that major. Words match at the start of a word,
# so "engineer" also catches "engineering".
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


def parse(ts):
    """Parse an ISO timestamp from Localist. Returns None if missing/bad."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def short(text, limit=170):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def tags(ev):
    """Return the list of fields of study this event seems relevant to."""
    blob = ((ev.get("title") or "") + " " + (ev.get("description") or "")).lower()
    found = []
    for field, words in FIELD_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(w), blob) for w in words):
            found.append(field)
    return found


def row(ev):
    start, end = parse(ev.get("start")), parse(ev.get("end"))
    when = start.strftime("%-I:%M %p") if start else "Time TBD"
    if start and end:
        when += " to " + end.strftime("%-I:%M %p")
    where = escape(ev.get("location") or "Location TBD")
    title = escape(ev.get("title") or "Untitled event")
    if ev.get("url"):
        title = f'<a href="{escape(ev["url"])}" target="_blank" rel="noopener">{title}</a>'
    ev_tags = tags(ev)
    badge = "".join(f'<span class="badge">{escape(t)}</span>' for t in ev_tags)
    data_tags = escape("|".join(ev_tags))
    img = (f'<img src="{escape(ev["image"])}" alt="" loading="lazy">'
           if ev.get("image") else "")
    return f"""
    <article class="event" data-tags="{data_tags}">
      <div class="info">
        <h3>{title}</h3>
        <p class="meta">{when}, {where}</p>
        <p class="desc">{escape(short(ev.get("description")))}</p>
        <div class="badges">{badge}</div>
      </div>
      {img}
    </article>"""


def build(events):
    days = OrderedDict()
    for ev in sorted(events, key=lambda e: e.get("start") or "9999"):
        start = parse(ev.get("start"))
        days.setdefault(start.date() if start else None, []).append(ev)

    counts = OrderedDict((f, 0) for f in FIELD_KEYWORDS)
    for ev in events:
        for t in tags(ev):
            counts[t] += 1
    chips = '<button class="chip active" data-tag="">All</button>' + "".join(
        f'<button class="chip" data-tag="{escape(f)}">{escape(f)} ({n})</button>'
        for f, n in counts.items() if n)

    sections = ""
    for day, items in days.items():
        if day:
            num, label = day.strftime("%-d"), day.strftime("%A, %B")
        else:
            num, label = "?", "Date to be announced"
        sections += f"""
  <section class="day">
    <div class="date"><span class="num">{num}</span><span class="lbl">{label}</span></div>
    <div class="list">{"".join(row(e) for e in items)}</div>
  </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Purdue Events, in one place</title>
<style>
  :root {{
    --bg: #f1f1ee; --card: #ffffff; --ink: #1b1b1b; --muted: #5d5d5d;
    --line: #d9d9d4; --gold: #cfb991; --gold-ink: #4a3b17;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #141414; --card: #1f1f1f; --ink: #f0f0ec; --muted: #a8a8a2;
             --line: #333; --gold: #cfb991; --gold-ink: #1b1b1b; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink);
         font: 16px/1.5 "Avenir Next", "Helvetica Neue", Arial, sans-serif; }}
  header {{ background: #000; color: #fff; padding: 2.2rem 1.25rem 1.6rem;
           border-bottom: 6px solid var(--gold); }}
  header div {{ max-width: 860px; margin: 0 auto; }}
  h1 {{ margin: 0 0 .3rem; font-size: clamp(1.8rem, 5vw, 2.8rem); font-weight: 800;
       letter-spacing: -.02em; }}
  header p {{ margin: 0; color: #cfcfca; max-width: 52ch; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 1.25rem; }}
  #q {{ width: 100%; padding: .8rem 1rem; font: inherit; color: var(--ink);
       background: var(--card); border: 1px solid var(--line); border-radius: 6px;
       margin-bottom: 1.5rem; }}
  #q:focus-visible, a:focus-visible {{ outline: 3px solid var(--gold); outline-offset: 2px; }}
  .day {{ display: grid; grid-template-columns: 110px 1fr; gap: 1.25rem;
         padding: 1.25rem 0; border-top: 1px solid var(--line); }}
  .date {{ position: sticky; top: 1rem; align-self: start; }}
  .num {{ display: block; font-size: 3rem; font-weight: 800; line-height: 1; }}
  .lbl {{ color: var(--muted); font-size: .9rem; }}
  .event {{ display: flex; gap: 1rem; justify-content: space-between;
           background: var(--card); border-left: 4px solid var(--gold);
           padding: 1rem 1.1rem; margin-bottom: .75rem; }}
  .event img {{ width: 110px; height: 80px; object-fit: cover; border-radius: 4px; }}
  h3 {{ margin: 0 0 .15rem; font-size: 1.05rem; }}
  h3 a {{ color: inherit; text-decoration-color: var(--gold); text-underline-offset: 3px; }}
  .meta {{ margin: 0; color: var(--muted); font-size: .92rem; }}
  .desc {{ margin: .4rem 0 0; font-size: .92rem; max-width: 60ch; }}
  .badges {{ display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .5rem; }}
  .badges:empty {{ display: none; }}
  .badge {{ background: var(--gold); color: var(--gold-ink); font-size: .75rem;
           font-weight: 700; padding: .1rem .55rem; border-radius: 99px; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1.5rem; }}
  .chip {{ font: inherit; font-size: .88rem; color: var(--ink); background: var(--card);
          border: 1px solid var(--line); border-radius: 99px; padding: .35rem .85rem;
          cursor: pointer; }}
  .chip:focus-visible {{ outline: 3px solid var(--gold); outline-offset: 2px; }}
  .chip.active {{ background: var(--gold); color: var(--gold-ink); border-color: var(--gold);
                 font-weight: 700; }}
  #none {{ display: none; color: var(--muted); }}
  @media (max-width: 600px) {{
    .day {{ grid-template-columns: 1fr; gap: .5rem; }}
    .date {{ position: static; display: flex; align-items: baseline; gap: .6rem; }}
    .num {{ font-size: 2rem; }}
    .event img {{ display: none; }}
  }}
</style>
</head>
<body>
<header><div>
  <h1>Purdue events, in one place</h1>
  <p>{len(events)} upcoming events from events.purdue.edu. Filter by your field of study or search by keyword.</p>
</div></header>
<main>
  <div class="chips" role="group" aria-label="Filter by field of study">{chips}</div>
  <input id="q" type="search" placeholder="Search events, for example: career, library, workshop" aria-label="Search events">
  <p id="none">No events match your search. Try a shorter word.</p>
  {sections}
</main>
<script>
  const q = document.getElementById("q");
  let activeTag = "";

  function applyFilters() {{
    const term = q.value.toLowerCase().trim();
    let shown = 0;
    document.querySelectorAll(".event").forEach(el => {{
      const tagHit = !activeTag || el.dataset.tags.split("|").includes(activeTag);
      const textHit = el.textContent.toLowerCase().includes(term);
      const hit = tagHit && textHit;
      el.style.display = hit ? "" : "none";
      if (hit) shown++;
    }});
    document.querySelectorAll(".day").forEach(d => {{
      const any = [...d.querySelectorAll(".event")].some(e => e.style.display !== "none");
      d.style.display = any ? "" : "none";
    }});
    document.getElementById("none").style.display = shown ? "none" : "block";
  }}

  q.addEventListener("input", applyFilters);
  document.querySelectorAll(".chip").forEach(chip => {{
    chip.addEventListener("click", () => {{
      activeTag = chip.dataset.tag;
      document.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === chip));
      applyFilters();
    }});
  }});
</script>
</body>
</html>"""


if __name__ == "__main__":
    with open("events.json", encoding="utf-8") as f:
        events = json.load(f)
    with open("events.html", "w", encoding="utf-8") as f:
        f.write(build(events))
    print(f"Wrote events.html with {len(events)} events. Open it with: open events.html")
