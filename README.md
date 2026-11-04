# Purdue-Events
Purdue Events Aggregator (Proof of Concept)

A small Python project that collects campus event listings into one structured dataset and displays them as a single, searchable page. It exists to explore a problem: Purdue Indianapolis students often miss campus events because announcements are scattered across BoilerLink, Instagram, CampusBoard, and flyers.

Status: proof of concept. It currently pulls from one source (events.purdue.edu) and covers all of Purdue, not only the Indianapolis campus.

What's in this project
File	Purpose
fetch_purdue_events.py	Calls the Purdue events API, converts each event to a common format, and saves the results to events.json.
make_mockup.py	Reads events.json and builds events.html, a styled agenda page with search and field-of-study filters.
events.json	Generated output from the fetch script (not committed by hand).
events.html	Generated mockup page (open in any browser).
Requirements
Python 3.9 or newer
The requests library (needed by fetch_purdue_events.py only; make_mockup.py uses just the standard library)
An internet connection for the fetch step
Setup (macOS)
bash
cd ~/purdue-events
python3 -m venv venv          # one time: create a virtual environment
source venv/bin/activate      # turn it on (look for "(venv)" in your prompt)
pip install requests          # one time: install the dependency

The virtual environment keeps this project's packages separate from the rest of your computer. You need to run source venv/bin/activate again each time you open a new Terminal window.

Usage
bash
cd ~/purdue-events
source venv/bin/activate
python fetch_purdue_events.py   # fetch events, writes events.json
python make_mockup.py           # build the page, writes events.html
open events.html                # view it in your browser

If you only want to rebuild the page from existing data, run just the last two commands.

How it works
Fetch. fetch_purdue_events.py requests events from the Localist API that powers events.purdue.edu (https://events.purdue.edu/api/2/events). By default it asks for the next 30 days, 50 events per page. It sends a descriptive User-Agent so site administrators can identify the traffic.
Normalize. Each source formats events differently, so the script converts every event into one common format. Future sources should each get their own small conversion function that produces the same fields.
Display. make_mockup.py groups events by date, adds field-of-study tags, and writes a self-contained HTML page with search and filter chips.
Common event format
Field	Description
title	Event name
description	Plain-text description
start, end	ISO 8601 timestamps (first occurrence if the event recurs)
location	Venue name
address	Street address, if provided
url	Link to the original listing
image	Event photo URL, if provided
source	Where the event came from (currently events.purdue.edu)
The mockup page
Events grouped by day in an agenda layout
Keyword search that filters as you type
Filter chips by field of study (for example Architecture & Design, Engineering, Business), each showing a count
Search and chips work together
Responsive layout and automatic dark mode
Field-of-study tags are keyword guesses

The API data has no "major" field, so make_mockup.py tags an event when its title or description contains certain words. These tags are approximate: some events will be missed or tagged wrongly. To change them, edit the FIELD_KEYWORDS dictionary near the top of make_mockup.py. Each line maps a field name to a list of trigger words, and words match at the start of a word (so engineer also matches "engineering").

Customizing the fetch

In fetch_purdue_events.py, fetch_events(days=30, per_page=50, page=1) controls how far ahead to look and how many results to request.

Known limitations
Single source. Only events.purdue.edu is included. BoilerLink, CampusBoard, and social media are not.
Not filtered to Indianapolis. Results cover all of Purdue.
No pagination. Only the first page of results is fetched.
Recurring events show only their first occurrence.
Storage is a flat JSON file. There is no database, deduplication, or handling of canceled events.
Not automated. Nothing runs on a schedule or alerts you if the fetch fails.
Roadmap
Filter to Purdue Indianapolis (group or campus filter in the API)
Fetch all pages of results
Use Localist's own categories or departments instead of keyword guessing, if available in the data
Store events in SQLite with deduplication
Add more sources
Output a subscribable calendar (ICS) feed
Responsible use

Automated data collection carries legal and ethical considerations. Localist's API documentation states that API use is subject to its terms of use, so confirm with Purdue's events team that ongoing use is acceptable before running this regularly or publicly. Keep request volume low, identify the scraper with a clear User-Agent, and check a site's robots.txt and terms before adding any new source.

References
Krotov, V., Johnson, L., & Silva, L. (2020). Tutorial: Legality and ethics of web scraping. Communications of the Association for Information Systems, 47. https://doi.org/10.17705/1CAIS.04724
Koster, M., Illyes, G., Zeller, H., & Sassman, L. (2022). Robots Exclusion Protocol (RFC 9309). Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc9309
Localist API documentation: https://developer.localist.com/doc/api
