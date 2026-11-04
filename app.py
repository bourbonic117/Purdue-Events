
import requests
import re
from flask import Flask, render_template_string
from html.parser import HTMLParser
from datetime import datetime
from collections import OrderedDict

app = Flask(__name__)

# ==========================================
# EVENT CATEGORIES
# ==========================================

FIELD_KEYWORDS = {
    "Architecture & Design": [
        "architect", "interior design", "design",
        "landscape", "urban planning"
    ],
    "Engineering": [
        "engineer", "robotics", "mechanical",
        "electrical", "civil", "aerospace"
    ],
    "Computer Science & Tech": [
        "computer science", "coding", "software",
        "data science", "cybersecurity",
        "machine learning", "artificial intelligence"
    ],
    "Business": [
        "business", "finance", "accounting",
        "entrepreneur", "marketing", "management"
    ],
    "Health & Nursing": [
        "nursing", "health", "medical",
        "pharmacy", "clinical"
    ],
    "Science & Math": [
        "biology", "chemistry", "physics",
        "math", "research"
    ],
    "Arts & Humanities": [
        "music", "theatre", "theater", "film",
        "gallery", "history", "english",
        "psychology", "communication"
    ],
    "Career & Networking": [
        "career", "internship", "networking",
        "resume", "job fair"
    ]
}


# ==========================================
# CLEAN EVENT DESCRIPTIONS
# ==========================================

class DescriptionParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)


def clean_description(description):

    if not description:
        return ""

    parser = DescriptionParser()
    parser.feed(description)

    return " ".join(" ".join(parser.text).split())


# ==========================================
# SCRAPER 1: BOILERLINK
# ==========================================

def fetch_boilerlink():

    url = "https://boilerlink.purdue.edu/api/discovery/event/search"

    response = requests.get(
        url,
        params={
            "status": "Approved",
            "take": 50,
            "skip": 0
        },
        timeout=15
    )

    response.raise_for_status()

    events = response.json()["value"]

    normalized = []

    for event in events:

        normalized.append({
            "title": event.get("name"),
            "description": clean_description(
                event.get("description")
            ),
            "start": event.get("startsOn"),
            "end": event.get("endsOn"),
            "location": event.get("location"),
            "url": None,
            "image": None,
            "source": "BoilerLink"
        })

    return normalized


# ==========================================
# SCRAPER 2: PURDUE EVENTS
# ==========================================

def fetch_purdue():

    url = "https://events.purdue.edu/api/2/events"

    response = requests.get(
        url,
        params={
            "days": 30,
            "pp": 50,
            "page": 1
        },
        headers={
            "User-Agent": "PurdueStudentEventProject/1.0"
        },
        timeout=15
    )

    response.raise_for_status()

    events = response.json()["events"]

    normalized = []

    for item in events:

        event = item["event"]

        instances = event.get("event_instances", [])

        first = (
            instances[0]["event_instance"]
            if instances else {}
        )

        normalized.append({
            "title": event.get("title"),
            "description": clean_description(
                event.get("description_text")
            ),
            "start": first.get("start"),
            "end": first.get("end"),
            "location": event.get("location_name"),
            "url": event.get("localist_url"),
            "image": event.get("photo_url"),
            "source": "Purdue Events"
        })

    return normalized


# ==========================================
# EVENT CATEGORIZATION
# ==========================================

def get_tags(event):

    text = (
        (event.get("title") or "") + " " +
        (event.get("description") or "")
    ).lower()

    found = []

    for field, keywords in FIELD_KEYWORDS.items():

        if any(
            re.search(r"\b" + re.escape(word), text)
            for word in keywords
        ):
            found.append(field)

    return found


# ==========================================
# DATE FORMATTING
# ==========================================

def parse_date(timestamp):

    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

    except (ValueError, AttributeError):
        return None


def format_time(timestamp):

    date = parse_date(timestamp)

    if not date:
        return "Time TBD"

    return date.strftime("%I:%M %p").lstrip("0")


# ==========================================
# COMBINE AND ORGANIZE EVENTS
# ==========================================

