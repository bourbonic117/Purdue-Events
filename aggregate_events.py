"""
aggregate_events.py
Collect Purdue / IU Indianapolis events from several sources at once, merge
duplicates, and write one events.json.

Sources
  1. events.purdue.edu       Localist JSON API
  2. boilerlink.purdue.edu   BoilerLink (Engage) search API
  3. campusbord.com          HTML page (parsed from its visible text)
  4. events.iu.edu           LiveWhale JSON feed for IU Indianapolis

Setup (once, inside your venv):
    pip install requests beautifulsoup4

Run:
    python aggregate_events.py             # writes events.json
    python aggregate_events.py --debug     # show full error details
    python aggregate_events.py --days 14 --out my_events.json

The output is a list of events with the same core fields as before (title,
description, start, end, location, address, url, image, source), so
make_mockup.py still works. Extra fields: organizer, tags, perks, sources.
"""

import argparse
import json
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

TZ = ZoneInfo("America/Indiana/Indianapolis")
HEADERS = {"User-Agent": "PurdueIndyEventAggregator/0.2 (student project)"}
TIMEOUT = 20
DAYS_AHEAD = 30
DEBUG = False

# IU's calendar groups events by "group" name. If the IU source returns 0
# events, this is the first thing to check (open events.iu.edu/indianapolis/,
# DevTools > Network, and look at the live/json request it makes).
IU_JSON = "https://events.iu.edu/live/json/events/group/Indianapolis/"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def get(url, **kwargs):
    """GET with one retry. Raises requests.RequestException on failure."""
    last = None
    for _ in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as err:
            last = err
            time.sleep(1.5)
    raise last


def clean_html(text):
    """Strip HTML tags and collapse whitespace."""
    if not text:
        return ""
    return " ".join(BeautifulSoup(text, "html.parser").get_text(" ").split())


def to_local_iso(value, naive_tz=TZ):
    """Turn many timestamp shapes into an ISO string in Indianapolis time."""
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=naive_tz)
    return dt.astimezone(TZ).isoformat()


def make_event(source, source_url, title, start, end=None, description="",
               location=None, address=None, url=None, image=None,
               organizer=None, tags=None, perks=None, naive_tz=TZ):
    return {
        "title": (title or "").strip(),
        "description": clean_html(description),
        "start": to_local_iso(start, naive_tz),
        "end": to_local_iso(end, naive_tz),
        "location": location or None,
        "address": address or None,
        "url": url or None,
        "image": image or None,
        "organizer": organizer or None,
        "tags": sorted(set(t for t in (tags or []) if t)),
        "perks": sorted(set("Food" if "food" in p.lower() else p
                            for p in (perks or []) if p)),
        "source": source,
        "sources": [{"name": source, "url": url or source_url}],
    }


# ----------------------------------------------------------------------
# Source 1: events.purdue.edu (Localist)
# ----------------------------------------------------------------------

def fetch_purdue():
    base = "https://events.purdue.edu"
    out = []
    for page in range(1, 6):  # safety cap: 5 pages
        data = get(base + "/api/2/events",
                   params={"days": DAYS_AHEAD, "pp": 50, "page": page}).json()
        for item in data.get("events", []):
            e = item["event"]
            filters = e.get("filters") or {}
            tags = [t.get("name") for t in filters.get("event_types", [])]
            orgs = [d.get("name") for d in filters.get("departments", [])]
            for inst in (e.get("event_instances") or [{}]):
                i = inst.get("event_instance", {})
                out.append(make_event(
                    "Purdue Events", base, e.get("title"),
                    i.get("start"), i.get("end"), e.get("description_text"),
                    e.get("location_name"), e.get("address"),
                    e.get("localist_url"), e.get("photo_url"),
                    ", ".join(o for o in orgs if o), tags))
        if page >= (data.get("page") or {}).get("total", 1):
            break
        time.sleep(0.5)
    return out


# ----------------------------------------------------------------------
# Source 2: BoilerLink (Engage search API)
# ----------------------------------------------------------------------

