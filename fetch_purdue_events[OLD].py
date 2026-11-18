"""
Proof of concept: pull upcoming events from events.purdue.edu (Localist API).

Setup (one time):
    pip install requests

Run:
    python fetch_purdue_events.py
"""

import json
import requests

BASE_URL = "https://events.purdue.edu/api/2/events"


def fetch_events(days=30, per_page=50, page=1):
    """Ask the API for events happening in the next `days` days."""
    params = {
        "days": days,       # how far ahead to look
        "pp": per_page,     # results per page
        "page": page,       # which page of results
    }
    headers = {"User-Agent": "PurdueIndyEventAggregator/0.1 (student project)"}
    response = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
    response.raise_for_status()  # stop with a clear error if the request failed
    return response.json()


def normalize(raw_event):
    """Convert one Localist event into OUR common format."""
    e = raw_event["event"]
    # An event can have several dates (recurring). Take the first for now.
    instances = e.get("event_instances", [])
    first = instances[0]["event_instance"] if instances else {}

    return {
        "title": e.get("title"),
        "description": e.get("description_text"),
        "start": first.get("start"),
        "end": first.get("end"),
        "location": e.get("location_name"),
        "address": e.get("address"),
        "url": e.get("localist_url"),
        "image": e.get("photo_url"),
        "source": "events.purdue.edu",
    }


if __name__ == "__main__":
    data = fetch_events()

    # Print the raw shape of the first event so you can see what's available.
    print("--- RAW FIRST EVENT (explore this!) ---")
    print(json.dumps(data["events"][0], indent=2)[:2000])

    # Convert everything to our own format.
    events = [normalize(item) for item in data["events"]]

    print("\n--- NORMALIZED EVENTS ---")
    for ev in events:
        print(f'{ev["start"]}  |  {ev["title"]}  |  {ev["location"]}')

    # Save to a file so you can inspect it.
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    print(f"\nSaved {len(events)} events to events.json")