def get_all_events():

    events = []

    # Get BoilerLink events
    try:
        events.extend(fetch_boilerlink())
        print("BoilerLink events collected.")

    except requests.RequestException as error:
        print("BoilerLink error:", error)

    # Get Purdue Events
    try:
        events.extend(fetch_purdue())
        print("Purdue Events collected.")

    except requests.RequestException as error:
        print("Purdue Events error:", error)

    # Remove duplicate events
    unique_events = {}

    for event in events:

        key = (
            (event.get("title") or "").strip().lower(),
            event.get("start")
        )

        if key not in unique_events:
            unique_events[key] = event

    events = list(unique_events.values())

    # Prepare events for the website
    for event in events:

        event["tags"] = get_tags(event)

        event["short_description"] = (
            event["description"][:170] + "..."
            if len(event["description"]) > 170
            else event["description"]
        )

        event["time"] = format_time(event["start"])

        end_time = format_time(event["end"])

        if event["time"] != "Time TBD" and end_time != "Time TBD":
            event["time"] += " to " + end_time

    # Sort events by date
    events.sort(
        key=lambda event: (
            parse_date(event["start"]) is None,
            parse_date(event["start"]) or datetime.max
        )
    )

    return events


# ==========================================
# HTML WEBSITE
# ==========================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Purdue Events, in One Place</title>

<style>

:root {
    --bg: #f1f1ee;
    --card: #ffffff;
    --ink: #1b1b1b;
    --muted: #5d5d5d;
    --line: #d9d9d4;
    --gold: #cfb991;
    --gold-ink: #4a3b17;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 16px/1.5 Arial, sans-serif;
}

header {
    background: #000;
    color: white;
    padding: 2.2rem 1.25rem 1.6rem;
    border-bottom: 6px solid var(--gold);
}

header div {
    max-width: 860px;
    margin: auto;
}

h1 {
    margin: 0 0 .3rem;
    font-size: clamp(1.8rem, 5vw, 2.8rem);
}

header p {
    color: #cfcfca;
    margin: 0;
}

main {
    max-width: 860px;
    margin: auto;
    padding: 1.25rem;
}

#q {
    width: 100%;
    padding: .8rem 1rem;
    font: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    margin-bottom: 1.5rem;
}

.day {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 1.25rem;
    padding: 1.25rem 0;
    border-top: 1px solid var(--line);
}

.date {
    position: sticky;
    top: 1rem;
    align-self: start;
}

.num {
    display: block;
    font-size: 3rem;
    font-weight: 800;
    line-height: 1;
}

.lbl {
    color: var(--muted);
    font-size: .9rem;
}

.event {
    display: flex;
    gap: 1rem;
    justify-content: space-between;
    background: var(--card);
    border-left: 4px solid var(--gold);
    padding: 1rem 1.1rem;
    margin-bottom: .75rem;
}

.event img {
    width: 110px;
    height: 80px;
    object-fit: cover;
    border-radius: 4px;
}

h3 {
    margin: 0 0 .15rem;
    font-size: 1.05rem;
}

h3 a {
    color: inherit;
    text-decoration-color: var(--gold);
}

.meta {
    margin: 0;
    color: var(--muted);
    font-size: .92rem;
}

.desc {
    margin: .4rem 0 0;
    font-size: .92rem;
}

.badges {
    display: flex;
    flex-wrap: wrap;
    gap: .35rem;
    margin-top: .5rem;
}

.badge {
    background: var(--gold);
    color: var(--gold-ink);
    font-size: .75rem;
    font-weight: 700;
    padding: .1rem .55rem;
    border-radius: 99px;
}

.source {
    color: var(--muted);
    font-size: .75rem;
    margin-top: .5rem;
}

.chips {
    display: flex;
    flex-wrap: wrap;
    gap: .5rem;
    margin-bottom: 1.5rem;
}

.chip {
    font: inherit;
    font-size: .88rem;
    background: white;
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: .35rem .85rem;
    cursor: pointer;
}

.chip.active {
    background: var(--gold);
    color: var(--gold-ink);
    font-weight: 700;
}

#none {
    display: none;
    color: var(--muted);
}

@media (max-width: 600px) {

    .day {
        grid-template-columns: 1fr;
        gap: .5rem;
    }

    .date {
        position: static;
        display: flex;
        align-items: baseline;
        gap: .6rem;
    }

    .num {
        font-size: 2rem;
    }

    .event img {
        display: none;
    }
}