def fetch_boilerlink():
    base = "https://boilerlink.purdue.edu"
    now = datetime.now(timezone.utc)
    out, skip, take = [], 0, 100
    while skip < 500:  # safety cap
        data = get(base + "/api/discovery/event/search", params={
            "endsAfter": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "orderByField": "endsOn",
            "orderByDirection": "ascending",
            "status": "Approved",
            "take": take,
            "skip": skip,
        }).json()
        rows = data.get("value", [])
        for e in rows:
            img = e.get("imagePath")
            out.append(make_event(
                "BoilerLink", base + "/events", e.get("name"),
                e.get("startsOn"), e.get("endsOn"), e.get("description"),
                e.get("location"), None,
                f"{base}/event/{e.get('id')}" if e.get("id") else None,
                f"https://se-images.campuslabs.com/clink/images/{img}" if img else None,
                e.get("organizationName"),
                e.get("categoryNames"), e.get("benefitNames")))
        if len(rows) < take:
            break
        skip += take
        time.sleep(0.5)
    return out


# ----------------------------------------------------------------------
# Source 3: CampusBord (HTML, parsed from visible text order)
# ----------------------------------------------------------------------
# The page lists a date heading ("Today", "Tomorrow", "Nov 18"), then for
# each event: time, title, "By <organizer>", location, then tag labels.

TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s?(AM|PM)$", re.I)
DATE_RE = re.compile(
    r"^(Today|Tomorrow|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2})$",
    re.I)


def resolve_day(label, today):
    low = label.lower()
    if low == "today":
        return today
    if low == "tomorrow":
        return today + timedelta(days=1)
    mon, day = label.replace(".", "").split()[:2]
    day_date = datetime.strptime(f"{mon[:3].title()} {day} {today.year}", "%b %d %Y").date()
    if day_date < today - timedelta(days=60):  # e.g. a "Jan 5" seen in December
        day_date = day_date.replace(year=today.year + 1)
    return day_date


def parse_campusbord(html, today=None):
    base = "https://campusbord.com/"
    today = today or datetime.now(TZ).date()
    soup = BeautifulSoup(html, "html.parser")
    lines = [ln.strip() for ln in soup.get_text("\n").split("\n") if ln.strip()]

    imgs = [i.get("src", "") for i in soup.find_all("img")
            if "/api/event/img/" in i.get("src", "") or "/static/images/fliers/" in i.get("src", "")]

    events, cur_day, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        if ln == "Contact Us":
            break
        if DATE_RE.match(ln):
            cur_day = resolve_day(ln, today)
            i += 1
            continue
        if cur_day and TIME_RE.match(ln):
            block, j = [], i + 1
            while j < len(lines) and not TIME_RE.match(lines[j]) \
                    and not DATE_RE.match(lines[j]) and lines[j] != "Contact Us":
                block.append(lines[j])
                j += 1
            if block:
                title = block[0]
                organizer, rest = None, block[1:]
                if rest and rest[0].lower().startswith("by "):
                    organizer, rest = rest[0][3:].strip(), rest[1:]
                location = rest[0] if rest else None
                labels = rest[1:]
                clock = datetime.strptime(ln.upper().replace(" ", ""), "%I:%M%p").time()
                start = datetime.combine(cur_day, clock, tzinfo=TZ).isoformat()
                events.append(make_event(
                    "CampusBord", base, title, start, None, "", location,
                    None, None, None, organizer,
                    [t for t in labels if t != "Food"],
                    ["Food"] if "Food" in labels else []))
            i = j
            continue
        i += 1

    # Photos line up one-to-one with events only if the counts match.
    if len(imgs) == len(events):
        for ev, src in zip(events, imgs):
            if "/api/event/img/" in src:  # skip generic category placeholders
                ev["image"] = urljoin(base, src)
    return events


def fetch_campusbord():
    return parse_campusbord(get("https://campusbord.com/").text)


# ----------------------------------------------------------------------
# Source 4: IU Indianapolis (events.iu.edu, LiveWhale JSON)
# ----------------------------------------------------------------------

def fetch_iu():
    data = get(IU_JSON, params={"max": 100}).json()
    rows = data if isinstance(data, list) else data.get("events", [])
    out = []
    for e in rows:
        cats = e.get("categories") or []
        tags = [c if isinstance(c, str) else (c or {}).get("title") for c in cats]
        thumb = e.get("thumbnail")
        out.append(make_event(
            "IU Indianapolis", "https://events.iu.edu/indianapolis/",
            e.get("title"),
            e.get("date_utc"), e.get("date2_utc"),
            e.get("description") or e.get("summary"),
            e.get("location"), None, e.get("url"),
            urljoin("https://events.iu.edu/", thumb) if thumb else None,
            e.get("group_title"), tags, naive_tz=timezone.utc))
    return out


