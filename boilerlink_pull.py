#TECH 120 Group 3 Final Project (Purdue Event Data Scraper)
import requests

#BoilerLink pulls their events from following website JSON API.
events2 = 10
boilerlink = "https://boilerlink.purdue.edu/api/discovery/event/search"
pullinfoBL = requests.get(boilerlink,params={"status": "Approved", "take": events2, "skip": 0}) #take: # of events pulled | skip: # of events skipped before pulling
data = pullinfoBL.json()

#cuts everything before 'value' phrase in original JSON
events = data["value"]

#filters out all unneccesary fields from filtered list.
filtereddata = [
    [
        event["organizationName"],
        event["name"],
        event["description"],
        event["location"],
        event["startsOn"],
        event["endsOn"],
    ]
    for event in events #repeats to find all qualified 'events'
]

#Removing HTML tags from description field
for event in filtereddata:
    if event[2] is not None:
        event[2] = event[2].strip("<p>")
        event [2] = event[2].strip("&ndash;")
        event [2] = event[2].strip("div>")
        event [2] = event[2].strip("class=")
        event [2] = event[2].strip("&nbsp;")
        event [2] = event[2].strip("</p>")

print ("The Following is a list of the next {events2} events from BoilerLink:")
print (filtereddata)