</style>
</head>

<body>

<header>
    <div>
        <h1>Purdue events, in one place</h1>

        <p>
            {{ count }} upcoming events collected from Purdue event websites.
        </p>
    </div>
</header>

<main>

    <div class="chips">

        <button class="chip active" data-tag="">
            All
        </button>

        {% for field, number in counts.items() %}

            {% if number > 0 %}

                <button class="chip" data-tag="{{ field }}">
                    {{ field }} ({{ number }})
                </button>

            {% endif %}

        {% endfor %}

    </div>

    <input
        id="q"
        type="search"
        placeholder="Search events, organizations, locations..."
    >

    <p id="none">
        No events match your search. Try a shorter word.
    </p>

    {% for day in days %}

        <section class="day">

            <div class="date">
                <span class="num">{{ day.number }}</span>
                <span class="lbl">{{ day.label }}</span>
            </div>

            <div class="list">

                {% for event in day.events %}

                    <article
                        class="event"
                        data-tags="{{ event.tags | join('|') }}"
                    >

                        <div class="info">

                            <h3>

                                {% if event.url %}

                                    <a href="{{ event.url }}"
                                       target="_blank"
                                       rel="noopener">
                                        {{ event.title or "Untitled event" }}
                                    </a>

                                {% else %}

                                    {{ event.title or "Untitled event" }}

                                {% endif %}

                            </h3>

                            <p class="meta">
                                {{ event.time }} ·
                                {{ event.location or "Location TBD" }}
                            </p>

                            <p class="desc">
                                {{ event.short_description }}
                            </p>

                            <div class="badges">

                                {% for tag in event.tags %}

                                    <span class="badge">
                                        {{ tag }}
                                    </span>

                                {% endfor %}

                            </div>

                            <p class="source">
                                Source: {{ event.source }}
                            </p>

                        </div>

                        {% if event.image %}

                            <img
                                src="{{ event.image }}"
                                alt=""
                                loading="lazy"
                            >

                        {% endif %}

                    </article>

                {% endfor %}

            </div>

        </section>

    {% endfor %}

</main>

<script>

const q = document.getElementById("q");

let activeTag = "";

function applyFilters() {

    const term = q.value.toLowerCase().trim();

    let shown = 0;

    document.querySelectorAll(".event").forEach(el => {

        const tagHit =
            !activeTag ||
            el.dataset.tags.split("|").includes(activeTag);

        const textHit =
            el.textContent.toLowerCase().includes(term);

        const hit = tagHit && textHit;

        el.style.display = hit ? "" : "none";

        if (hit) shown++;

    });

    document.querySelectorAll(".day").forEach(day => {

        const any = [...day.querySelectorAll(".event")]
            .some(event => event.style.display !== "none");

        day.style.display = any ? "" : "none";

    });

    document.getElementById("none").style.display =
        shown ? "none" : "block";

}

q.addEventListener("input", applyFilters);

document.querySelectorAll(".chip").forEach(chip => {

    chip.addEventListener("click", () => {

        activeTag = chip.dataset.tag;

        document.querySelectorAll(".chip").forEach(c => {
            c.classList.toggle("active", c === chip);
        });

        applyFilters();

    });

});

</script>

</body>
</html>
"""


# ==========================================
# RUN WEBSITE
# ==========================================

@app.route("/")
def home():

    events = get_all_events()

    # Group events by date
    grouped = OrderedDict()

    for event in events:

        date = parse_date(event["start"])

        day = date.date() if date else None

        grouped.setdefault(day, []).append(event)

    days = []

    for date, items in grouped.items():

        if date:

            days.append({
                "number": date.day,
                "label": date.strftime("%A, %B"),
                "events": items
            })

        else:

            days.append({
                "number": "?",
                "label": "Date to be announced",
                "events": items
            })

    # Count events in each category
    counts = OrderedDict(
        (field, 0) for field in FIELD_KEYWORDS
    )

    for event in events:

        for tag in event["tags"]:
            counts[tag] += 1

    return render_template_string(
        HTML_PAGE,
        events=events,
        days=days,
        counts=counts,
        count=len(events)
    )


if __name__ == "__main__":

    app.run(debug=True)