# ----------------------------------------------------------------------
# Duplicate detection and merging
# ----------------------------------------------------------------------

STOP_WORDS = {"the", "a", "an", "and", "of", "at", "for", "to", "in", "on", "with"}


def norm_title(title):
    text = re.sub(r"[^a-z0-9 ]+", " ", (title or "").lower())
    return " ".join(w for w in text.split() if w not in STOP_WORDS)


def similar_titles(a, b):
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = sorted((na, nb), key=len)
    # One title inside the other counts only if they are close in length, so
    # "Career Fair" is not merged with "Career Fair Prep Workshop".
    if len(short) >= 8 and short in long_ and len(short) / len(long_) >= 0.7:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.85


def close_in_time(a, b, minutes=30):
    if not a["start"] or not b["start"]:
        return a["start"] == b["start"]  # both unknown counts as a match
    gap = abs(datetime.fromisoformat(a["start"]) - datetime.fromisoformat(b["start"]))
    return gap <= timedelta(minutes=minutes)


def completeness(e):
    return (len(e["description"]) > 0) * 2 + sum(
        1 for k in ("location", "url", "image", "organizer", "end") if e.get(k))


def merge(a, b):
    """Combine two records of the same event, keeping the fuller one."""
    keep, other = (a, b) if completeness(a) >= completeness(b) else (b, a)
    for k in ("end", "location", "address", "url", "image", "organizer"):
        if not keep.get(k) and other.get(k):
            keep[k] = other[k]
    if len(other["description"]) > len(keep["description"]):
        keep["description"] = other["description"]
    keep["tags"] = sorted(set(keep["tags"]) | set(other["tags"]))
    keep["perks"] = sorted(set(keep["perks"]) | set(other["perks"]))
    for s in other["sources"]:
        if s not in keep["sources"]:
            keep["sources"].append(s)
    return keep


def dedupe(events):
    """Same normalized title (or near match) + start within 30 minutes = same event."""
    buckets, removed = {}, 0
    for ev in events:
        day = (ev["start"] or "")[:10] or None
        group = buckets.setdefault(day, [])
        for idx, existing in enumerate(group):
            if close_in_time(existing, ev) and similar_titles(existing["title"], ev["title"]):
                group[idx] = merge(existing, ev)
                removed += 1
                break
        else:
            group.append(ev)
    merged = [e for group in buckets.values() for e in group]
    for e in merged:
        e["source"] = " + ".join(s["name"] for s in e["sources"])
    return merged, removed


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

SOURCES = {
    "Purdue Events": fetch_purdue,
    "BoilerLink": fetch_boilerlink,
    "CampusBord": fetch_campusbord,
    "IU Indianapolis": fetch_iu,
}


def in_window(ev, start, end):
    if not ev["start"]:
        return True
    return start <= datetime.fromisoformat(ev["start"]) <= end


def main():
    global DAYS_AHEAD, DEBUG
    parser = argparse.ArgumentParser(description="Aggregate Purdue/IU events.")
    parser.add_argument("--out", default="events.json")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    DAYS_AHEAD, DEBUG = args.days, args.debug

    print(f"Fetching {len(SOURCES)} sources at once...")
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        futures = {name: pool.submit(fn) for name, fn in SOURCES.items()}

    all_events, report = [], []
    for name, fut in futures.items():
        try:
            rows = fut.result()
            all_events.extend(rows)
            report.append((name, len(rows), "ok" if rows else "ok, but 0 events (check the source)"))
        except Exception as err:  # one failing source must not stop the others
            report.append((name, 0, f"FAILED: {err}"))
            if DEBUG:
                traceback.print_exc()

    now = datetime.now(TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window = [e for e in all_events if e["title"] and in_window(e, start, now + timedelta(days=DAYS_AHEAD))]
    unique, removed = dedupe(window)
    unique.sort(key=lambda e: (e["start"] is None, e["start"] or ""))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print("\nSource summary")
    for name, count, status in report:
        print(f"  {name:<16} {count:>4} events   {status}")
    print(f"\nCollected {len(all_events)}, kept {len(window)} in the next {DAYS_AHEAD} days, "
          f"merged {removed} duplicates -> {len(unique)} unique events")
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
